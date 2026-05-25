"""Repair issue helpers for the PocketSmith integration."""
import logging

from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue, async_delete_issue
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ISSUE_UNCATEGORISED = "uncategorised_transactions"
ISSUE_BACKFILL_FAILED = "backfill_failed"


def update_repair_issues(hass: HomeAssistant, data: dict) -> None:
    """Create or clear repair issues based on the latest coordinator data."""
    _update_uncategorised_issue(hass, data)


def _update_uncategorised_issue(hass: HomeAssistant, data: dict) -> None:
    count = data.get("uncategorised_count", 0) or 0
    if count > 0:
        async_create_issue(
            hass,
            DOMAIN,
            ISSUE_UNCATEGORISED,
            is_fixable=False,
            is_persistent=False,
            severity=IssueSeverity.WARNING,
            translation_key=ISSUE_UNCATEGORISED,
            translation_placeholders={"count": str(count)},
            learn_more_url="https://app.pocketsmith.com",
        )
    else:
        async_delete_issue(hass, DOMAIN, ISSUE_UNCATEGORISED)


def raise_backfill_failed_issue(hass: HomeAssistant, account_title: str) -> None:
    """Raise a repair issue when backfill fails an account after max retries."""
    async_create_issue(
        hass,
        DOMAIN,
        ISSUE_BACKFILL_FAILED,
        is_fixable=False,
        is_persistent=True,
        severity=IssueSeverity.WARNING,
        translation_key=ISSUE_BACKFILL_FAILED,
        translation_placeholders={"account": account_title},
    )


def clear_backfill_failed_issue(hass: HomeAssistant) -> None:
    """Clear the backfill failed issue (e.g. after a successful reset)."""
    async_delete_issue(hass, DOMAIN, ISSUE_BACKFILL_FAILED)
