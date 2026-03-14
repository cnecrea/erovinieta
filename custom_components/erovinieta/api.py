"""Manager API async pentru integrarea CNAIR eRovinieta.

Folosește aiohttp pentru apeluri HTTP native async,
eliminând necesitatea async_add_executor_job.
"""

from __future__ import annotations

import logging
import time

import aiohttp
from yarl import URL

from .const import (
    TOKEN_VALIDITY_SECONDS,
    URL_DETALII_TRANZACTIE,
    URL_GET_COUNTRIES,
    URL_GET_PAGINATED,
    URL_GET_USER_DATA,
    URL_LOGIN,
    URL_TRANZACTII,
    URL_TRECERI_POD,
)
from .exceptions import (
    ErovinietaApiError,
    ErovinietaAuthError,
    ErovinietaConnectionError,
)

_LOGGER = logging.getLogger(__name__)


class ErovinietaAPI:
    """Client API async pentru serviciul CNAIR eRovinieta."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> None:
        """Inițializează clientul API."""
        self._session = session
        self._username = username
        self._password = password
        self._token_time: float = 0

    @property
    def authenticated(self) -> bool:
        """Verifică dacă sesiunea curentă este validă."""
        return (time.monotonic() - self._token_time) < TOKEN_VALIDITY_SECONDS

    # ------------------------------------------------------------------
    #  Autentificare
    # ------------------------------------------------------------------

    async def authenticate(self) -> None:
        """Autentifică utilizatorul și stochează cookie-ul JSESSIONID."""
        payload = {
            "username": self._username,
            "password": self._password,
            "_spring_security_remember_me": "on",
        }
        self._session.cookie_jar.clear()

        try:
            async with self._session.post(URL_LOGIN, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ErovinietaAuthError(
                        f"Autentificare eșuată (HTTP {resp.status}): {text[:200]}"
                    )
        except aiohttp.ClientError as err:
            raise ErovinietaConnectionError(
                f"Eroare de conexiune la autentificare: {err}"
            ) from err

        # Verificăm că JSESSIONID a fost setat de server
        cookies = self._session.cookie_jar.filter_cookies(URL(URL_LOGIN))
        if "JSESSIONID" not in cookies:
            raise ErovinietaAuthError(
                "Cookie-ul JSESSIONID nu a fost primit după autentificare."
            )

        self._token_time = time.monotonic()
        _LOGGER.debug("Autentificare reușită pentru %s", self._username)

    # ------------------------------------------------------------------
    #  Cereri HTTP
    # ------------------------------------------------------------------

    async def _ensure_auth(self) -> None:
        """Asigură autentificarea înainte de un apel API."""
        if not self.authenticated:
            await self.authenticate()

    async def _request(
        self,
        method: str,
        url: str,
        json_data: dict | None = None,
        headers: dict | None = None,
    ) -> dict | list:
        """Execută o cerere HTTP cu re-autentificare automată."""
        await self._ensure_auth()

        try:
            return await self._do_request(method, url, json_data, headers)
        except ErovinietaAuthError:
            _LOGGER.debug("Token expirat, re-autentificare...")
            await self.authenticate()
            return await self._do_request(method, url, json_data, headers)

    async def _do_request(
        self,
        method: str,
        url: str,
        json_data: dict | None = None,
        headers: dict | None = None,
    ) -> dict | list:
        """Execută efectiv cererea HTTP."""
        kwargs: dict = {}
        if json_data is not None:
            kwargs["json"] = json_data
        if headers is not None:
            kwargs["headers"] = headers

        try:
            async with self._session.request(method, url, **kwargs) as resp:
                if resp.status in (401, 403):
                    raise ErovinietaAuthError(f"HTTP {resp.status}")
                if resp.status != 200:
                    text = await resp.text()
                    raise ErovinietaApiError(
                        f"Eroare API (HTTP {resp.status}): {text[:200]}"
                    )

                data = await resp.json(content_type=None)
                if data is None:
                    raise ErovinietaApiError("Răspuns JSON gol de la server.")
                return data
        except aiohttp.ClientError as err:
            raise ErovinietaConnectionError(
                f"Cerere eșuată către {url}: {err}"
            ) from err

    # ------------------------------------------------------------------
    #  Helper intern
    # ------------------------------------------------------------------

    @staticmethod
    def _add_timestamp(base_url: str, first_param: bool = True) -> str:
        """Adaugă un timestamp unic la URL (cache-busting)."""
        ts = int(time.time() * 1000)
        sep = "?" if first_param else "&"
        return f"{base_url}{sep}timestamp={ts}"

    # ------------------------------------------------------------------
    #  Metode publice API
    # ------------------------------------------------------------------

    async def get_user_data(self) -> dict:
        """Obține datele utilizatorului."""
        url = self._add_timestamp(URL_GET_USER_DATA)
        return await self._request("GET", url)

    async def get_paginated_data(self, limit: int = 20, page: int = 0) -> dict:
        """Obține date paginate (vehicule)."""
        base = f"{URL_GET_PAGINATED}?limit={limit}&page={page}"
        url = self._add_timestamp(base, first_param=False)
        return await self._request("GET", url)

    async def get_countries(self) -> list:
        """Obține lista țărilor disponibile."""
        return await self._request("GET", URL_GET_COUNTRIES)

    async def get_tranzactii(self, date_from: int, date_to: int) -> dict:
        """Obține lista de tranzacții într-un interval de timp."""
        url = URL_TRANZACTII.format(dateFrom=date_from, dateTo=date_to)
        return await self._request("GET", url)

    async def get_detalii_tranzactie(self, series: str) -> dict:
        """Obține detaliile unei tranzacții specifice."""
        url = URL_DETALII_TRANZACTIE.format(series=series)
        return await self._request("GET", url)

    async def get_treceri_pod(
        self,
        vin: str,
        plate_no: str,
        certificate_series: str,
        period: int = 4,
    ) -> dict:
        """Obține istoricul trecerilor de pod pentru un vehicul."""
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
        return await self._request(
            "POST", URL_TRECERI_POD, json_data=payload, headers=headers
        )

    # ------------------------------------------------------------------
    #  Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Închide sesiunea HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()
