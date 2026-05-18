"""PocketSmith Integration."""
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv

from .backfill import async_trigger_backfill
from .const import (
    CONF_ENABLE_BACKFILL,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_ENABLE_BACKFILL,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
)
from .coordinator import PocketSmithCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type PocketSmithConfigEntry = ConfigEntry[PocketSmithCoordinator]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry versions to the current schema."""
    _LOGGER.debug("Migrating PocketSmith config entry from version %s.%s", entry.version, entry.minor_version)

    if entry.version == 1:
        # v1 → v2: no data changes; version bump establishes migration scaffold.
        hass.config_entries.async_update_entry(entry, version=2, minor_version=1)
        _LOGGER.info("Migrated PocketSmith config entry to version 2.1")

    return True


def _update_interval_from_options(entry: ConfigEntry) -> timedelta:
    """Return the polling interval from options, falling back to the default."""
    hours = entry.options.get(CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS)
    return timedelta(hours=hours)


async def async_setup_entry(hass: HomeAssistant, entry: PocketSmithConfigEntry) -> bool:
    """Set up PocketSmith from a config entry."""
    coordinator = PocketSmithCoordinator(
        hass,
        developer_key=entry.data["developer_key"],
        update_interval=_update_interval_from_options(entry),
        entry=entry,
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await async_trigger_backfill(hass, coordinator, coordinator.data, entry)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


async def _async_options_updated(hass: HomeAssistant, entry: PocketSmithConfigEntry) -> None:
    """Handle options updates — adjust coordinator interval and re-trigger backfill if needed."""
    coordinator: PocketSmithCoordinator = entry.runtime_data

    new_interval = _update_interval_from_options(entry)
    if coordinator.update_interval != new_interval:
        _LOGGER.debug(
            "PocketSmith polling interval changed to %s hours",
            entry.options.get(CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS),
        )
        coordinator.update_interval = new_interval

    if entry.options.get(CONF_ENABLE_BACKFILL, DEFAULT_ENABLE_BACKFILL):
        await async_trigger_backfill(hass, coordinator, coordinator.data, entry)


async def async_unload_entry(hass: HomeAssistant, entry: PocketSmithConfigEntry) -> bool:
    """Handle unloading of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
