"""Diagnostics for the PocketSmith integration."""
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = ["developer_key"]
TO_REDACT_USER = ["email", "tell_a_friend_code"]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a PocketSmith config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data

    enriched = data.get("enriched_categories", [])
    monthly_events: dict = data.get("monthly_events", {})
    monthly_transactions: dict = data.get("monthly_transactions", {})
    budget: list = data.get("budget", [])

    null_budgeted = [c for c in enriched if c.get("budgeted") is None]
    null_actual = [c for c in enriched if c.get("actual") is None]
    bill_categories = [c for c in enriched if c.get("is_bill")]

    # Build a summary of which bill categories have/don't have events
    bill_event_summary = [
        {
            "category_id": c.get("category_id"),
            "category_title": c.get("category_title"),
            "has_event": c.get("category_id") in monthly_events,
            "budgeted": c.get("budgeted"),
            "actual": c.get("actual"),
        }
        for c in bill_categories
    ]

    # Build a summary of budget packages: does each category have a current period?
    budget_package_summary = []
    for pkg in budget:
        if not isinstance(pkg, dict):
            continue
        cat = pkg.get("category")
        if not cat:
            continue
        analysis = pkg.get("expense") or pkg.get("income")
        periods = analysis.get("periods", []) if analysis else []
        current = next((p for p in periods if p.get("current")), None)
        budget_package_summary.append({
            "category_id": cat.get("id"),
            "category_title": cat.get("title"),
            "has_current_period": current is not None,
            "current_period_dates": (
                {"start": current.get("start_date"), "end": current.get("end_date")}
                if current else None
            ),
            "period_count": len(periods),
        })

    return {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "options": dict(entry.options),
        "user": async_redact_data(data.get("user", {}), TO_REDACT_USER),
        "summary": {
            "accounts_count": len(data.get("accounts", [])),
            "enriched_categories_count": len(enriched),
            "budget_packages_count": len(budget),
            "monthly_events_category_count": len(monthly_events),
            "monthly_transactions_category_count": len(monthly_transactions),
            "categories_with_null_budgeted": len(null_budgeted),
            "categories_with_null_actual": len(null_actual),
        },
        "monthly_events_category_ids": sorted(monthly_events.keys()),
        "monthly_transactions_category_ids": sorted(monthly_transactions.keys()),
        "bill_event_summary": bill_event_summary,
        "budget_package_summary": budget_package_summary,
        "enriched_categories": enriched,
    }
