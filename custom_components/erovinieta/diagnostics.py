"""Suport diagnostice pentru integrarea CNAIR eRovinieta.

Furnizează informații de debug cu date sensibile redactate automat.
Accesibil din Setări → Integrări → eRovinieta → Diagnostice.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ErovinietaCoordinator
from .helpers import redact_data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Returnează datele de diagnostic pentru o intrare de configurare."""
    coordinator: ErovinietaCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Redactăm datele sensibile din configurare
    entry_data = {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "data": redact_data(dict(entry.data)),
        "options": dict(entry.options),
        "version": entry.version,
    }

    # Redactăm datele sensibile din coordinator
    coordinator_data = {}
    if coordinator.data:
        coordinator_data = redact_data(coordinator.data)

    # Statistici (ne-sensibile)
    stats = {}
    if coordinator.data:
        paginated = coordinator.data.get("paginated_data", {}).get("view", [])
        treceri = coordinator.data.get("treceri_pod_per_vehicul", {})
        transactions = coordinator.data.get("transactions", [])

        stats = {
            "vehicule_count": len(paginated),
            "treceri_per_vehicul": {
                plate: len(detections)
                for plate, detections in treceri.items()
            },
            "transactions_count": len(transactions),
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
        }

    return {
        "config_entry": entry_data,
        "coordinator_data": coordinator_data,
        "statistics": stats,
    }
