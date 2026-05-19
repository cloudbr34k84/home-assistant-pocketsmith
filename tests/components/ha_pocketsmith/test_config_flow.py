"""Tests for the PocketSmith config flow."""
import aiohttp
import asyncio
import pytest
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ha_pocketsmith.const import (
    CONF_ENABLE_BACKFILL,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_ENABLE_BACKFILL,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
)


# ---------------------------------------------------------------------------
# Initial setup flow
# ---------------------------------------------------------------------------

async def test_form_is_shown(recorder_mock, hass):
    """Config form is presented on initial load."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_successful_setup(recorder_mock, hass):
    """Valid developer key creates a config entry."""
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


async def test_invalid_auth(recorder_mock, hass):
    """Invalid developer key shows invalid_auth error."""
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


async def test_insufficient_permissions(recorder_mock, hass):
    """Key without permissions shows insufficient_permissions error."""
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


async def test_cannot_connect(recorder_mock, hass):
    """Network error shows cannot_connect error."""
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


async def test_timeout_shows_cannot_connect(recorder_mock, hass):
    """Timeout shows cannot_connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        side_effect=asyncio.TimeoutError(),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"developer_key": "some_key"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_unknown_exception_shows_unknown(recorder_mock, hass):
    """Unexpected exception shows unknown error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        side_effect=RuntimeError("boom"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"developer_key": "some_key"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_duplicate_entry(recorder_mock, hass):
    """Second setup attempt aborts with already_configured."""
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

    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# Reconfigure flow
# ---------------------------------------------------------------------------

async def _create_entry(hass) -> config_entries.ConfigEntry:
    """Helper: create a config entry via the normal user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"developer_key": "original_key"},
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    return hass.config_entries.async_get_entry(result["result"].entry_id)


async def test_reconfigure_form_is_shown(recorder_mock, hass):
    """Reconfigure step shows form pre-filled with current key."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"


async def test_reconfigure_success(recorder_mock, hass):
    """Reconfigure with valid new key updates entry data and aborts with reconfigure_successful."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )

    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        return_value=None,
    ), patch.object(hass.config_entries, "async_reload"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"developer_key": "new_key_xyz"},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["developer_key"] == "new_key_xyz"


async def test_reconfigure_invalid_auth(recorder_mock, hass):
    """Reconfigure with bad key shows invalid_auth error."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
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


# ---------------------------------------------------------------------------
# Reauth flow
# ---------------------------------------------------------------------------

async def test_reauth_form_is_shown(recorder_mock, hass):
    """Reauth step shows the reauth_confirm form."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


async def test_reauth_success(recorder_mock, hass):
    """Reauth with valid key updates entry and aborts with reauth_successful."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )

    with patch(
        "custom_components.ha_pocketsmith.config_flow._validate_developer_key",
        return_value=None,
    ), patch.object(hass.config_entries, "async_reload"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"developer_key": "reauthed_key"},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["developer_key"] == "reauthed_key"


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------

async def test_options_flow_defaults(recorder_mock, hass):
    """Options form shows with current defaults."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_saves(recorder_mock, hass):
    """Options flow saves updated interval and backfill values."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_UPDATE_INTERVAL_HOURS: 4,
            CONF_ENABLE_BACKFILL: False,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_UPDATE_INTERVAL_HOURS] == 4
    assert entry.options[CONF_ENABLE_BACKFILL] is False


async def test_options_flow_default_values(recorder_mock, hass):
    """Options flow with no prior options uses the built-in defaults."""
    entry = await _create_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_UPDATE_INTERVAL_HOURS: DEFAULT_UPDATE_INTERVAL_HOURS,
            CONF_ENABLE_BACKFILL: DEFAULT_ENABLE_BACKFILL,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_UPDATE_INTERVAL_HOURS] == DEFAULT_UPDATE_INTERVAL_HOURS
    assert entry.options[CONF_ENABLE_BACKFILL] == DEFAULT_ENABLE_BACKFILL
