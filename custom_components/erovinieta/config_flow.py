"""ConfigFlow, OptionsFlow și ReconfigureFlow pentru CNAIR eRovinieta.

Flow-uri disponibile:
- ConfigFlow (async_step_user): configurare inițială cu credentiale
- ReauthFlow (async_step_reauth): re-autentificare automată (HA trigger)
- ReconfigureFlow (async_step_reconfigure): schimbare parolă (din meniu)
- OptionsFlow (async_step_init): interval actualizare + istoric tranzacții
"""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import ErovinietaAPI
from .const import (
    CONF_ISTORIC_TRANZACTII,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ISTORIC_TRANZACTII_DEFAULT,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)
from .exceptions import ErovinietaAuthError, ErovinietaConnectionError

_LOGGER = logging.getLogger(__name__)

# ------------------------------------------------------------------
#  Scheme reutilizabile (selectoare HA moderne)
# ------------------------------------------------------------------

SELECTOR_USERNAME = TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT))
SELECTOR_PASSWORD = TextSelector(
    TextSelectorConfig(type=TextSelectorType.PASSWORD)
)
SELECTOR_INTERVAL = NumberSelector(
    NumberSelectorConfig(
        min=MIN_UPDATE_INTERVAL,
        max=MAX_UPDATE_INTERVAL,
        step=60,
        unit_of_measurement="secunde",
        mode=NumberSelectorMode.BOX,
    )
)
SELECTOR_ISTORIC = NumberSelector(
    NumberSelectorConfig(
        min=1,
        max=10,
        step=1,
        unit_of_measurement="ani",
        mode=NumberSelectorMode.SLIDER,
    )
)


# =====================================================================
#  ConfigFlow
# =====================================================================


class ErovinietaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ConfigFlow pentru configurarea integrării eRovinieta."""

    VERSION = 1

    def __init__(self) -> None:
        """Inițializare."""
        self._reauth_entry: ConfigEntry | None = None

    # ------------------------------------------------------------------
    #  Configurare inițială
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configurare inițială — credentiale + setări."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # NumberSelector returnează float — convertim la int
            update_interval = int(
                user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            )
            istoric = int(
                user_input.get(CONF_ISTORIC_TRANZACTII, ISTORIC_TRANZACTII_DEFAULT)
            )

            # Testăm credentialele
            errors = await self._test_credentials(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )

            if not errors:
                # Prevenim duplicate pe același username
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"CNAIR eRovinieta ({user_input[CONF_USERNAME]})",
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    options={
                        CONF_UPDATE_INTERVAL: update_interval,
                        CONF_ISTORIC_TRANZACTII: istoric,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): SELECTOR_USERNAME,
                vol.Required(CONF_PASSWORD): SELECTOR_PASSWORD,
                vol.Required(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): SELECTOR_INTERVAL,
                vol.Required(
                    CONF_ISTORIC_TRANZACTII, default=ISTORIC_TRANZACTII_DEFAULT
                ): SELECTOR_ISTORIC,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    # ------------------------------------------------------------------
    #  Re-autentificare (declanșată automat de HA la ConfigEntryAuthFailed)
    # ------------------------------------------------------------------

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Punct de intrare pentru re-autentificare."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Formular re-autentificare — doar parola."""
        errors: dict[str, str] = {}

        if user_input is not None and self._reauth_entry is not None:
            username = self._reauth_entry.data[CONF_USERNAME]
            errors = await self._test_credentials(
                username, user_input[CONF_PASSWORD]
            )

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={
                        **self._reauth_entry.data,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
                await self.hass.config_entries.async_reload(
                    self._reauth_entry.entry_id
                )
                return self.async_abort(reason="reauth_successful")

        schema = vol.Schema(
            {vol.Required(CONF_PASSWORD): SELECTOR_PASSWORD}
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "username": (
                    self._reauth_entry.data.get(CONF_USERNAME, "")
                    if self._reauth_entry
                    else ""
                )
            },
        )

    # ------------------------------------------------------------------
    #  Reconfigurare (declanșată manual de utilizator din meniu)
    # ------------------------------------------------------------------

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Permite schimbarea parolei din meniul integrării."""
        entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        errors: dict[str, str] = {}

        if user_input is not None and entry is not None:
            username = entry.data[CONF_USERNAME]
            errors = await self._test_credentials(
                username, user_input[CONF_PASSWORD]
            )

            if not errors:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        schema = vol.Schema(
            {vol.Required(CONF_PASSWORD): SELECTOR_PASSWORD}
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "username": (
                    entry.data.get(CONF_USERNAME, "") if entry else ""
                )
            },
        )

    # ------------------------------------------------------------------
    #  Helper: testare credentiale
    # ------------------------------------------------------------------

    async def _test_credentials(
        self, username: str, password: str
    ) -> dict[str, str]:
        """Testează credentialele fără a păstra sesiunea."""
        errors: dict[str, str] = {}
        session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        try:
            api = ErovinietaAPI(session, username, password)
            await api.authenticate()
        except ErovinietaAuthError:
            errors["base"] = "authentication_failed"
        except ErovinietaConnectionError:
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception("Eroare neașteptată la testarea credentialelor")
            errors["base"] = "unknown"
        finally:
            await session.close()
        return errors

    # ------------------------------------------------------------------
    #  Options flow
    # ------------------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Returnează OptionsFlow-ul pentru integrare."""
        return ErovinietaOptionsFlow()


# =====================================================================
#  OptionsFlow
# =====================================================================


class ErovinietaOptionsFlow(config_entries.OptionsFlow):
    """OptionsFlow pentru setările integrării eRovinieta.

    self.config_entry este injectat automat de Home Assistant.
    IMPORTANT: Folosim vol.Required (nu Optional) pentru a evita
    checkbox-ul de enable/disable pe care HA îl randează la Optional.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configurare interval actualizare și istoric tranzacții."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # NumberSelector returnează float — convertim la int
            update_interval = int(
                user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            )
            istoric = int(
                user_input.get(
                    CONF_ISTORIC_TRANZACTII, ISTORIC_TRANZACTII_DEFAULT
                )
            )

            if (
                update_interval < MIN_UPDATE_INTERVAL
                or update_interval > MAX_UPDATE_INTERVAL
            ):
                errors[CONF_UPDATE_INTERVAL] = "invalid_update_interval"

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_UPDATE_INTERVAL: update_interval,
                        CONF_ISTORIC_TRANZACTII: istoric,
                    },
                )

        # vol.Required + default = câmp cu valoare pre-completată, FĂRĂ checkbox
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                    ),
                ): SELECTOR_INTERVAL,
                vol.Required(
                    CONF_ISTORIC_TRANZACTII,
                    default=self.config_entry.options.get(
                        CONF_ISTORIC_TRANZACTII, ISTORIC_TRANZACTII_DEFAULT
                    ),
                ): SELECTOR_ISTORIC,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
