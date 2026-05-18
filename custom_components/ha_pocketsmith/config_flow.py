"""Config flow for PocketSmith."""
import asyncio
import logging

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

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


class PocketSmithConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the PocketSmith UI setup flow."""

    VERSION = 2
    MINOR_VERSION = 1

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
