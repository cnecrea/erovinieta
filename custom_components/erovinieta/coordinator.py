"""Coordinator pentru integrarea CNAIR eRovinieta."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import ErovinietaAPI
from .const import (
    CONF_ISTORIC_TRANZACTII,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ISTORIC_TRANZACTII_DEFAULT,
    LICENSE_DATA_KEY,
)
from .exceptions import ErovinietaAuthError, ErovinietaConnectionError
from .helpers import safe_get

_LOGGER = logging.getLogger(__name__)


class ErovinietaCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator centralizat pentru datele din API-ul eRovinieta."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: ErovinietaAPI,
        config_entry: ConfigEntry,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Inițializează coordinatorul."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=update_interval),
            config_entry=config_entry,
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        """Actualizează datele periodic prin apeluri API.

        Convertește excepțiile de autentificare în ConfigEntryAuthFailed
        (declanșează reauth flow) și cele de conexiune în UpdateFailed
        (declanșează retry automat).
        """
        # Verificare licență — nu fetchuim date dacă licența/trial nu e validă
        license_mgr = self.hass.data.get(DOMAIN, {}).get(LICENSE_DATA_KEY)
        if license_mgr and not license_mgr.is_valid:
            _LOGGER.debug("[eRovinieta] Licență invalidă — se omit apelurile API")
            return self.data or {}

        try:
            return await self._fetch_all_data()
        except ErovinietaAuthError as err:
            raise ConfigEntryAuthFailed(
                f"Autentificare eșuată: {err}"
            ) from err
        except ErovinietaConnectionError as err:
            raise UpdateFailed(
                f"Eroare de conexiune: {err}"
            ) from err
        except Exception as err:
            raise UpdateFailed(
                f"Eroare neașteptată la actualizarea datelor: {err}"
            ) from err

    async def _fetch_all_data(self) -> dict:
        """Obține toate datele necesare din API."""
        # 1. Date utilizator
        user_data = await self._safe_fetch(
            self.api.get_user_data, {}, "date utilizator"
        )

        # 2. Date paginate (vehicule)
        paginated_data = await self._safe_fetch(
            self.api.get_paginated_data, {}, "date vehicule"
        )
        vehicule = [
            safe_get(v.get("entity"), {})
            for v in safe_get(paginated_data.get("view"), [])
        ]

        # 3. Lista de țări
        countries_data = await self._safe_fetch(
            self.api.get_countries, [], "lista de țări"
        )

        # 4. Treceri de pod — per vehicul
        treceri_per_vehicul: dict[str, list] = {}
        for vehicul in vehicule:
            vin = safe_get(vehicul.get("vin"))
            plate_no = safe_get(vehicul.get("plateNo"))
            cert = safe_get(vehicul.get("certificateSeries"))
            if not all([vin, plate_no, cert]):
                continue

            try:
                result = await self.api.get_treceri_pod(vin, plate_no, cert)
                treceri_per_vehicul[plate_no] = safe_get(
                    result.get("detectionList"), []
                )
            except ErovinietaAuthError:
                raise  # Propagăm erori de autentificare
            except Exception as err:
                _LOGGER.warning(
                    "Eroare la obținerea trecerilor pentru %s: %s", plate_no, err
                )
                treceri_per_vehicul[plate_no] = []

        # 5. Tranzacții
        istoric = self.config_entry.options.get(
            CONF_ISTORIC_TRANZACTII, ISTORIC_TRANZACTII_DEFAULT
        )
        now = datetime.now()
        date_from = int(
            (now - timedelta(days=istoric * 365)).timestamp() * 1000
        )
        date_to = int(now.timestamp() * 1000)

        try:
            tx_result = await self.api.get_tranzactii(date_from, date_to)
            transactions = safe_get(tx_result.get("view"), [])
        except ErovinietaAuthError:
            raise
        except Exception as err:
            _LOGGER.warning("Eroare la obținerea tranzacțiilor: %s", err)
            transactions = []

        _LOGGER.debug(
            "Actualizare completă: %d vehicule, %d treceri pod, %d tranzacții",
            len(vehicule),
            sum(len(v) for v in treceri_per_vehicul.values()),
            len(transactions),
        )

        return {
            "user_data": user_data,
            "paginated_data": paginated_data,
            "countries_data": countries_data,
            "transactions": transactions,
            "treceri_pod_per_vehicul": treceri_per_vehicul,
        }

    async def _safe_fetch(self, func, default, name: str):
        """Execută un apel API cu protecție la erori.

        Erorile de autentificare sunt propagate (declanșează reauth).
        Restul erorilor sunt loggate și returnează valoarea implicită.
        """
        try:
            return await func()
        except ErovinietaAuthError:
            raise
        except Exception as err:
            _LOGGER.warning("Eroare la obținerea %s: %s", name, err)
            return default
