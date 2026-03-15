"""PocketSmith sensor platform."""
import logging

from homeassistant.components.device_registry import DeviceEntryType
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PocketSmithCoordinator

_LOGGER = logging.getLogger(__name__)


def _make_device_info(coordinator) -> DeviceInfo:
    """Return a shared DeviceInfo for all PocketSmith sensors."""
    return DeviceInfo(
        identifiers={(DOMAIN, str(coordinator.data["user_id"]))},
        name="PocketSmith — %s" % coordinator.data.get("user", {}).get("name", "User"),
        manufacturer="PocketSmith",
        entry_type=DeviceEntryType.SERVICE,
    )


ACCOUNT_BALANCE_DESCRIPTION = SensorEntityDescription(
    key="balance",
    name="Account Balance",
    icon="mdi:currency-usd",
    device_class="monetary",
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """YAML configuration is no longer supported."""
    _LOGGER.warning(
        "PocketSmith YAML configuration is no longer supported. "
        "Please migrate to a config entry."
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PocketSmith sensors from a config entry."""
    coordinator: PocketSmithCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        PocketSmithSensor(coordinator, account)
        for account in coordinator.data["accounts"]
    ]
    sensors.append(PocketsmithUncategorisedTransactions(coordinator))
    sensors.append(PocketSmithCategoriesSensor(coordinator))
    sensors.extend(
        PocketSmithCategorySensor(coordinator, enriched_category)
        for enriched_category in coordinator.data.get("enriched_categories", [])
    )
    sensors.append(PocketSmithBudgetSummarySensor(coordinator))
    sensors.append(PocketSmithTrendAnalysisSensor(coordinator))
    sensors.append(PocketSmithUserSensor(coordinator))
    async_add_entities(sensors)


class PocketSmithSensor(CoordinatorEntity, SensorEntity):
    """Representation of a PocketSmith account balance sensor."""

    def __init__(self, coordinator: PocketSmithCoordinator, account: dict) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._account_id = account["id"]
        # Store slug at init so unique_id is stable if coordinator data is temporarily absent.
        account_title = account.get("title", "Unnamed Account")
        self._account_title_slug = account_title.replace(" ", "_").lower()
        self.entity_description = ACCOUNT_BALANCE_DESCRIPTION
        self._attr_device_info = _make_device_info(coordinator)

    @property
    def _account(self) -> dict:
        """Return the current account dict from coordinator data."""
        for account in self.coordinator.data.get("accounts", []):
            if account["id"] == self._account_id:
                return account
        return {}

    @property
    def unique_id(self) -> str:
        """Return a stable unique ID for this sensor."""
        return "pocketsmith_%s_%s_balance" % (self._account_id, self._account_title_slug)

    @property
    def name(self) -> str:
        """Return the sensor name."""
        account_title = self._account.get("title", "Unnamed Account")
        return "PocketSmith %s Balance" % account_title

    @property
    def native_value(self):
        """Return the current account balance."""
        return self._account.get("current_balance")

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency code as the unit."""
        return self._account.get("currency_code", "USD").upper()

    @property
    def extra_state_attributes(self) -> dict:
        """Return filtered transaction account sub-accounts as attributes."""
        filtered = [
            {
                "id": ta.get("id"),
                "account_id": ta.get("account_id"),
                "name": ta.get("name"),
                "current_balance": ta.get("current_balance"),
            }
            for ta in self._account.get("transaction_accounts", [])
        ]
        return {"transaction_accounts": filtered}


class PocketsmithUncategorisedTransactions(CoordinatorEntity, SensorEntity):
    """Sensor reporting the count of uncategorised transactions."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_device_info = _make_device_info(coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_uncategorised_transactions" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Uncategorised Transactions"

    @property
    def native_value(self):
        """Return the count of uncategorised transactions."""
        return self.coordinator.data.get("uncategorised_count")

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "transactions"

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:alert-circle-outline"


class PocketSmithCategoriesSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the total number of PocketSmith categories."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_device_info = _make_device_info(coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_categories" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Total Spent"

    @property
    def native_value(self):
        """Return total actual spend from the budget summary expense or income analysis."""
        raw = self.coordinator.data.get("budget_summary", {})
        data = raw[0] if isinstance(raw, list) else raw
        expense = data.get("expense", {})
        if expense:
            amount = expense.get("total_actual_amount")
            if amount is not None:
                return abs(amount)
        income = data.get("income", {})
        if income:
            return income.get("total_actual_amount")
        return None

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:cash-minus"

    @property
    def extra_state_attributes(self) -> dict:
        """Return an empty dict — category data is now exposed via PocketSmithCategorySensor."""
        return {}


class PocketSmithCategorySensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a single enriched PocketSmith category."""

    def __init__(self, coordinator: PocketSmithCoordinator, enriched_category: dict) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._category_id = enriched_category["category_id"]
        import re
        raw_slug = enriched_category.get("category_title", "").lower().replace(" ", "_")
        self._category_slug = re.sub(r"[^\w]", "", raw_slug)
        self._attr_device_info = _make_device_info(coordinator)

    @property
    def _enriched(self) -> dict:
        """Return the current enriched category from coordinator data."""
        for cat in self.coordinator.data.get("enriched_categories", []):
            if cat.get("category_id") == self._category_id:
                return cat
        return {}

    @property
    def unique_id(self) -> str:
        """Return a stable unique ID for this sensor."""
        return "pocketsmith_category_%s_%s" % (self._category_id, self._category_slug)

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Category %s" % self._enriched.get("category_title", self._category_slug)

    @property
    def native_value(self):
        """Return the actual spend for the current period, or 0 if not available."""
        actual = self._enriched.get("actual")
        return actual if actual is not None else 0

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency code."""
        return self._enriched.get("currency", "AUD")

    @property
    def icon(self) -> str:
        """Return the sensor icon based on whether the category is over budget."""
        if self._enriched.get("over_budget"):
            return "mdi:cash-remove"
        return "mdi:cash-check"

    @property
    def extra_state_attributes(self) -> dict:
        """Return enriched category details as attributes."""
        e = self._enriched
        return {
            "category_id": e.get("category_id"),
            "category_title": e.get("category_title"),
            "parent_id": e.get("parent_id"),
            "parent_title": e.get("parent_title"),
            "is_bill": e.get("is_bill"),
            "budgeted": e.get("budgeted"),
            "actual": e.get("actual"),
            "remaining": e.get("remaining"),
            "over_by": e.get("over_by"),
            "over_budget": e.get("over_budget"),
            "percentage_used": e.get("percentage_used"),
            "currency": e.get("currency"),
        }


class PocketSmithBudgetSummarySensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the PocketSmith budget summary."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_device_info = _make_device_info(coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_budget_summary" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Budget Summary"

    @property
    def _summary_data(self) -> dict:
        """Return the budget summary dict, unwrapping a list if necessary."""
        raw = self.coordinator.data.get("budget_summary", {})
        if isinstance(raw, list):
            return raw[0] if raw else {}
        return raw

    @property
    def native_value(self):
        """Return total_under_by from expense or income analysis."""
        data = self._summary_data
        expense = data.get("expense", {})
        if expense:
            return expense.get("total_under_by")
        income = data.get("income", {})
        if income:
            return income.get("total_under_by")
        return None

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency code from expense or income analysis."""
        data = self._summary_data
        code = data.get("expense", {}).get("currency_code") or data.get("income", {}).get("currency_code") or "AUD"
        return code.upper()

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:calculator-variant"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the full budget summary as attributes."""
        return self.coordinator.data.get("budget_summary", {})


class PocketSmithTrendAnalysisSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the PocketSmith trend analysis package count."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_device_info = _make_device_info(coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_trend_analysis" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Total Trend Spend"

    @property
    def native_value(self):
        """Return total absolute expense spend across all trend analysis packages."""
        total = 0.0
        for package in self.coordinator.data.get("trend_analysis", []):
            if not isinstance(package, dict):
                continue
            expense = package.get("expense")
            if expense:
                amount = expense.get("total_actual_amount")
                if amount is not None:
                    total += abs(amount)
        return round(total, 2)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency code from the first trend analysis package."""
        packages = self.coordinator.data.get("trend_analysis", [])
        for first in packages:
            if not isinstance(first, dict):
                continue
            code = (
                (first.get("expense") or {}).get("currency_code")
                or (first.get("income") or {}).get("currency_code")
                or "AUD"
            )
            return code.upper()
        return "AUD"

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:chart-line"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the full trend analysis list as an attribute."""
        return {"trend_analysis": self.coordinator.data.get("trend_analysis", [])}


class PocketSmithUserSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting PocketSmith user profile information."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_device_info = _make_device_info(coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_user" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith User"

    @property
    def native_value(self):
        """Return the user's name."""
        return self.coordinator.data.get("user", {}).get("name")

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:account-circle"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the user profile dict, excluding sensitive keys."""
        user = self.coordinator.data.get("user")
        if not user:
            return {}
        return {k: v for k, v in user.items() if k not in ("email", "tell_a_friend_code")}
