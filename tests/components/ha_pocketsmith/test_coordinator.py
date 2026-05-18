"""Tests for PocketSmithCoordinator._build_enriched_categories."""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from custom_components.ha_pocketsmith.coordinator import PocketSmithCoordinator


def _make_coordinator(hass=None):
    """Build a minimal coordinator for unit-testing pure methods."""
    coord = object.__new__(PocketSmithCoordinator)
    return coord


# ---------------------------------------------------------------------------
# _build_enriched_categories
# ---------------------------------------------------------------------------

CATEGORY_GROCERIES = {
    "id": 10,
    "title": "Groceries",
    "parent_id": None,
    "is_bill": False,
    "is_transfer": False,
    "children": [],
}

CATEGORY_DINING = {
    "id": 11,
    "title": "Dining",
    "parent_id": None,
    "is_bill": False,
    "is_transfer": False,
    "children": [],
}

CATEGORY_TRANSFER = {
    "id": 99,
    "title": "Transfer",
    "parent_id": None,
    "is_bill": False,
    "is_transfer": True,
    "children": [],
}

CATEGORY_RENT = {
    "id": 20,
    "title": "Rent",
    "parent_id": None,
    "is_bill": True,
    "is_transfer": False,
    "children": [],
}

CATEGORY_FOOD = {
    "id": 1,
    "title": "Food",
    "parent_id": None,
    "is_bill": False,
    "is_transfer": False,
    "children": [
        {
            "id": 10,
            "title": "Groceries",
            "parent_id": 1,
            "is_bill": False,
            "is_transfer": False,
            "children": [],
        }
    ],
}


def _build(categories, budget, monthly_transactions, monthly_events, monthly_transaction_counts):
    coord = _make_coordinator()
    with patch("custom_components.ha_pocketsmith.coordinator.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value = date(2026, 5, 15)
        return coord._build_enriched_categories(
            categories, budget, monthly_transactions, monthly_events, monthly_transaction_counts
        )


def test_transfer_categories_excluded():
    """Transfer categories are not included in enriched output."""
    result = _build([CATEGORY_TRANSFER], {}, {}, {}, {})
    assert result == []


def test_basic_category_no_budget():
    """Category with no budget has budgeted=None and actual from transactions."""
    result = _build([CATEGORY_GROCERIES], [], {10: 150.0}, {}, {10: 3})
    assert len(result) == 1
    cat = result[0]
    assert cat["category_id"] == 10
    assert cat["category_title"] == "Groceries"
    assert cat["actual"] == 150.0
    assert cat["budgeted"] is None
    assert cat["transaction_count"] == 3


def test_category_with_no_transactions_and_no_budget():
    """Category with no transactions and no budget has actual=None."""
    result = _build([CATEGORY_GROCERIES], [], {}, {}, {})
    assert len(result) == 1
    assert result[0]["actual"] is None
    assert result[0]["budgeted"] is None


def test_over_budget_flag():
    """over_budget is True when actual exceeds budgeted."""
    budget = [
        {
            "category": {"id": 10},
            "expense": {
                "currency_code": "AUD",
                "periods": [
                    {
                        "current": True,
                        "start_date": "2026-05-01",
                        "end_date": "2026-05-31",
                        "forecast_amount": -100.0,
                    }
                ],
            },
        }
    ]
    result = _build([CATEGORY_GROCERIES], budget, {10: 200.0}, {}, {10: 5})
    assert len(result) == 1
    cat = result[0]
    assert cat["over_budget"] is True
    assert cat["over_by"] > 0


def test_under_budget_flag():
    """over_budget is False when actual is less than budgeted."""
    budget = [
        {
            "category": {"id": 10},
            "expense": {
                "currency_code": "AUD",
                "periods": [
                    {
                        "current": True,
                        "start_date": "2026-05-01",
                        "end_date": "2026-05-31",
                        "forecast_amount": -300.0,
                    }
                ],
            },
        }
    ]
    result = _build([CATEGORY_GROCERIES], budget, {10: 50.0}, {}, {10: 1})
    cat = result[0]
    assert cat["over_budget"] is False
    assert cat["remaining"] > 0
    assert cat["over_by"] == 0


def test_bill_category_uses_events():
    """Bill category budgeted amount comes from monthly_events, not budget packages."""
    result = _build([CATEGORY_RENT], [], {20: 800.0}, {20: 1200.0}, {20: 1})
    cat = result[0]
    assert cat["budgeted"] == 1200.0
    assert cat["actual"] == 800.0


def test_bill_category_no_event_this_month():
    """Bill category with no event this month has budgeted=None."""
    result = _build([CATEGORY_RENT], [], {20: 800.0}, {}, {20: 1})
    cat = result[0]
    assert cat["budgeted"] is None


def test_parent_child_relationship():
    """Child category has correct parent_id and parent_title."""
    result = _build([CATEGORY_FOOD], [], {10: 50.0}, {}, {10: 2})
    child = next(c for c in result if c["category_id"] == 10)
    assert child["parent_id"] == 1
    assert child["parent_title"] == "Food"


def test_multiple_categories_all_returned():
    """All non-transfer categories are included."""
    result = _build(
        [CATEGORY_GROCERIES, CATEGORY_DINING, CATEGORY_TRANSFER],
        [], {}, {}, {}
    )
    ids = {c["category_id"] for c in result}
    assert 10 in ids
    assert 11 in ids
    assert 99 not in ids


def test_percentage_used_computed():
    """percentage_used is computed when budgeted > 0."""
    budget = [
        {
            "category": {"id": 10},
            "expense": {
                "currency_code": "AUD",
                "periods": [
                    {
                        "current": True,
                        "start_date": "2026-05-01",
                        "end_date": "2026-05-31",
                        "forecast_amount": -200.0,
                    }
                ],
            },
        }
    ]
    result = _build([CATEGORY_GROCERIES], budget, {10: 100.0}, {}, {10: 2})
    cat = result[0]
    assert cat["percentage_used"] == 50.0


def test_no_current_period_skips_budgeted():
    """Budget package with no current period results in budgeted=None."""
    budget = [
        {
            "category": {"id": 10},
            "expense": {
                "currency_code": "AUD",
                "periods": [
                    {
                        "current": False,
                        "start_date": "2026-04-01",
                        "end_date": "2026-04-30",
                        "forecast_amount": -200.0,
                    }
                ],
            },
        }
    ]
    result = _build([CATEGORY_GROCERIES], budget, {10: 100.0}, {}, {10: 2})
    cat = result[0]
    assert cat["budgeted"] is None
