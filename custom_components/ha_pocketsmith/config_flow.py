"""Config flow for PocketSmith."""
import asyncio
import logging

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_PERIOD,
    CONF_INTERVAL,
    DEFAULT_PERIOD,
    DEFAULT_INTERVAL,
    PERIOD_OPTIONS,
    INTERVAL_OPTIONS,
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


class PocketSmithConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the PocketSmith UI setup flow."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return PocketSmithOptionsFlow(config_entry)

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


class PocketSmithOptionsFlow(config_entries.OptionsFlow):
    """Handle PocketSmith options (period and interval)."""

    def __init__(self, config_entry) -> None:
        """Initialise the options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Show the options form."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_period = self._config_entry.options.get(CONF_PERIOD, DEFAULT_PERIOD)
        current_interval = self._config_entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PERIOD, default=current_period): vol.In(PERIOD_OPTIONS),
                    vol.Required(CONF_INTERVAL, default=current_interval): vol.In(INTERVAL_OPTIONS),
                }
            ),
        )
