"""PocketSmith binary sensor platform."""
import logging
from datetime import datetime, timezone

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PocketSmithCoordinator
from .helpers import non_transfer_budget_packages
from .sensor import _make_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PocketSmith binary sensors from a config entry."""
    coordinator: PocketSmithCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        PocketSmithOverBudgetBinarySensor(coordinator),
        PocketSmithForecastNeedsRecalculateBinarySensor(coordinator),
        PocketSmithHasUncategorisedBinarySensor(coordinator),
    ])


class PocketSmithOverBudgetBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that is on when any non-transfer category is over budget."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_device_info = _make_device_info(coordinator)
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
        return "PocketSmith Over Budget"

    @property
    def is_on(self) -> bool:
        """Return True if any non-transfer package is over budget."""
        return any(
            (pkg.get("current_period") or {}).get("over_budget") is True
            for pkg in non_transfer_budget_packages(self.coordinator.data.get("budget", []))
        )

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        over = any(
            (pkg.get("current_period") or {}).get("over_budget") is True
            for pkg in non_transfer_budget_packages(self.coordinator.data.get("budget", []))
        )
        return "mdi:alert-circle" if over else "mdi:check-circle"

    @property
    def extra_state_attributes(self) -> dict:
        """Return details of over-budget categories."""
        over_budget = []
        for pkg in non_transfer_budget_packages(self.coordinator.data.get("budget", [])):
            period = pkg.get("current_period") or {}
            if period.get("over_budget") is not True:
                continue
            cat = pkg.get("category") or {}
            forecast = period.get("forecast_amount")
            actual = period.get("actual_amount")
            over_budget.append({
                "category_title": cat.get("title"),
                "parent_title": (cat.get("parent_category") or {}).get("title"),
                "actual": abs(actual) if actual is not None else None,
                "budgeted": abs(forecast) if forecast is not None else None,
                "over_by": period.get("over_by"),
                "percentage_used": period.get("percentage_used"),
            })
        return {
            "over_budget_count": len(over_budget),
            "categories": over_budget,
        }


class PocketSmithForecastNeedsRecalculateBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that is on when the forecast is stale or missing."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_device_info = _make_device_info(coordinator)

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
        return "PocketSmith Forecast Needs Recalculate"

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
        age = datetime.now(timezone.utc) - last_updated
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
        stale = (datetime.now(timezone.utc) - last_updated).total_seconds() > 86400
        return "mdi:refresh-circle" if stale else "mdi:check-circle"


class PocketSmithHasUncategorisedBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that is on when there are uncategorised transactions."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_device_info = _make_device_info(coordinator)
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
        return "PocketSmith Has Uncategorised"

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
