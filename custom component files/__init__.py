"""PocketSmith Integration."""
import logging
from homeassistant.helpers import discovery
from homeassistant.core import HomeAssistant
from .const import DOMAIN  # Import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the PocketSmith component."""
    hass.data.setdefault(DOMAIN, {})
    if DOMAIN in config:
        developer_key = config[DOMAIN].get("developer_key")
        hass.data[DOMAIN] = {"developer_key": developer_key}
        await discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    return True
