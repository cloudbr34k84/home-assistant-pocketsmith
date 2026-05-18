"""HA actions (services) for the PocketSmith integration."""
import logging

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers.storage import Store

from .backfill import async_trigger_backfill
from .const import DOMAIN
from .repairs import clear_backfill_failed_issue

_LOGGER = logging.getLogger(__name__)

_STORAGE_KEY = "%s.backfill" % DOMAIN
_STORAGE_VERSION = 1


def async_register_actions(hass: HomeAssistant) -> None:
    """Register all PocketSmith actions."""

    async def handle_refresh(call: ServiceCall) -> None:
        """Force an immediate coordinator refresh."""
        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator = entry.runtime_data.coordinator
            await coordinator.async_request_refresh()
            _LOGGER.debug("PocketSmith manual refresh triggered")

    async def handle_reset_backfill(call: ServiceCall) -> None:
        """Clear backfill progress so the next startup re-sweeps all accounts."""
        store = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)
        await store.async_remove()
        clear_backfill_failed_issue(hass)
        _LOGGER.info("PocketSmith backfill progress reset — will re-sweep on next startup")

        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator = entry.runtime_data.coordinator
            await async_trigger_backfill(hass, coordinator, coordinator.data, entry, entry.runtime_data.backfill)

    async def handle_get_budget_summary(call: ServiceCall) -> ServiceResponse:
        """Return current budget summary as structured data."""
        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator = entry.runtime_data.coordinator
            data = coordinator.data
            categories = data.get("enriched_categories", [])
            over_budget = [c for c in categories if c.get("over_budget")]
            return {
                "total_categories": len(categories),
                "over_budget_count": len(over_budget),
                "over_budget_categories": [
                    {
                        "category_title": c.get("category_title"),
                        "parent_title": c.get("parent_title"),
                        "budgeted": c.get("budgeted"),
                        "actual": c.get("actual"),
                        "over_by": c.get("over_by"),
                        "percentage_used": c.get("percentage_used"),
                    }
                    for c in over_budget
                ],
                "uncategorised_count": data.get("uncategorised_count", 0),
                "net_worth": sum(
                    acc.get("current_balance") or 0
                    for acc in data.get("accounts", [])
                ),
            }
        return {}

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)
    hass.services.async_register(DOMAIN, "reset_backfill", handle_reset_backfill)
    hass.services.async_register(
        DOMAIN,
        "get_budget_summary",
        handle_get_budget_summary,
        supports_response=SupportsResponse.ONLY,
    )


def async_unregister_actions(hass: HomeAssistant) -> None:
    """Remove all PocketSmith actions."""
    hass.services.async_remove(DOMAIN, "refresh")
    hass.services.async_remove(DOMAIN, "reset_backfill")
    hass.services.async_remove(DOMAIN, "get_budget_summary")
