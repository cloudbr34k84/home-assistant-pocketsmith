"""PocketSmith Integration."""
import logging
from homeassistant.helpers import discovery
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the PocketSmith component."""
    hass.data.setdefault(DOMAIN, {})
    if DOMAIN in config:
        developer_key = config[DOMAIN].get("developer_key")
        hass.data[DOMAIN] = {"developer_key": developer_key}
        await discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PocketSmith from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN] = {"developer_key": entry.data.get("developer_key")}
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle unloading of an entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok and DOMAIN in hass.data:
        hass.data.pop(DOMAIN)
    return unload_ok
