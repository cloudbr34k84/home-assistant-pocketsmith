"""Fixtures for ha_pocketsmith tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry

from custom_components.ha_pocketsmith.const import (
    DOMAIN,
    BackfillState,
    PocketSmithData,
)


# ---------------------------------------------------------------------------
# Auto-enable custom integrations (required by pytest-homeassistant-custom-component)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations, recorder_mock):
    """Enable custom integrations defined in the test dir."""
    yield


# ---------------------------------------------------------------------------
# Minimal coordinator / data fixtures
# ---------------------------------------------------------------------------

SAMPLE_USER = {
    "id": 42,
    "name": "Brad Test",
    "last_activity_at": "2026-05-01T00:00:00Z",
    "forecast_needs_recalculate": False,
}

SAMPLE_ACCOUNTS = [
    {"id": 1, "title": "Savings", "current_balance": 1000.0, "currency_code": "AUD",
     "transaction_accounts": []},
    {"id": 2, "title": "Checking", "current_balance": 500.0, "currency_code": "AUD",
     "transaction_accounts": []},
]

SAMPLE_COORDINATOR_DATA = {
    "user_id": 42,
    "user": SAMPLE_USER,
    "accounts": SAMPLE_ACCOUNTS,
    "uncategorised_count": 3,
    "categories": [],
    "budget": [],
    "monthly_transactions": {},
    "monthly_transaction_counts": {},
    "monthly_events": {},
    "enriched_categories": [],
    "forecast_last_updated": None,
}


@pytest.fixture
def mock_coordinator():
    """Return a mock PocketSmithCoordinator with sample data."""
    coordinator = MagicMock()
    coordinator.data = SAMPLE_COORDINATOR_DATA.copy()
    return coordinator


@pytest.fixture
def mock_entry(hass):
    """Return a mock config entry with PocketSmithData runtime_data."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = {"developer_key": "test_key_abc123"}
    entry.options = {}
    entry.runtime_data = PocketSmithData(
        coordinator=MagicMock(),
        backfill=BackfillState(),
    )
    return entry


# ---------------------------------------------------------------------------
# Config flow validation mocks
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_validate_ok():
    """Mock a successful developer key validation."""
    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        return_value=None,
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate_invalid_auth():
    """Mock an invalid-auth error."""
    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        side_effect=ValueError("invalid_auth"),
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate_insufficient_permissions():
    """Mock an insufficient-permissions error."""
    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        side_effect=ValueError("insufficient_permissions"),
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate_cannot_connect():
    """Mock a network/connectivity error."""
    import aiohttp

    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        side_effect=aiohttp.ClientError(),
    ) as mock:
        yield mock
