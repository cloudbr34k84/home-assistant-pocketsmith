"""Config flow for PocketSmith."""
import asyncio
import logging

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ENABLE_BACKFILL,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_ENABLE_BACKFILL,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
_API_ME = "https://api.pocketsmith.com/v2/me"
_TIMEOUT = 10


async def _validate_developer_key(hass, developer_key: str) -> None:
    """Raise ValueError on bad key, aiohttp.ClientError on network failure."""
    headers = {
        "Accept": "application/json",
        "Authorization": "Key %s" % developer_key,
    }
    session = async_get_clientsession(hass)
    async with asyncio.timeout(_TIMEOUT):
        async with session.get(_API_ME, headers=headers) as response:
            if response.status == 401:
                raise ValueError("invalid_auth")
            if response.status == 403:
                raise ValueError("insufficient_permissions")
            response.raise_for_status()


class PocketSmithOptionsFlow(config_entries.OptionsFlow):
    """Handle PocketSmith options."""

    async def async_step_init(self, user_input=None):
        """Show the options form."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options
        schema = vol.Schema({
            vol.Required(
                CONF_UPDATE_INTERVAL_HOURS,
                default=current.get(CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS),
            ): vol.All(int, vol.Range(min=1, max=24)),
            vol.Required(
                CONF_ENABLE_BACKFILL,
                default=current.get(CONF_ENABLE_BACKFILL, DEFAULT_ENABLE_BACKFILL),
            ): bool,
        })

        return self.async_show_form(step_id="init", data_schema=schema)


class PocketSmithConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the PocketSmith UI setup flow."""

    VERSION = 2
    MINOR_VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return PocketSmithOptionsFlow()

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors = {}
        if user_input is not None:
            try:
                await _validate_developer_key(self.hass, user_input["developer_key"])
            except ValueError as err:
                errors["base"] = str(err)
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except asyncio.TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during PocketSmith config flow")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="PocketSmith",
                    data={"developer_key": user_input["developer_key"]},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("developer_key"): str}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        """Handle re-authentication when the developer key is rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Handle re-authentication confirmation."""
        errors = {}
        if user_input is not None:
            try:
                await _validate_developer_key(self.hass, user_input["developer_key"])
            except ValueError as err:
                errors["base"] = str(err)
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except asyncio.TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during PocketSmith reauth")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self._get_reauth_entry(),
                    data={"developer_key": user_input["developer_key"]},
                )
                await self.hass.config_entries.async_reload(self._get_reauth_entry().entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("developer_key"): str}),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        """Allow the user to update their developer key from the 3-dot menu."""
        errors = {}
        if user_input is not None:
            try:
                await _validate_developer_key(self.hass, user_input["developer_key"])
            except ValueError as err:
                errors["base"] = str(err)
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except asyncio.TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during PocketSmith reconfigure")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self._get_reconfigure_entry(),
                    data={"developer_key": user_input["developer_key"]},
                )
                await self.hass.config_entries.async_reload(self._get_reconfigure_entry().entry_id)
                return self.async_abort(reason="reconfigure_successful")

        entry = self._get_reconfigure_entry()
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required("developer_key", default=entry.data.get("developer_key", "")): str,
            }),
            errors=errors,
        )
