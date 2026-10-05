"""Token normalization, error recovery, reauth precedence and options."""

from unittest.mock import AsyncMock

import pytest
from custom_components.claude_usage.coordinator import InvalidTokenError
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.parametrize(
    "failure,error",
    [
        (None, "empty_token"),
        (InvalidTokenError("invalid"), "invalid_auth"),
        (UpdateFailed("offline"), "cannot_connect"),
    ],
)
async def test_user_error_then_success(hass, monkeypatch, failure, error):
    probe = AsyncMock(side_effect=failure)
    monkeypatch.setattr("custom_components.claude_usage.config_flow.fetch_usage", probe)
    result = await hass.config_entries.flow.async_init(
        "claude_usage", context={"source": "user"}
    )
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_token": "   " if failure is None else "example-token"}
    )
    assert error in result["errors"].values()
    probe.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_token": "  example-token  ", "scan_interval": 300}
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {"api_token": "example-token", "scan_interval": 300}
    assert result["result"].unique_id == "claude_usage"


async def test_duplicate_is_aborted(hass, monkeypatch):
    monkeypatch.setattr(
        "custom_components.claude_usage.config_flow.fetch_usage", AsyncMock()
    )
    MockConfigEntry(
        domain="claude_usage",
        unique_id="claude_usage",
        data={"api_token": "example-old"},
    ).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        "claude_usage", context={"source": "user"}, data={"api_token": "example-token"}
    )
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "failure,error",
    [
        (None, "empty_token"),
        (InvalidTokenError("invalid"), "invalid_auth"),
        (UpdateFailed("offline"), "cannot_connect"),
    ],
)
async def test_reauth_error_then_replaces_stale_option(
    hass, monkeypatch, failure, error
):
    probe = AsyncMock(side_effect=failure)
    monkeypatch.setattr("custom_components.claude_usage.config_flow.fetch_usage", probe)
    monkeypatch.setattr(
        hass.config_entries, "async_reload", AsyncMock(return_value=True)
    )
    entry = MockConfigEntry(
        domain="claude_usage",
        unique_id="claude_usage",
        data={"api_token": "example-old", "scan_interval": 300},
        options={"api_token": "example-stale", "scan_interval": 600},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        "claude_usage",
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_token": " " if failure is None else "example-new"}
    )
    assert error in result["errors"].values()
    probe.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_token": " example-new "}
    )
    assert result["reason"] == "reauth_successful"
    assert entry.data["api_token"] == "example-new"
    assert entry.options == {"scan_interval": 600}


@pytest.mark.parametrize(
    "token,want",
    [
        (" ", {"scan_interval": 600}),
        (" example-new ", {"api_token": "example-new", "scan_interval": 600}),
    ],
)
async def test_options_blank_keeps_token(hass, token, want):
    entry = MockConfigEntry(
        domain="claude_usage", data={"api_token": "example-old", "scan_interval": 300}
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"api_token": token, "scan_interval": 600}
    )
    assert result["type"] == "create_entry"
    assert entry.options == want
    assert entry.data["api_token"] == "example-old"
