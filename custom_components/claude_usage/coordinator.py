"""Poll the Anthropic Messages API and parse the unified rate-limit headers.

This is the integration's data source: a minimal Haiku probe call whose response
*headers* carry the claude.ai subscription's rolling usage limits. The body is
irrelevant — we only ever read `anthropic-ratelimit-unified-*` headers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import httpx

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ANTHROPIC_BETA,
    ANTHROPIC_ENDPOINT,
    ANTHROPIC_MODEL,
    ANTHROPIC_VERSION,
    CONF_API_TOKEN,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HEADER_5H_RESET,
    HEADER_5H_STATUS,
    HEADER_5H_UTILIZATION,
    HEADER_7D_RESET,
    HEADER_7D_STATUS,
    HEADER_7D_UTILIZATION,
    HEADER_STATUS,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

# Assignment rather than `type ...` (PEP 695) so the file still parses under
# Python 3.11 — it is only syntax-checked here, not run.
ClaudeUsageConfigEntry = ConfigEntry["ClaudeUsageCoordinator"]


class InvalidTokenError(Exception):
    """Raised when the API rejects the token (401/403)."""


def _parse_utilization(value: str | None) -> float | None:
    """Parse a 0–1 fraction into a percentage, or None when missing/invalid."""
    if not value:
        return None
    try:
        return round(float(value) * 100, 2)
    except ValueError:
        return None


def _parse_reset(value: str | None) -> datetime | None:
    """Parse a Unix-epoch timestamp into a UTC datetime, or None."""
    if not value:
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def _parse_status(value: str | None) -> str | None:
    """Normalize a status header, or None when missing/empty."""
    if not value:
        return None
    return value.strip() or None


def _extract_headers(response: httpx.Response) -> dict[str, Any]:
    """Read the unified rate-limit headers into a fixed-key dict."""
    headers = response.headers
    return {
        "five_hour_utilization": _parse_utilization(
            headers.get(HEADER_5H_UTILIZATION)
        ),
        "seven_day_utilization": _parse_utilization(
            headers.get(HEADER_7D_UTILIZATION)
        ),
        "five_hour_reset": _parse_reset(headers.get(HEADER_5H_RESET)),
        "seven_day_reset": _parse_reset(headers.get(HEADER_7D_RESET)),
        "five_hour_status": _parse_status(headers.get(HEADER_5H_STATUS)),
        "seven_day_status": _parse_status(headers.get(HEADER_7D_STATUS)),
        "status": _parse_status(headers.get(HEADER_STATUS)),
    }


async def fetch_usage(hass: HomeAssistant, token: str) -> dict[str, Any]:
    """POST a minimal Haiku probe and return the parsed rate-limit headers.

    Raises ``InvalidTokenError`` on 401/403 and ``UpdateFailed`` on any other
    failure. Also used by the config flow to validate a freshly entered token.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "anthropic-beta": ANTHROPIC_BETA,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "x"}],
    }

    client = get_async_client(hass)
    try:
        response = await client.post(
            ANTHROPIC_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as err:
        status = err.response.status_code
        if status in (401, 403):
            raise InvalidTokenError(
                f"Token rejected with HTTP {status} — expired or invalid."
            ) from err
        if status == 429:
            retry_after = err.response.headers.get("retry-after", "unknown")
            raise UpdateFailed(
                f"Rate limited (429); retry-after={retry_after}s. "
                "Consider raising the scan interval."
            ) from err
        raise UpdateFailed(f"Anthropic API returned HTTP {status}.") from err
    except httpx.HTTPError as err:
        raise UpdateFailed(f"Anthropic API not reachable: {err}") from err

    return _extract_headers(response)


class ClaudeUsageCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the Anthropic API and hold the latest rate-limit state."""

    config_entry: ClaudeUsageConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> None:
        """Read the token and interval; options override the setup values."""
        self._token: str = entry.options.get(CONF_API_TOKEN) or entry.data[
            CONF_API_TOKEN
        ]
        interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """One poll round. Failures become UpdateFailed so HA surfaces them."""
        try:
            return await fetch_usage(self.hass, self._token)
        except InvalidTokenError as err:
            _LOGGER.warning("Claude Usage token rejected (likely expired): %s", err)
            # ConfigEntryAuthFailed, not UpdateFailed: this starts the reauth
            # flow, so Home Assistant offers "Sign in again" instead of just
            # marking the sensors unavailable.
            raise ConfigEntryAuthFailed(
                "Token rejected (401/403) — it is likely expired. Enter a new "
                "one in the re-authentication dialog."
            ) from err
