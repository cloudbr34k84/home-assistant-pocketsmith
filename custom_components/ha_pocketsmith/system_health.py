"""System health for the PocketSmith integration."""
from typing import Any

from homeassistant.components import system_health
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@callback
def async_register(hass: HomeAssistant, register: system_health.SystemHealthRegistration) -> None:
    """Register system health callbacks."""
    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Return system health info for PocketSmith."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return {"api_reachable": False}

    entry = entries[0]
    try:
        coordinator = hass.data[DOMAIN][entry.entry_id]
    except KeyError:
        return {"api_reachable": False}

    return {
        "api_reachable": system_health.async_check_can_reach_url(
            hass, "https://api.pocketsmith.com/v2/me"
        ),
        "last_activity_at": coordinator.data.get("user", {}).get("last_activity_at"),
        "forecast_needs_recalculate": coordinator.data.get("user", {}).get(
            "forecast_needs_recalculate"
        ),
    }
