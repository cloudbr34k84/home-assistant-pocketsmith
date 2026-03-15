"""PocketSmith Integration."""
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import PocketSmithCoordinator

_LOGGER = logging.getLogger(__name__)
_UPDATE_INTERVAL = timedelta(hours=1)

PLATFORMS = ["sensor", "binary_sensor"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type PocketSmithConfigEntry = ConfigEntry[PocketSmithCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PocketSmithConfigEntry) -> bool:
    """Set up PocketSmith from a config entry."""
    coordinator = PocketSmithCoordinator(
        hass,
        developer_key=entry.data["developer_key"],
        update_interval=_UPDATE_INTERVAL,
        entry=entry,
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: PocketSmithConfigEntry) -> bool:
    """Handle unloading of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
