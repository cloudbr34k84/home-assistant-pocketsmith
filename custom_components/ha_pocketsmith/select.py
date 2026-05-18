"""PocketSmith select platform — active currency for Net Worth sensor."""
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ACTIVE_CURRENCY, DEFAULT_CURRENCY, DOMAIN
from .coordinator import PocketSmithCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PocketSmith select entities from a config entry."""
    coordinator: PocketSmithCoordinator = entry.runtime_data.coordinator
    async_add_entities([PocketSmithActiveCurrencySelect(coordinator, entry)])


class PocketSmithActiveCurrencySelect(CoordinatorEntity, SelectEntity):
    """Select entity that controls which currency the Net Worth sensor reports in."""

    _attr_has_entity_name = True
    _attr_translation_key = "active_currency"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:currency-usd"

    def __init__(self, coordinator: PocketSmithCoordinator, entry: ConfigEntry) -> None:
        """Initialise the select entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._user_id = coordinator.data["user_id"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._user_id))},
            name="PocketSmith",
            manufacturer="PocketSmith",
            model="Cloud Integration",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def unique_id(self) -> str:
        return "pocketsmith_%s_active_currency" % self._user_id

    @property
    def options(self) -> list[str]:
        """Return the list of currencies present across all accounts."""
        currencies = {
            (acc.get("currency_code") or DEFAULT_CURRENCY).upper()
            for acc in self.coordinator.data.get("accounts", [])
        }
        return sorted(currencies) or [DEFAULT_CURRENCY]

    @property
    def current_option(self) -> str:
        """Return the currently selected currency."""
        saved = self._entry.options.get(CONF_ACTIVE_CURRENCY)
        if saved and saved in self.options:
            return saved
        # Default to the first account's currency.
        accounts = self.coordinator.data.get("accounts", [])
        if accounts:
            return (accounts[0].get("currency_code") or DEFAULT_CURRENCY).upper()
        return DEFAULT_CURRENCY

    async def async_select_option(self, option: str) -> None:
        """Persist the selected currency to config entry options."""
        new_options = {**self._entry.options, CONF_ACTIVE_CURRENCY: option}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        _LOGGER.debug("PocketSmith active currency set to %s", option)
