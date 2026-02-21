"""Punctul de inițializare pentru integrarea CNAIR eRovinieta."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .api import ErovinietaAPI
from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .coordinator import ErovinietaCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setează integrarea folosind configuration.yaml (nu este utilizat)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setează integrarea folosind ConfigFlow."""
    _LOGGER.info(
        "Configurăm integrarea CNAIR eRovinieta pentru utilizatorul %s",
        entry.data["username"],
    )

    # Creează instanța API și autentifică
    api = ErovinietaAPI(entry.data["username"], entry.data["password"])
    try:
        await hass.async_add_executor_job(api.authenticate)
    except Exception as e:
        _LOGGER.error(
            "Eroare la autentificarea utilizatorului %s: %s",
            entry.data["username"],
            e,
        )
        return False

    # Obține intervalul de actualizare
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    # Creează coordinatorul — cu config_entry (necesar HA 2025.x)
    coordinator = ErovinietaCoordinator(
        hass, api, config_entry=entry, update_interval=update_interval
    )
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.error("Eroare la actualizarea inițială a datelor: %s", e)
        return False

    # Adaugă coordinatorul în Home Assistant
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    # Configurează platformele
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Înregistrează ascultătorul pentru actualizări de opțiuni
    entry.async_on_unload(entry.add_update_listener(async_update_entry))

    return True


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Aplică modificările aduse opțiunilor."""
    _LOGGER.info("Actualizăm opțiunile pentru integrarea Erovinieta.")

    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    coordinator: ErovinietaCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    coordinator.update_interval = timedelta(seconds=update_interval)
    _LOGGER.info("Intervalul de actualizare a fost setat la %s secunde.", update_interval)

    await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Elimină integrarea."""
    _LOGGER.info(
        "Eliminăm integrarea Erovinieta pentru utilizatorul %s",
        entry.data["username"],
    )

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
