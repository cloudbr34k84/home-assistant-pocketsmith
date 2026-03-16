"""PocketSmith binary sensor platform."""
import logging
from datetime import datetime, timezone

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import PocketSmithCoordinator

from .sensor import _make_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PocketSmith binary sensors from a config entry."""
    coordinator: PocketSmithCoordinator = entry.runtime_data

    async_add_entities([
        PocketSmithOverBudgetBinarySensor(coordinator),
        PocketSmithForecastNeedsRecalculateBinarySensor(coordinator),
        PocketSmithHasUncategorisedBinarySensor(coordinator),
    ])


class PocketSmithOverBudgetBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that is on when any non-transfer category is over budget."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def device_info(self):
        """Return device info."""
        return _make_device_info(self.coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_over_budget" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "Pocketsmith Over Budget"

    def _over_budget_packages(self) -> list:
        """Return details of categories that are over budget this month."""
        result = []
        for cat in self.coordinator.data.get("enriched_categories", []):
            if not cat.get("over_budget"):
                continue
            result.append({
                "category_title": cat.get("category_title"),
                "parent_title": cat.get("parent_title"),
                "actual": cat.get("actual"),
                "budgeted": cat.get("budgeted"),
                "over_by": cat.get("over_by"),
                "percentage_used": cat.get("percentage_used"),
            })
        return result

    @property
    def is_on(self) -> bool:
        """Return True if any non-transfer package is over budget."""
        return len(self._over_budget_packages()) > 0

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:alert-circle" if self._over_budget_packages() else "mdi:check-circle"

    @property
    def extra_state_attributes(self) -> dict:
        """Return details of over-budget categories."""
        over_budget = self._over_budget_packages()
        return {
            "over_budget_count": len(over_budget),
            "categories": over_budget,
        }


class PocketSmithForecastNeedsRecalculateBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that is on when the forecast is stale or missing."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]

    @property
    def device_info(self):
        """Return device info."""
        return _make_device_info(self.coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_forecast_needs_recalculate" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "Pocketsmith Forecast Needs Recalculate"

    @property
    def is_on(self) -> bool:
        """Return True if forecast_last_updated is missing or older than 24 hours."""
        last_updated = self.coordinator.data.get("forecast_last_updated")
        if last_updated is None:
            return True
        if isinstance(last_updated, str):
            try:
                last_updated = datetime.fromisoformat(last_updated)
            except ValueError:
                return True
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        age = dt_util.utcnow() - last_updated
        return age.total_seconds() > 86400

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        last_updated = self.coordinator.data.get("forecast_last_updated")
        if last_updated is None:
            return "mdi:refresh-circle"
        if isinstance(last_updated, str):
            try:
                last_updated = datetime.fromisoformat(last_updated)
            except ValueError:
                return "mdi:refresh-circle"
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        stale = (dt_util.utcnow() - last_updated).total_seconds() > 86400
        return "mdi:refresh-circle" if stale else "mdi:check-circle"


class PocketSmithHasUncategorisedBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that is on when there are uncategorised transactions."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def device_info(self):
        """Return device info."""
        return _make_device_info(self.coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_has_uncategorised" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "Pocketsmith Has Uncategorised"

    @property
    def is_on(self) -> bool:
        """Return True if there are uncategorised transactions."""
        return self.coordinator.data.get("uncategorised_count", 0) > 0

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:tag-off" if self.coordinator.data.get("uncategorised_count", 0) > 0 else "mdi:tag-check"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the uncategorised transaction count."""
        return {"uncategorised_count": self.coordinator.data.get("uncategorised_count", 0)}
