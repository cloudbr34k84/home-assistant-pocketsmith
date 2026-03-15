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
    state_class=SensorStateClass.TOTAL,
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
    coordinator: PocketSmithCoordinator = entry.runtime_data

    sensors = [
        PocketSmithSensor(coordinator, account)
        for account in coordinator.data["accounts"]
    ]
    sensors.append(PocketSmithUncategorisedTransactions(coordinator))
    sensors.append(PocketSmithCategoriesSensor(coordinator))
    sensors.extend(
        PocketSmithCategorySensor(coordinator, enriched_category)
        for enriched_category in coordinator.data.get("enriched_categories", [])
    )
    sensors.append(PocketSmithNetWorthSensor(coordinator))
    sensors.append(PocketSmithUserSensor(coordinator))
    async_add_entities(sensors)


class PocketSmithSensor(CoordinatorEntity, SensorEntity):
    """Representation of a PocketSmith account balance sensor."""

    _attr_has_entity_name = True

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
        return "Pocketsmith %s Balance" % account_title

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

    _attr_has_entity_name = True

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

    _attr_has_entity_name = True

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
        return "Pocketsmith Categories"

    @property
    def native_value(self):
        """Return the count of categories."""
        return len(self.coordinator.data.get("enriched_categories", []))

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return "mdi:cash-minus"

    @property
    def extra_state_attributes(self) -> dict:
        """Return budgeted and unbudgeted category name lists."""
        cats = self.coordinator.data.get("enriched_categories", [])
        return {
            "budgeted_categories": [c.get("category_title") for c in cats if c.get("budgeted") is not None],
            "unbudgeted_categories": [c.get("category_title") for c in cats if c.get("budgeted") is None],
        }


class PocketSmithCategorySensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a single enriched PocketSmith category."""

    _attr_has_entity_name = True

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
        """Return the category title."""
        return self._enriched.get("category_title", self._category_slug)

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


class PocketSmithNetWorthSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the total net worth across all accounts."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PocketSmithCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._user_id = coordinator.data["user_id"]
        self._attr_state_class = SensorStateClass.TOTAL

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
        return "Pocketsmith Net Worth"

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


class PocketSmithUserSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting PocketSmith user profile information."""

    _attr_has_entity_name = True

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
        return "Pocketsmith User"

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
