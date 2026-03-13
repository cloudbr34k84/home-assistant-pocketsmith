"""PocketSmith Integration."""
import logging
import aiohttp
import async_timeout
from homeassistant.helpers import discovery
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
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

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PocketSmith from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session = aiohttp.ClientSession()  # Create a reusable session for HTTP requests
    developer_key = entry.data.get("developer_key")
    hass.data[DOMAIN] = {
        "developer_key": developer_key,
        "session": session,
    }

    try:
        # Adding a timeout for initial data fetch if necessary
        async with async_timeout.timeout(10):
            # Place any initial API call or data fetching here
            _LOGGER.debug("Fetching initial data from PocketSmith...")
            # Assuming there's some initial API call that can be performed here
            # await some_api_fetch_function(session, developer_key)

    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        _LOGGER.error(f"Error occurred while fetching data from PocketSmith: {err}")
        return False

    # Load platforms related to the integration (like sensors)
    hass.async_create_task(
        discovery.async_load_platform(hass, "sensor", DOMAIN, {}, entry)
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle unloading of an entry."""
    if DOMAIN in hass.data:
        session = hass.data[DOMAIN].get("session")
        if session:
            await session.close()  # Properly close the aiohttp session
        hass.data.pop(DOMAIN)
    return True
