"""Excepții personalizate pentru integrarea CNAIR eRovinieta."""

from homeassistant.exceptions import HomeAssistantError


class ErovinietaError(HomeAssistantError):
    """Excepție de bază pentru integrarea eRovinieta."""


class ErovinietaAuthError(ErovinietaError):
    """Eroare de autentificare (credentiale invalide sau token expirat)."""


class ErovinietaConnectionError(ErovinietaError):
    """Eroare de conexiune la API-ul eRovinieta."""


class ErovinietaApiError(ErovinietaError):
    """Eroare generală la apelul API-ului eRovinieta."""
