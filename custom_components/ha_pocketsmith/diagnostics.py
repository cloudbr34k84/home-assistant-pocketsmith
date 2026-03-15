"""Diagnostics for the PocketSmith integration."""
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = ["developer_key"]
TO_REDACT_USER = ["email", "tell_a_friend_code"]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a PocketSmith config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data

    return {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "options": dict(entry.options),
        "user": async_redact_data(data.get("user", {}), TO_REDACT_USER),
        "accounts_count": len(data.get("accounts", [])),
        "categories_count": len(data.get("enriched_categories", [])),
        "budget_count": len(data.get("budget", [])),
    }
