"""Tests for PocketSmith sensor entities."""
import pytest
from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntry

from custom_components.ha_pocketsmith.const import (
    BACKFILL_STATUS_IDLE,
    BACKFILL_STATUS_RUNNING,
    BACKFILL_STATUS_COMPLETE,
    CONF_ACTIVE_CURRENCY,
    BackfillState,
)
from custom_components.ha_pocketsmith.sensor import (
    PocketSmithBackfillSensor,
    PocketSmithNetWorthSensor,
    PocketSmithSensor,
    PocketSmithUncategorisedTransactions,
    PocketSmithCategorySensor,
)


def _make_coordinator(data):
    coord = MagicMock()
    coord.data = data
    return coord


def _make_entry(options=None):
    entry = MagicMock(spec=ConfigEntry)
    entry.options = options or {}
    return entry


SAMPLE_DATA = {
    "user_id": 42,
    "accounts": [
        {"id": 1, "title": "Savings", "current_balance": 1000.0,
         "currency_code": "AUD", "transaction_accounts": []},
        {"id": 2, "title": "Checking", "current_balance": 500.0,
         "currency_code": "AUD", "transaction_accounts": []},
    ],
    "uncategorised_count": 5,
    "enriched_categories": [],
}


# ---------------------------------------------------------------------------
# PocketSmithSensor (account balance)
# ---------------------------------------------------------------------------

class TestPocketSmithSensor:
    def _make(self, account):
        coord = _make_coordinator(SAMPLE_DATA)
        return PocketSmithSensor(coord, account)

    def test_native_value(self):
        sensor = self._make(SAMPLE_DATA["accounts"][0])
        assert sensor.native_value == 1000.0

    def test_unique_id_is_stable(self):
        sensor = self._make(SAMPLE_DATA["accounts"][0])
        assert "1" in sensor.unique_id
        assert "savings" in sensor.unique_id

    def test_native_unit_of_measurement(self):
        sensor = self._make(SAMPLE_DATA["accounts"][0])
        assert sensor.native_unit_of_measurement == "AUD"

    def test_extra_state_attributes_has_transaction_accounts(self):
        sensor = self._make(SAMPLE_DATA["accounts"][0])
        attrs = sensor.extra_state_attributes
        assert "transaction_accounts" in attrs

    def test_missing_account_returns_empty(self):
        """Sensor handles coordinator data missing its account gracefully."""
        coord = _make_coordinator({**SAMPLE_DATA, "accounts": []})
        sensor = PocketSmithSensor(coord, {"id": 99, "title": "Gone", "current_balance": 0.0, "currency_code": "AUD"})
        # _account property should return {}
        assert sensor.native_value is None


# ---------------------------------------------------------------------------
# PocketSmithUncategorisedTransactions
# ---------------------------------------------------------------------------

class TestUncategorisedSensor:
    def test_native_value(self):
        coord = _make_coordinator(SAMPLE_DATA)
        sensor = PocketSmithUncategorisedTransactions(coord)
        assert sensor.native_value == 5

    def test_unique_id_contains_user_id(self):
        coord = _make_coordinator(SAMPLE_DATA)
        sensor = PocketSmithUncategorisedTransactions(coord)
        assert "42" in sensor.unique_id


# ---------------------------------------------------------------------------
# PocketSmithNetWorthSensor
# ---------------------------------------------------------------------------

class TestNetWorthSensor:
    def _make(self, options=None):
        coord = _make_coordinator(SAMPLE_DATA)
        entry = _make_entry(options)
        return PocketSmithNetWorthSensor(coord, entry)

    def test_sums_all_accounts(self):
        sensor = self._make()
        assert sensor.native_value == 1500.0

    def test_default_currency_from_first_account(self):
        sensor = self._make()
        assert sensor.native_unit_of_measurement == "AUD"

    def test_active_currency_option_respected(self):
        sensor = self._make(options={CONF_ACTIVE_CURRENCY: "USD"})
        assert sensor.native_unit_of_measurement == "USD"

    def test_zero_balance_accounts(self):
        data = {**SAMPLE_DATA, "accounts": [
            {"id": 1, "title": "Zero", "current_balance": 0.0, "currency_code": "AUD", "transaction_accounts": []}
        ]}
        coord = _make_coordinator(data)
        sensor = PocketSmithNetWorthSensor(coord, _make_entry())
        assert sensor.native_value == 0.0

    def test_no_accounts_returns_zero(self):
        data = {**SAMPLE_DATA, "accounts": []}
        coord = _make_coordinator(data)
        sensor = PocketSmithNetWorthSensor(coord, _make_entry())
        assert sensor.native_value == 0


# ---------------------------------------------------------------------------
# PocketSmithCategorySensor
# ---------------------------------------------------------------------------

ENRICHED_CAT = {
    "category_id": 10,
    "category_title": "Groceries",
    "parent_id": None,
    "parent_title": None,
    "is_bill": False,
    "budgeted": 300.0,
    "actual": 150.0,
    "remaining": 150.0,
    "over_by": 0,
    "over_budget": False,
    "percentage_used": 50.0,
    "currency": "AUD",
    "transaction_count": 5,
    "category_level": 1,
}


class TestCategorySensor:
    def _make(self):
        data = {**SAMPLE_DATA, "enriched_categories": [ENRICHED_CAT]}
        coord = _make_coordinator(data)
        return PocketSmithCategorySensor(coord, ENRICHED_CAT)

    def test_native_value(self):
        assert self._make().native_value == 150.0

    def test_unique_id_contains_category_id(self):
        assert "10" in self._make().unique_id

    def test_not_over_budget_icon(self):
        assert self._make().icon == "mdi:cash-check"

    def test_over_budget_icon(self):
        cat = {**ENRICHED_CAT, "over_budget": True}
        data = {**SAMPLE_DATA, "enriched_categories": [cat]}
        coord = _make_coordinator(data)
        sensor = PocketSmithCategorySensor(coord, cat)
        assert sensor.icon == "mdi:cash-remove"

    def test_extra_state_attributes(self):
        attrs = self._make().extra_state_attributes
        assert attrs["is_rollup"] is False
        assert attrs["category_id"] == 10
        assert attrs["percentage_used"] == 50.0

    def test_no_actual_returns_zero(self):
        cat = {**ENRICHED_CAT, "actual": None}
        data = {**SAMPLE_DATA, "enriched_categories": [cat]}
        coord = _make_coordinator(data)
        sensor = PocketSmithCategorySensor(coord, cat)
        assert sensor.native_value == 0


# ---------------------------------------------------------------------------
# PocketSmithBackfillSensor
# ---------------------------------------------------------------------------

class TestBackfillSensor:
    def _make(self, state=None):
        coord = _make_coordinator(SAMPLE_DATA)
        bs = state or BackfillState()
        return PocketSmithBackfillSensor(coord, bs)

    def test_default_state_is_idle(self):
        assert self._make().native_value == BACKFILL_STATUS_IDLE

    def test_running_state(self):
        bs = BackfillState(status=BACKFILL_STATUS_RUNNING, accounts_total=3, accounts_remaining=2, current_account="Savings")
        sensor = self._make(bs)
        assert sensor.native_value == BACKFILL_STATUS_RUNNING
        attrs = sensor.extra_state_attributes
        assert attrs["accounts_total"] == 3
        assert attrs["accounts_remaining"] == 2
        assert attrs["current_account"] == "Savings"

    def test_complete_state(self):
        bs = BackfillState(status=BACKFILL_STATUS_COMPLETE, accounts_total=3, accounts_remaining=0)
        sensor = self._make(bs)
        assert sensor.native_value == BACKFILL_STATUS_COMPLETE
        assert sensor.extra_state_attributes["accounts_remaining"] == 0

    def test_unique_id_contains_user_id(self):
        assert "42" in self._make().unique_id
