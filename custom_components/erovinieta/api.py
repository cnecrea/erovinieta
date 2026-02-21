"""Manager API pentru integrarea CNAIR eRovinieta."""

import requests
import logging
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError

from .const import (
    URL_LOGIN,
    URL_GET_USER_DATA,
    URL_GET_PAGINATED,
    URL_GET_COUNTRIES,
    URL_TRANZACTII,
    URL_DETALII_TRANZACTIE,
    URL_TRECERI_POD,
)

_LOGGER = logging.getLogger(__name__)


class ErovinietaAPI:
    TOKEN_VALIDITY_SECONDS = 3600  # Durata de valabilitate a token-ului în secunde

    def __init__(self, username: str, password: str) -> None:
        """Inițializează API-ul Erovinieta."""
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.token: str | None = None
        self.token_acquired_time: datetime | None = None

    # -------------------------------------------------------------------------
    #                 Autentificare
    # -------------------------------------------------------------------------
    def is_authenticated(self) -> bool:
        """Verifică dacă token-ul este valid și nu a expirat."""
        if self.token is None or self.token_acquired_time is None:
            return False
        elapsed_time = (datetime.now() - self.token_acquired_time).total_seconds()
        return elapsed_time < self.TOKEN_VALIDITY_SECONDS - 60

    def authenticate(self) -> None:
        """Autentifică utilizatorul și stochează cookie-ul JSESSIONID."""
        _LOGGER.debug("Inițiem procesul de autentificare pentru utilizatorul %s", self.username)
        payload = {
            "username": self.username,
            "password": self.password,
            "_spring_security_remember_me": "on",
        }

        self.session.cookies.clear()

        try:
            response = self.session.post(URL_LOGIN, json=payload, timeout=10)
            _LOGGER.debug("Răspuns la autentificare: %s", response.text)
            response.raise_for_status()
        except requests.RequestException as e:
            _LOGGER.error("Cerere de autentificare eșuată: %s", e)
            self.token = None
            self.token_acquired_time = None
            raise Exception("Autentificare eșuată.") from e

        if response.status_code == 200:
            self.token = self.session.cookies.get("JSESSIONID")
            if not self.token:
                _LOGGER.error("JSESSIONID nu a fost găsit în cookie-uri.")
                raise Exception("Autentificare eșuată: JSESSIONID lipsă.")
            self.token_acquired_time = datetime.now()
            _LOGGER.info("Autentificarea a reușit pentru %s", self.username)
        else:
            _LOGGER.error("Eroare la autentificare: %s", response.text)
            raise Exception("Autentificare eșuată.")

    # -------------------------------------------------------------------------
    #                 Metodă de bază pentru cererile HTTP
    # -------------------------------------------------------------------------
    def _request(self, method: str, url: str, payload=None, headers=None, reauth: bool = True):
        """Execută o cerere HTTP cu verificarea autentificării."""
        if not self.is_authenticated():
            _LOGGER.info("Token inexistent sau expirat. Autentificare în curs...")
            self.authenticate()

        resp_data, status_code, resp_text = self._do_request(method, url, payload, headers)

        if (status_code in [401, 403] or resp_data is None) and reauth:
            _LOGGER.info("Token expirat sau răspuns gol. Reîncercăm autentificarea...")
            self.authenticate()
            resp_data, status_code, resp_text = self._do_request(method, url, payload, headers)

        if status_code != 200 or resp_data is None:
            _LOGGER.error(
                "Eroare API: [%s] %s. Răspuns gol sau invalid.", status_code, resp_text
            )
            raise Exception(f"Eroare API: {status_code}, răspuns gol sau invalid.")

        return resp_data

    def _do_request(self, method: str, url: str, payload=None, headers=None):
        """Execută cererea HTTP."""
        if headers is None:
            headers = {}
        if self.token:
            self.session.cookies.set("JSESSIONID", self.token, path="/")

        _LOGGER.debug("Cerere HTTP [%s] către %s, payload=%s", method, url, payload)
        try:
            response = self.session.request(
                method, url, json=payload, headers=headers, timeout=10
            )
        except requests.RequestException as e:
            _LOGGER.error("Cerere HTTP eșuată: %s", e)
            return None, None, str(e)

        try:
            data = response.json()
        except JSONDecodeError:
            _LOGGER.error(
                "Răspunsul de la server nu este JSON valid. Răspuns text: %s",
                response.text,
            )
            data = None

        return data, response.status_code, response.text

    # -------------------------------------------------------------------------
    #                 Metode Helper
    # -------------------------------------------------------------------------
    def _generate_timestamp_url(self, base_url: str, is_first_param: bool = True) -> str:
        """Adaugă timestamp la URL."""
        timestamp = int(datetime.now().timestamp() * 1000)
        separator = "?" if is_first_param else "&"
        return f"{base_url}{separator}timestamp={timestamp}"

    # -------------------------------------------------------------------------
    #                 Metode Publice (Accesate de integrare)
    # -------------------------------------------------------------------------
    def get_user_data(self):
        """Obține detalii despre utilizator."""
        url = self._generate_timestamp_url(URL_GET_USER_DATA)
        _LOGGER.debug("Cerere către URL-ul utilizator: %s", url)
        return self._request("GET", url)

    def get_paginated_data(self, limit: int = 20, page: int = 0):
        """Obține date paginate."""
        base_url = f"{URL_GET_PAGINATED}?limit={limit}&page={page}"
        url = self._generate_timestamp_url(base_url, is_first_param=False)
        _LOGGER.debug("Cerere către URL-ul paginat: %s", url)
        return self._request("GET", url)

    def get_countries(self):
        """Obține lista țărilor."""
        _LOGGER.debug("Cerere către URL-ul țărilor: %s", URL_GET_COUNTRIES)
        return self._request("GET", URL_GET_COUNTRIES)

    def get_tranzactii(self, date_from: int, date_to: int):
        """Obține lista de tranzacții."""
        url = URL_TRANZACTII.format(dateFrom=date_from, dateTo=date_to)
        _LOGGER.debug("Cerere către URL-ul tranzacțiilor: %s", url)
        return self._request("GET", url)

    def get_detalii_tranzactie(self, series: str):
        """Obține detalii pentru o tranzacție."""
        url = URL_DETALII_TRANZACTIE.format(series=series)
        _LOGGER.debug("Cerere către URL-ul detaliilor tranzacției: %s", url)
        return self._request("GET", url)

    def get_treceri_pod(
        self, vin: str, plate_no: str, certificate_series: str, period: int = 4
    ):
        """Obține istoricul trecerilor de pod."""
        url = URL_TRECERI_POD
        payload = {
            "vin": vin,
            "plateNo": plate_no,
            "certificateSeries": certificate_series,
            "vehicleFleetEntity": {
                "certificateSeries": certificate_series,
                "plateNo": plate_no,
                "vin": vin,
            },
            "period": period,
        }
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
        }
        _LOGGER.debug("Cerere către trecerile de pod: %s cu payload: %s", url, payload)
        return self._request("POST", url, payload=payload, headers=headers)
