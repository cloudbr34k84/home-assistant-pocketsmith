"""Fixtures for ha_pocketsmith config flow tests."""
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture
def mock_validate_ok():
    """Return a fixture that mocks a successful developer key validation."""
    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        return_value=None,
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate_invalid_auth():
    """Return a fixture that mocks an invalid-auth error."""
    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        side_effect=ValueError("invalid_auth"),
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate_insufficient_permissions():
    """Return a fixture that mocks an insufficient-permissions error."""
    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        side_effect=ValueError("insufficient_permissions"),
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate_cannot_connect():
    """Return a fixture that mocks a network/connectivity error."""
    import aiohttp

    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        side_effect=aiohttp.ClientError(),
    ) as mock:
        yield mock
