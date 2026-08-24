"""Constants for the Claude Usage integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "claude_usage"

CONF_API_TOKEN: Final = "api_token"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_NAME: Final = "Claude Usage"
DEFAULT_SCAN_INTERVAL: Final = 300
MIN_SCAN_INTERVAL: Final = 60
MAX_SCAN_INTERVAL: Final = 3600

REQUEST_TIMEOUT: Final = 15

ANTHROPIC_ENDPOINT: Final = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION: Final = "2023-06-01"
ANTHROPIC_BETA: Final = "oauth-2025-04-20"
ANTHROPIC_MODEL: Final = "claude-haiku-4-5"

HEADER_5H_UTILIZATION: Final = "anthropic-ratelimit-unified-5h-utilization"
HEADER_5H_RESET: Final = "anthropic-ratelimit-unified-5h-reset"
HEADER_7D_UTILIZATION: Final = "anthropic-ratelimit-unified-7d-utilization"
HEADER_7D_RESET: Final = "anthropic-ratelimit-unified-7d-reset"
HEADER_STATUS: Final = "anthropic-ratelimit-unified-status"
HEADER_5H_STATUS: Final = "anthropic-ratelimit-unified-5h-status"
HEADER_7D_STATUS: Final = "anthropic-ratelimit-unified-7d-status"
