"""PocketSmith sensor platform."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PocketSmithCoordinator

_LOGGER = logging.getLogger(__name__)

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
        PocketSmithBudgetSensor(coordinator, package)
        for package in coordinator.data.get("budget", [])
    )
    sensors.append(PocketSmithBudgetSummarySensor(coordinator))
    sensors.append(PocketSmithTrendAnalysisSensor(coordinator))
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
        return "PocketSmith Account %s %s" % (account_title, self.entity_description.name)

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

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_uncategorised_transactions" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "Pocketsmith Uncategorised Transactions"

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

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_categories" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Categories"

    @property
    def native_value(self):
        """Return the count of categories."""
        return len(self.coordinator.data.get("categories", []))

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:tag-multiple"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the full categories list as an attribute."""
        return {"categories": self.coordinator.data.get("categories", [])}


class PocketSmithBudgetSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a single PocketSmith budget analysis package."""

    def __init__(self, coordinator: PocketSmithCoordinator, package: dict) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        category = package["category"]
        self._category_id = category["id"]
        self._category_slug = category["title"].replace(" ", "_").lower()

    @property
    def _package(self) -> dict:
        """Return the current package from coordinator data by category id."""
        for pkg in self.coordinator.data.get("budget", []):
            if pkg.get("category", {}).get("id") == self._category_id:
                return pkg
        return {}

    @property
    def unique_id(self) -> str:
        """Return a stable unique ID for this sensor."""
        return "pocketsmith_%s_%s_budget" % (self._category_id, self._category_slug)

    @property
    def name(self) -> str:
        """Return the sensor name."""
        title = self._package.get("category", {}).get("title", self._category_slug)
        return "PocketSmith Budget %s" % title

    @property
    def native_value(self):
        """Return the total forecast amount from expense or income analysis."""
        expense = self._package.get("expense")
        if expense:
            return expense.get("total_forecast_amount")
        income = self._package.get("income")
        if income:
            return income.get("total_forecast_amount")
        return None

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency code from the expense or income analysis."""
        expense = self._package.get("expense")
        if expense:
            return expense.get("currency_code", "USD").upper()
        income = self._package.get("income")
        if income:
            return income.get("currency_code", "USD").upper()
        return "USD"

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:cash-clock"

    @property
    def extra_state_attributes(self) -> dict:
        """Return budget analysis details as attributes."""
        category = self._package.get("category", {})
        return {
            "category_id": category.get("id"),
            "category_title": category.get("title"),
            "is_transfer": self._package.get("is_transfer"),
            "expense": self._package.get("expense"),
            "income": self._package.get("income"),
        }


class PocketSmithBudgetSummarySensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the PocketSmith budget summary."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_budget_summary" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Budget Summary"

    @property
    def native_value(self):
        """Return total actual amount from expense or income analysis."""
        summary = self.coordinator.data.get("budget_summary", {})
        expense = summary.get("expense")
        if expense:
            return expense.get("total_actual_amount")
        income = summary.get("income")
        if income:
            return income.get("total_actual_amount")
        return None

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

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_trend_analysis" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Trend Analysis"

    @property
    def native_value(self):
        """Return the count of trend analysis packages."""
        return len(self.coordinator.data.get("trend_analysis", []))

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:chart-line"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the full trend analysis list as an attribute."""
        return {"trend_analysis": self.coordinator.data.get("trend_analysis", [])}
