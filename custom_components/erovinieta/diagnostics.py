"""
Diagnosticare pentru integrarea CNAIR eRovinieta.

Exportă informații de diagnostic pentru support tickets:
- Licență (fingerprint, status, cheie mascată)
- Coordinator și date statistice
- Starea senzorilor

Datele sensibile (parolă, token-uri) sunt excluse.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, LICENSE_DATA_KEY


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Returnează datele de diagnostic pentru CNAIR eRovinieta."""

    # ── Licență (fingerprint + cheie mascată) ──
    license_mgr = hass.data.get(DOMAIN, {}).get(LICENSE_DATA_KEY)
    licenta_info: dict[str, Any] = {}
    if license_mgr:
        licenta_info = {
            "fingerprint": license_mgr.fingerprint,
            "status": license_mgr.status,
            "license_key": license_mgr.license_key_masked,
            "is_valid": license_mgr.is_valid,
            "license_type": license_mgr.license_type,
        }

    # ── Coordinator ──
    coordinator_info: dict[str, Any] = {}
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator:
        coordinator_info = {
            "last_update_success": coordinator.last_update_success,
        }
        if coordinator.data:
            paginated = coordinator.data.get("paginated_data", {}).get("view", [])
            treceri = coordinator.data.get("treceri_pod_per_vehicul", {})
            transactions = coordinator.data.get("transactions", [])
            coordinator_info.update({
                "vehicule_count": len(paginated),
                "treceri_per_vehicul": {
                    plate: len(detections)
                    for plate, detections in treceri.items()
                },
                "transactions_count": len(transactions),
            })

    # ── Senzori activi ──
    senzori_activi = sorted(
        entitate.entity_id
        for entitate in hass.states.async_all("sensor")
        if entitate.entity_id.startswith(f"sensor.{DOMAIN}_")
    )

    # ── Config entry (fără date sensibile) ──
    return {
        "intrare": {
            "titlu": entry.title,
            "versiune": entry.version,
            "domeniu": DOMAIN,
            "username": _mascheaza_email(entry.data.get("username", "")),
            "update_interval": entry.data.get("update_interval"),
        },
        "licenta": licenta_info,
        "coordinator": coordinator_info,
        "stare": {
            "senzori_activi": len(senzori_activi),
            "lista_senzori": senzori_activi,
        },
    }


def _mascheaza_email(email: str) -> str:
    """Maschează email-ul păstrând prima literă și domeniul."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}{'*' * (len(local) - 1)}@{domain}"
