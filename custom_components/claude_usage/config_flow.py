"""Config flow: claude.ai OAuth token, polling interval and reauth."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    CONF_API_TOKEN,
    CONF_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import ClaudeUsageConfigEntry, InvalidTokenError, fetch_usage

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
        ),
    }
)


STEP_REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


class ClaudeUsageConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup form for the Claude Usage integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the form, validate the token with a probe call, then create it."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_API_TOKEN].strip()
            if not token:
                errors[CONF_API_TOKEN] = "empty_token"
            else:
                user_input[CONF_API_TOKEN] = token
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                try:
                    await fetch_usage(self.hass, token)
                except InvalidTokenError:
                    errors["base"] = "invalid_auth"
                except UpdateFailed:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """The coordinator saw a 401/403 — Home Assistant asks for a new token.

        There is no refresh token by design (see docs/stand.md, "claude_usage:
        warum es beim OAuth-Token bleibt"). Reauth is the supported way to say
        so out loud: HA shows "Reconfigure"/"Sign in again" in the sidebar
        instead of letting the sensors rot as unavailable.
        """
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Take a fresh token, probe it, then replace the stored one."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            token = str(user_input.get(CONF_API_TOKEN, "")).strip()
            if not token:
                errors[CONF_API_TOKEN] = "empty_token"
            else:
                try:
                    await fetch_usage(self.hass, token)
                except InvalidTokenError:
                    errors["base"] = "invalid_auth"
                except UpdateFailed:
                    errors["base"] = "cannot_connect"
                else:
                    # The token has to leave the options as well: the
                    # coordinator reads `options[api_token] or data[api_token]`,
                    # so a stale token in the options would beat the new one.
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={CONF_API_TOKEN: token},
                        options={
                            key: value
                            for key, value in entry.options.items()
                            if key != CONF_API_TOKEN
                        },
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        entry: ClaudeUsageConfigEntry,
    ) -> ClaudeUsageOptionsFlow:
        """Return the options flow for later interval/token changes."""
        return ClaudeUsageOptionsFlow()


class ClaudeUsageOptionsFlow(OptionsFlow):
    """Adjust the polling interval or replace the token later."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Interval and token; a blank token keeps the one from setup."""
        if user_input is not None:
            token = user_input.get(CONF_API_TOKEN, "").strip()
            if token:
                user_input[CONF_API_TOKEN] = token
            else:
                user_input.pop(CONF_API_TOKEN, None)
            return self.async_create_entry(data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_API_TOKEN, default=""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
