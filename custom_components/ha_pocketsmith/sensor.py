"""PocketSmith sensor platform."""
import logging
import re

from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PocketSmithCoordinator
from .helpers import non_transfer_budget_packages

_LOGGER = logging.getLogger(__name__)


def _make_device_info(coordinator) -> DeviceInfo:
    """Return a shared DeviceInfo for all PocketSmith sensors."""
    return DeviceInfo(
        identifiers={(DOMAIN, str(coordinator.data["user_id"]))},
        name="PocketSmith",
        manufacturer="PocketSmith",
        model="Cloud Integration",
        entry_type=DeviceEntryType.SERVICE,
    )


ACCOUNT_BALANCE_DESCRIPTION = SensorEntityDescription(
    key="balance",
    name="Account Balance",
    icon="mdi:currency-usd",
    device_class=SensorDeviceClass.MONETARY,
    state_class=SensorStateClass.MEASUREMENT,
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
    sensors.append(PocketSmithUncategorisedTransactions(coordinator))
    sensors.append(PocketSmithCategoriesSensor(coordinator))
    sensors.append(PocketSmithCategoriesBudgetedSensor(coordinator))
    sensors.append(PocketSmithCategoriesUnbudgetedSensor(coordinator))
    sensors.extend(
        PocketSmithCategorySensor(coordinator, enriched_category)
        for enriched_category in coordinator.data.get("enriched_categories", [])
    )
    sensors.append(PocketSmithBudgetSummarySensor(coordinator))
    sensors.append(PocketSmithNetWorthSensor(coordinator))
    sensors.append(PocketSmithTotalBudgetedSensor(coordinator))
    sensors.append(PocketSmithTotalSpentSensor(coordinator))
    sensors.append(PocketSmithBudgetRemainingSensor(coordinator))
    sensors.append(PocketSmithCategoriesOverBudgetCountSensor(coordinator))
    sensors.append(PocketSmithBudgetHealthSensor(coordinator))
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
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

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


class PocketSmithUncategorisedTransactions(CoordinatorEntity, SensorEntity):
    """Sensor reporting the count of uncategorised transactions."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

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
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

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
        return "mdi:cash-minus"

    @property
    def extra_state_attributes(self) -> dict:
        """Return an empty dict — category data is now exposed via PocketSmithCategorySensor."""
        return {}


class PocketSmithCategoriesBudgetedSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the count of categories that have a budget entry."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_categories_budgeted" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Categories Budgeted"

    def _budgeted_categories(self) -> list:
        """Return categories that have a matching entry in the budget list."""
        budgeted_ids = {
            pkg["category"]["id"]
            for pkg in self.coordinator.data.get("budget", [])
            if isinstance(pkg.get("category"), dict)
        }
        return [
            cat for cat in self.coordinator.data.get("categories", [])
            if cat.get("id") in budgeted_ids
        ]

    @property
    def native_value(self):
        """Return the count of budgeted categories."""
        return len(self._budgeted_categories())

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:tag-check"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the names of budgeted categories."""
        return {"category_names": [cat.get("title") for cat in self._budgeted_categories()]}


class PocketSmithCategoriesUnbudgetedSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the count of categories that have no budget entry."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_categories_unbudgeted" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Categories Unbudgeted"

    def _unbudgeted_categories(self) -> list:
        """Return categories that have no matching entry in the budget list."""
        budgeted_ids = {
            pkg["category"]["id"]
            for pkg in self.coordinator.data.get("budget", [])
            if isinstance(pkg.get("category"), dict)
        }
        return [
            cat for cat in self.coordinator.data.get("categories", [])
            if cat.get("id") not in budgeted_ids
        ]

    @property
    def native_value(self):
        """Return the count of unbudgeted categories."""
        return len(self._unbudgeted_categories())

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:tag-off"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the names of unbudgeted categories."""
        return {"category_names": [cat.get("title") for cat in self._unbudgeted_categories()]}


class PocketSmithCategorySensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a single enriched PocketSmith category."""

    def __init__(self, coordinator: PocketSmithCoordinator, enriched_category: dict) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._category_id = enriched_category["category_id"]
        raw_slug = enriched_category.get("category_title", "").lower().replace(" ", "_")
        self._category_slug = re.sub(r"[^\w]", "", raw_slug)
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

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
        e = self._enriched
        title = e.get("category_title", self._category_slug)
        parent_id = e.get("parent_id")
        if parent_id:
            parent = next(
                (c for c in self.coordinator.data.get("categories", []) if c.get("id") == parent_id),
                None,
            )
            if parent:
                return "PocketSmith Category %s > %s" % (parent.get("title", parent_id), title)
        return "PocketSmith Category %s" % title

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
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

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
        raw = self.coordinator.data.get("budget_summary", {})
        if isinstance(raw, list):
            return raw[0] if raw else {}
        return raw


class PocketSmithNetWorthSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the total net worth across all accounts."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_net_worth" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Net Worth"

    @property
    def native_value(self):
        """Return the sum of current_balance across all accounts."""
        return sum(
            acc.get("current_balance") or 0
            for acc in self.coordinator.data.get("accounts", [])
        )

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency code from the first account."""
        accounts = self.coordinator.data.get("accounts", [])
        if accounts:
            return (accounts[0].get("currency_code") or "AUD").upper()
        return "AUD"

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:bank"


def _budget_currency(coordinator) -> str:
    """Return the currency code from the first budget package."""
    for pkg in coordinator.data.get("budget", []):
        period = pkg.get("current_period") or {}
        code = period.get("currency_code")
        if code:
            return code.upper()
    return "AUD"


class PocketSmithTotalBudgetedSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the total budgeted amount across all non-transfer budget packages."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_total_budgeted" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Total Budgeted"

    @property
    def native_value(self):
        """Return sum of abs(forecast_amount) from current period across non-transfer packages."""
        total = 0.0
        for pkg in non_transfer_budget_packages(self.coordinator.data.get("budget", [])):
            period = pkg.get("current_period") or {}
            amount = period.get("forecast_amount")
            if amount is not None:
                total += abs(amount)
        return round(total, 2)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency code."""
        return _budget_currency(self.coordinator)

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:cash-clock"


class PocketSmithTotalSpentSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the total actual spend across all non-transfer budget packages."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_total_spent" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Total Spent"

    @property
    def native_value(self):
        """Return sum of abs(actual_amount) from current period across non-transfer packages."""
        total = 0.0
        for pkg in non_transfer_budget_packages(self.coordinator.data.get("budget", [])):
            period = pkg.get("current_period") or {}
            amount = period.get("actual_amount")
            if amount is not None:
                total += abs(amount)
        return round(total, 2)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency code."""
        return _budget_currency(self.coordinator)

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:cash-minus"


class PocketSmithBudgetRemainingSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the remaining budget (budgeted minus spent)."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_budget_remaining" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Budget Remaining"

    @property
    def native_value(self):
        """Return total budgeted minus total spent across non-transfer packages."""
        total_budgeted = 0.0
        total_spent = 0.0
        for pkg in non_transfer_budget_packages(self.coordinator.data.get("budget", [])):
            period = pkg.get("current_period") or {}
            forecast = period.get("forecast_amount")
            actual = period.get("actual_amount")
            if forecast is not None:
                total_budgeted += abs(forecast)
            if actual is not None:
                total_spent += abs(actual)
        return round(total_budgeted - total_spent, 2)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency code."""
        return _budget_currency(self.coordinator)

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:cash-plus"


class PocketSmithCategoriesOverBudgetCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the count of non-transfer budget categories that are over budget."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_categories_over_budget_count" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Categories Over Budget Count"

    @property
    def native_value(self):
        """Return count of non-transfer packages where the current period is over budget."""
        return sum(
            1 for pkg in non_transfer_budget_packages(self.coordinator.data.get("budget", []))
            if (pkg.get("current_period") or {}).get("over_budget") is True
        )

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "categories"

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:alert-circle-outline"


class PocketSmithBudgetHealthSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting an overall budget health status."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._cached_stats = None

    def _clear_cache(self) -> None:
        """Clear the cached budget stats so they are recomputed on next access."""
        self._cached_stats = None

    async def async_added_to_hass(self) -> None:
        """Register cache-clearing listener when coordinator updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._clear_cache)
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        return "pocketsmith_%s_budget_health" % self._user_id

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return "PocketSmith Budget Health"

    def _budget_stats(self) -> dict:
        """Return cached budget health statistics, computing if necessary."""
        if self._cached_stats is not None:
            return self._cached_stats
        packages = non_transfer_budget_packages(self.coordinator.data.get("budget", []))
        total_budgeted = 0.0
        total_actual = 0.0
        over_budget_pkgs = []
        warning_count = 0
        healthy_count = 0

        for pkg in packages:
            period = pkg.get("current_period") or {}
            forecast = period.get("forecast_amount")
            actual = period.get("actual_amount")
            if forecast is not None:
                total_budgeted += abs(forecast)
            if actual is not None:
                total_actual += abs(actual)
            pct = period.get("percentage_used") or 0
            over = period.get("over_budget") is True
            if over or pct > 100:
                cat = pkg.get("category") or {}
                over_budget_pkgs.append({
                    "category_title": cat.get("title"),
                    "parent_title": (cat.get("parent_category") or {}).get("title"),
                    "actual": abs(actual) if actual is not None else None,
                    "budgeted": abs(forecast) if forecast is not None else None,
                    "over_by": period.get("over_by"),
                    "percentage_used": pct,
                })
            elif pct >= 80:
                warning_count += 1
            else:
                healthy_count += 1

        overall_pct = round(total_actual / total_budgeted * 100, 1) if total_budgeted else 0.0

        budgeted_ids = {
            pkg.get("category", {}).get("id")
            for pkg in self.coordinator.data.get("budget", [])
            if isinstance(pkg.get("category"), dict)
        }
        unbudgeted_count = sum(
            1 for cat in self.coordinator.data.get("categories", [])
            if cat.get("id") not in budgeted_ids
        )

        top_overspent = sorted(
            over_budget_pkgs,
            key=lambda x: x.get("over_by") or 0,
            reverse=True,
        )[:3]

        self._cached_stats = {
            "overall_percentage_used": overall_pct,
            "total_budgeted": round(total_budgeted, 2),
            "total_actual": round(total_actual, 2),
            "total_remaining": round(total_budgeted - total_actual, 2),
            "over_budget_count": len(over_budget_pkgs),
            "warning_count": warning_count,
            "healthy_count": healthy_count,
            "unbudgeted_count": unbudgeted_count,
            "top_overspent": top_overspent,
        }
        return self._cached_stats

    @property
    def native_value(self) -> str:
        """Return 'critical', 'warning', or 'good' based on budget health."""
        stats = self._budget_stats()
        if stats["over_budget_count"] > 0 or stats["overall_percentage_used"] > 100:
            return "critical"
        if stats["overall_percentage_used"] >= 80:
            return "warning"
        return "good"

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:heart-pulse"

    @property
    def extra_state_attributes(self) -> dict:
        """Return detailed budget health statistics."""
        stats = self._budget_stats()
        return {
            "overall_percentage_used": stats["overall_percentage_used"],
            "total_budgeted": stats["total_budgeted"],
            "total_actual": stats["total_actual"],
            "total_remaining": stats["total_remaining"],
            "over_budget_count": stats["over_budget_count"],
            "warning_count": stats["warning_count"],
            "healthy_count": stats["healthy_count"],
            "unbudgeted_count": stats["unbudgeted_count"],
            "top_overspent": stats["top_overspent"],
        }


class PocketSmithTrendAnalysisSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the PocketSmith trend analysis package count."""

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return _make_device_info(self.coordinator)

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
