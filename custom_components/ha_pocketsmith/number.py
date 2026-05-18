"""PocketSmith number platform — polling interval control."""
import logging

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS, DOMAIN
from .coordinator import PocketSmithCoordinator

_LOGGER = logging.getLogger(__name__)

POLLING_INTERVAL_DESCRIPTION = NumberEntityDescription(
    key="polling_interval",
    translation_key="polling_interval",
    icon="mdi:timer-cog-outline",
    entity_category=EntityCategory.CONFIG,
    native_min_value=1,
    native_max_value=24,
    native_step=1,
    mode=NumberMode.BOX,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PocketSmith number entities from a config entry."""
    coordinator: PocketSmithCoordinator = entry.runtime_data.coordinator
    async_add_entities([PocketSmithPollingIntervalNumber(coordinator, entry)])


class PocketSmithPollingIntervalNumber(CoordinatorEntity, NumberEntity):
    """Number entity that controls the polling interval for PocketSmith."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PocketSmithCoordinator, entry: ConfigEntry) -> None:
        """Initialise the number entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._user_id = coordinator.data["user_id"]
        self.entity_description = POLLING_INTERVAL_DESCRIPTION
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._user_id))},
            name="PocketSmith",
            manufacturer="PocketSmith",
            model="Cloud Integration",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def unique_id(self) -> str:
        """Return a stable unique ID."""
        return "pocketsmith_%s_polling_interval" % self._user_id

    @property
    def native_value(self) -> float:
        """Return the current polling interval from options."""
        return self._entry.options.get(CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS)

    async def async_set_native_value(self, value: float) -> None:
        """Persist the new polling interval to config entry options."""
        new_options = {**self._entry.options, CONF_UPDATE_INTERVAL_HOURS: int(value)}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        _LOGGER.debug("PocketSmith polling interval set to %s hours via number entity", int(value))
