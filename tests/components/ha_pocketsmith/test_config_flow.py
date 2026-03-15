"""Tests for the PocketSmith config flow."""
import aiohttp
import pytest
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ha_pocketsmith.const import DOMAIN


async def test_form_is_shown(hass):
    """Test that the config form is presented on initial load."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_successful_setup(hass):
    """Test a valid developer key creates a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"developer_key": "valid_test_key"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "PocketSmith"
    assert result["data"] == {"developer_key": "valid_test_key"}


async def test_invalid_auth(hass):
    """Test that an invalid developer key shows the invalid_auth error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        side_effect=ValueError("invalid_auth"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"developer_key": "bad_key"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_insufficient_permissions(hass):
    """Test that a key without permissions shows the insufficient_permissions error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        side_effect=ValueError("insufficient_permissions"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"developer_key": "restricted_key"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "insufficient_permissions"}


async def test_cannot_connect(hass):
    """Test that a network error shows the cannot_connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        side_effect=aiohttp.ClientError(),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"developer_key": "some_key"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_entry(hass):
    """Test that a second setup attempt aborts with already_configured."""
    # First setup succeeds
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"developer_key": "valid_test_key"},
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Second attempt with the same unique_id should abort
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
