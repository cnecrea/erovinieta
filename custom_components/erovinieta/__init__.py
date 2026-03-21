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
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .api import ErovinietaAPI
from .const import (
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    LICENSE_DATA_KEY,
    PLATFORMS,
)
from .coordinator import ErovinietaCoordinator
from .exceptions import ErovinietaAuthError, ErovinietaConnectionError
from .license import LicenseManager

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setează integrarea (doar config entry, fără YAML)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurează integrarea dintr-o intrare de configurare."""
    hass.data.setdefault(DOMAIN, {})

    # ── Inițializare License Manager (o singură instanță per domeniu) ──
    if LICENSE_DATA_KEY not in hass.data[DOMAIN]:
        _LOGGER.debug("[eRovinieta] Inițializez LicenseManager (prima entry)")
        license_mgr = LicenseManager(hass)
        await license_mgr.async_load()
        hass.data[DOMAIN][LICENSE_DATA_KEY] = license_mgr
        _LOGGER.debug(
            "[eRovinieta] LicenseManager: status=%s, valid=%s, fingerprint=%s...",
            license_mgr.status,
            license_mgr.is_valid,
            license_mgr.fingerprint[:16],
        )

        # Heartbeat periodic — intervalul vine de la server (via valid_until)
        interval_sec = license_mgr.check_interval_seconds
        _LOGGER.debug(
            "[eRovinieta] Programez heartbeat periodic la fiecare %d secunde (%d ore)",
            interval_sec,
            interval_sec // 3600,
        )

        async def _heartbeat_periodic(_now) -> None:
            """Verifică statusul la server dacă cache-ul a expirat."""
            mgr: LicenseManager | None = hass.data.get(DOMAIN, {}).get(
                LICENSE_DATA_KEY
            )
            if not mgr:
                _LOGGER.debug("[eRovinieta] Heartbeat: LicenseManager nu există, skip")
                return
            if mgr.needs_heartbeat:
                _LOGGER.debug("[eRovinieta] Heartbeat: cache expirat, verific la server")
                await mgr.async_heartbeat()
            else:
                _LOGGER.debug("[eRovinieta] Heartbeat: cache valid, nu e nevoie de verificare")

        cancel_heartbeat = async_track_time_interval(
            hass,
            _heartbeat_periodic,
            timedelta(seconds=interval_sec),
        )
        hass.data[DOMAIN]["_cancel_heartbeat"] = cancel_heartbeat
        _LOGGER.debug("[eRovinieta] Heartbeat programat și stocat în hass.data")

        # ── Notificare re-enable (dacă a fost dezactivată anterior) ──
        was_disabled = hass.data.pop(f"{DOMAIN}_was_disabled", False)
        if was_disabled:
            await license_mgr.async_notify_event("integration_enabled")

        if not license_mgr.is_valid:
            _LOGGER.warning(
                "[eRovinieta] Integrarea nu are licență validă. "
                "Senzorii vor afișa 'Licență necesară'."
            )
        elif license_mgr.is_trial_valid:
            _LOGGER.info(
                "[eRovinieta] Perioadă de evaluare — %d zile rămase",
                license_mgr.trial_days_remaining,
            )
        else:
            _LOGGER.info(
                "[eRovinieta] Licență activă — tip: %s",
                license_mgr.license_type,
            )
    else:
        _LOGGER.debug(
            "[eRovinieta] LicenseManager există deja (entry suplimentară)"
        )

    # ── Setup API + Coordinator (logica originală) ──
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
    _LOGGER.info(
        "[eRovinieta] ── async_unload_entry ── entry_id=%s (%s)",
        entry.entry_id,
        entry.data.get(CONF_USERNAME),
    )

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
    _LOGGER.debug("[eRovinieta] Unload platforme: %s", "OK" if unload_ok else "EȘUAT")

    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        coordinator: ErovinietaCoordinator = hass.data[DOMAIN].pop(
            entry.entry_id
        )
        await coordinator.api.close()

        # Verifică dacă mai sunt entry-uri active
        entry_ids_ramase = {
            e.entry_id
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        }

        _LOGGER.debug(
            "[eRovinieta] Entry-uri rămase după unload: %d (%s)",
            len(entry_ids_ramase),
            entry_ids_ramase or "niciuna",
        )

        if not entry_ids_ramase:
            _LOGGER.info("[eRovinieta] Ultima entry descărcată — curăț domeniul complet")

            # ── Notificare lifecycle (înainte de cleanup!) ──
            mgr = hass.data[DOMAIN].get(LICENSE_DATA_KEY)
            if mgr and not hass.is_stopping:
                if entry.disabled_by:
                    await mgr.async_notify_event("integration_disabled")
                    # Flag pentru async_setup_entry: la re-enable, trimitem "enabled"
                    hass.data[f"{DOMAIN}_was_disabled"] = True
                else:
                    # Salvăm fingerprint-ul pentru async_remove_entry
                    hass.data.setdefault(f"{DOMAIN}_notify", {}).update({
                        "fingerprint": mgr.fingerprint,
                        "license_key": mgr._data.get("license_key", ""),
                    })
                    _LOGGER.debug(
                        "[eRovinieta] Fingerprint salvat pentru async_remove_entry"
                    )

            # Oprește heartbeat-ul periodic
            cancel_hb = hass.data[DOMAIN].pop("_cancel_heartbeat", None)
            if cancel_hb:
                cancel_hb()
                _LOGGER.debug("[eRovinieta] Heartbeat periodic oprit")

            # Elimină LicenseManager
            hass.data[DOMAIN].pop(LICENSE_DATA_KEY, None)
            _LOGGER.debug("[eRovinieta] LicenseManager eliminat")

            # Elimină domeniul complet
            hass.data.pop(DOMAIN, None)
            _LOGGER.debug("[eRovinieta] hass.data[%s] eliminat complet", DOMAIN)

            _LOGGER.info("[eRovinieta] Cleanup complet — domeniul %s descărcat", DOMAIN)
        else:
            _LOGGER.info(
                "Integrarea eRovinieta a fost eliminată pentru %s",
                entry.data[CONF_USERNAME],
            )
    else:
        _LOGGER.error("[eRovinieta] Unload EȘUAT pentru entry_id=%s", entry.entry_id)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Curăță complet la ștergerea integrării.

    Dacă e ultima entry, notifică serverul de licențe.
    """
    _LOGGER.debug(
        "[eRovinieta] ── async_remove_entry ── entry_id=%s (%s)",
        entry.entry_id,
        entry.data.get(CONF_USERNAME),
    )

    # ── Notificare licență (doar la ultima entry) ──
    remaining = hass.config_entries.async_entries(DOMAIN)
    if not remaining:
        notify_data = hass.data.pop(f"{DOMAIN}_notify", None)
        if notify_data and notify_data.get("fingerprint"):
            await _send_lifecycle_event(
                hass,
                notify_data["fingerprint"],
                notify_data.get("license_key", ""),
                "integration_removed",
            )


async def _send_lifecycle_event(
    hass: HomeAssistant, fingerprint: str, license_key: str, action: str
) -> None:
    """Trimite un eveniment lifecycle direct (fără LicenseManager).

    Folosit în async_remove_entry când LicenseManager nu mai există.
    """
    import hashlib
    import hmac as hmac_lib
    import json
    import time

    from .license import INTEGRATION, LICENSE_API_URL

    timestamp = int(time.time())
    payload = {
        "fingerprint": fingerprint,
        "timestamp": timestamp,
        "action": action,
        "license_key": license_key,
        "integration": INTEGRATION,
    }
    data = {k: v for k, v in payload.items() if k != "hmac"}
    msg = json.dumps(data, sort_keys=True).encode()
    payload["hmac"] = hmac_lib.new(
        fingerprint.encode(), msg, hashlib.sha256
    ).hexdigest()

    try:
        session = async_get_clientsession(hass)
        async with session.post(
            f"{LICENSE_API_URL}/notify",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "eRovinieta-HA-Integration/3.0",
            },
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                if not result.get("success"):
                    _LOGGER.warning(
                        "[eRovinieta] Server a refuzat '%s': %s",
                        action, result.get("error"),
                    )
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("[eRovinieta] Nu s-a putut raporta '%s': %s", action, err)
