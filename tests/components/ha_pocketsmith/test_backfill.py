"""Tests for PocketSmith backfill helper functions."""
import pytest
from datetime import date, datetime, timezone

from custom_components.ha_pocketsmith.backfill import (
    _flatten_categories,
    _reconstruct_balance_rows,
    _reconstruct_net_worth_rows,
    _resolve_parent_title,
)
from custom_components.ha_pocketsmith.const import BackfillState, BACKFILL_STATUS_IDLE


# ---------------------------------------------------------------------------
# _flatten_categories
# ---------------------------------------------------------------------------

class TestFlattenCategories:
    def test_flat_list(self):
        cats = [
            {"id": 1, "title": "Food", "children": []},
            {"id": 2, "title": "Transport", "children": []},
        ]
        flat = {}
        _flatten_categories(cats, flat)
        assert set(flat.keys()) == {1, 2}

    def test_nested_children(self):
        cats = [
            {
                "id": 1,
                "title": "Food",
                "children": [
                    {"id": 10, "title": "Groceries", "children": []},
                    {"id": 11, "title": "Dining", "children": []},
                ],
            }
        ]
        flat = {}
        _flatten_categories(cats, flat)
        assert set(flat.keys()) == {1, 10, 11}

    def test_deeply_nested(self):
        cats = [
            {
                "id": 1,
                "title": "Root",
                "children": [
                    {
                        "id": 2,
                        "title": "Mid",
                        "children": [
                            {"id": 3, "title": "Leaf", "children": []},
                        ],
                    }
                ],
            }
        ]
        flat = {}
        _flatten_categories(cats, flat)
        assert set(flat.keys()) == {1, 2, 3}

    def test_empty_list(self):
        flat = {}
        _flatten_categories([], flat)
        assert flat == {}


# ---------------------------------------------------------------------------
# _resolve_parent_title
# ---------------------------------------------------------------------------

class TestResolveParentTitle:
    def test_returns_parent_title(self):
        cat_meta = {
            1: {"id": 1, "title": "Food", "parent_id": None},
            10: {"id": 10, "title": "Groceries", "parent_id": 1},
        }
        assert _resolve_parent_title(10, cat_meta) == "Food"

    def test_no_parent_returns_none(self):
        cat_meta = {1: {"id": 1, "title": "Food", "parent_id": None}}
        assert _resolve_parent_title(1, cat_meta) is None

    def test_missing_parent_in_meta_returns_none(self):
        cat_meta = {10: {"id": 10, "title": "Groceries", "parent_id": 99}}
        assert _resolve_parent_title(10, cat_meta) is None


# ---------------------------------------------------------------------------
# _reconstruct_balance_rows
# ---------------------------------------------------------------------------

class TestReconstructBalanceRows:
    def test_empty_daily_nets_returns_empty(self):
        assert _reconstruct_balance_rows({}, 1000.0, date(2026, 5, 15)) == []

    def test_single_day(self):
        today = date(2026, 5, 15)
        # One transaction of +100 today means yesterday's balance was current - 100
        rows = _reconstruct_balance_rows({today: 100.0}, 1000.0, today)
        assert len(rows) == 1
        assert rows[0].mean == 1000.0

    def test_rows_sorted_ascending(self):
        today = date(2026, 5, 15)
        yesterday = date(2026, 5, 14)
        nets = {today: 50.0, yesterday: 30.0}
        rows = _reconstruct_balance_rows(nets, 500.0, today)
        starts = [r.start for r in rows]
        assert starts == sorted(starts)

    def test_balance_reconstructed_backwards(self):
        """Balance walks backwards from today's current_balance."""
        today = date(2026, 5, 3)
        day1 = date(2026, 5, 1)
        day2 = date(2026, 5, 2)
        day3 = date(2026, 5, 3)
        # Transactions: +100 on day1, +200 on day2, +50 on day3
        nets = {day1: 100.0, day2: 200.0, day3: 50.0}
        # Current balance after all = 1000
        rows = _reconstruct_balance_rows(nets, 1000.0, today)
        by_date = {r.start.date(): r.mean for r in rows}
        # day3 end balance = 1000 (current)
        assert by_date[day3] == 1000.0
        # day2 end balance = 1000 - 50 (day3 txn) = 950
        assert by_date[day2] == pytest.approx(950.0)
        # day1 end balance = 950 - 200 (day2 txn) = 750
        assert by_date[day1] == pytest.approx(750.0)

    def test_row_count_matches_date_range(self):
        start = date(2026, 5, 1)
        end = date(2026, 5, 10)
        nets = {date(2026, 5, i): 10.0 for i in range(1, 11)}
        rows = _reconstruct_balance_rows(nets, 500.0, end)
        assert len(rows) == 10


# ---------------------------------------------------------------------------
# _reconstruct_net_worth_rows
# ---------------------------------------------------------------------------

class TestReconstructNetWorthRows:
    def test_empty_returns_empty(self):
        assert _reconstruct_net_worth_rows({}, {}, date(2026, 5, 15)) == []

    def test_single_account_matches_balance_rows(self):
        today = date(2026, 5, 3)
        nets = {1: {today: 100.0}}
        balances = {1: 1000.0}
        rows = _reconstruct_net_worth_rows(nets, balances, today)
        assert len(rows) == 1
        assert rows[0].mean == pytest.approx(1000.0)

    def test_two_accounts_summed(self):
        today = date(2026, 5, 3)
        nets = {
            1: {today: 50.0},
            2: {today: 100.0},
        }
        balances = {1: 500.0, 2: 300.0}
        rows = _reconstruct_net_worth_rows(nets, balances, today)
        # Net worth today = 500 + 300 = 800
        assert rows[-1].mean == pytest.approx(800.0)

    def test_rows_sorted_ascending(self):
        d1 = date(2026, 5, 1)
        d2 = date(2026, 5, 2)
        nets = {1: {d1: 10.0, d2: 20.0}}
        balances = {1: 1000.0}
        rows = _reconstruct_net_worth_rows(nets, balances, d2)
        starts = [r.start for r in rows]
        assert starts == sorted(starts)


# ---------------------------------------------------------------------------
# BackfillState default values
# ---------------------------------------------------------------------------

class TestBackfillState:
    def test_defaults(self):
        bs = BackfillState()
        assert bs.status == BACKFILL_STATUS_IDLE
        assert bs.accounts_total == 0
        assert bs.accounts_remaining == 0
        assert bs.current_account is None

    def test_mutation(self):
        bs = BackfillState()
        bs.status = "running"
        bs.accounts_total = 5
        bs.accounts_remaining = 3
        bs.current_account = "Savings"
        assert bs.status == "running"
        assert bs.accounts_total == 5
        assert bs.accounts_remaining == 3
        assert bs.current_account == "Savings"
