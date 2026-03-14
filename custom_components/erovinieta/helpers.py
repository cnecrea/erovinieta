"""Funcții utilitare partajate pentru integrarea CNAIR eRovinieta."""

from __future__ import annotations

from typing import Any

from homeassistant.util import dt as dt_util


def format_timestamp_ms(timestamp_millis: int | float | None) -> str:
    """Formatează un timestamp în milisecunde în format YYYY-MM-DD HH:MM:SS.

    Folosește timezone-ul configurat în Home Assistant.
    Returnează string gol dacă timestamp-ul e invalid sau lipsește.
    """
    if not timestamp_millis or timestamp_millis <= 0:
        return ""
    try:
        dt = dt_util.utc_from_timestamp(timestamp_millis / 1000).astimezone(
            dt_util.DEFAULT_TIME_ZONE
        )
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError, OverflowError):
        return "Dată invalidă"


def safe_get(value: Any, default: Any = None) -> Any:
    """Returnează valoarea sau un fallback dacă e None sau string gol."""
    if value is None or value == "":
        return default
    return value


def sanitize_plate_no(plate_no: str) -> str:
    """Curăță un număr de înmatriculare pentru utilizare în ID-uri."""
    return plate_no.replace(" ", "_").lower()


def capitalize_name(name: str) -> str:
    """Capitalizează fiecare cuvânt dintr-un string."""
    if not name:
        return ""
    return " ".join(word.capitalize() for word in name.split())


def redact_data(data: Any, keys_to_redact: set[str] | None = None) -> Any:
    """Redactează date sensibile pentru diagnostice.

    Parcurge recursiv dict-uri și liste, înlocuind valorile
    corespunzătoare cheilor sensibile cu '**REDACTED**'.
    """
    if keys_to_redact is None:
        keys_to_redact = {
            "username",
            "password",
            "cnpCui",
            "email",
            "telefon",
            "adresa",
            "vin",
            "certificateSeries",
            "nume",
            "cont",
            "plateNo",
            "paymentPlateNo",
            "JSESSIONID",
        }

    if isinstance(data, dict):
        return {
            k: ("**REDACTED**" if k in keys_to_redact else redact_data(v, keys_to_redact))
            for k, v in data.items()
        }
    if isinstance(data, (list, tuple)):
        return [redact_data(item, keys_to_redact) for item in data]
    return data
