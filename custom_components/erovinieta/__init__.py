"""Integrare CNAIR eRovinieta pentru Home Assistant.

Oferă senzori pentru:
- Date utilizator
- Stare rovinietă per vehicul
- Treceri pod (istoric + restanțe)
- Sold peaje neexpirate
- Raport tranzacții
"""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .api import ErovinietaAPI
from .const import (
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import ErovinietaCoordinator
from .exceptions import ErovinietaAuthError, ErovinietaConnectionError

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setează integrarea (doar config entry, fără YAML)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurează integrarea dintr-o intrare de configurare."""
    session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30)
    )
    api = ErovinietaAPI(
        session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )

    # Autentificare inițială
    try:
        await api.authenticate()
    except ErovinietaAuthError as err:
        await api.close()
        raise ConfigEntryAuthFailed(
            f"Autentificare eșuată: {err}"
        ) from err
    except (ErovinietaConnectionError, Exception) as err:
        await api.close()
        raise ConfigEntryNotReady(
            f"Serviciul eRovinieta nu este disponibil: {err}"
        ) from err

    # Configurare coordinator
    update_interval = entry.options.get(
        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
    )
    coordinator = ErovinietaCoordinator(
        hass, api, config_entry=entry, update_interval=update_interval
    )

    # Prima actualizare a datelor
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await api.close()
        raise

    # Stocăm coordinatorul
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Configurăm platformele
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listener pentru schimbări de opțiuni
    entry.async_on_unload(entry.add_update_listener(async_update_entry))

    _LOGGER.info(
        "Integrarea eRovinieta a fost configurată pentru %s",
        entry.data[CONF_USERNAME],
    )
    return True


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Aplică modificările de opțiuni (interval, istoric)."""
    coordinator: ErovinietaCoordinator = hass.data[DOMAIN][entry.entry_id]

    update_interval = entry.options.get(
        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
    )
    coordinator.update_interval = timedelta(seconds=update_interval)

    _LOGGER.debug(
        "Interval de actualizare modificat la %s secunde.", update_interval
    )
    await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Dezinstalează integrarea și eliberează resursele."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        coordinator: ErovinietaCoordinator = hass.data[DOMAIN].pop(
            entry.entry_id
        )
        await coordinator.api.close()
        _LOGGER.info(
            "Integrarea eRovinieta a fost eliminată pentru %s",
            entry.data[CONF_USERNAME],
        )

    return unload_ok
