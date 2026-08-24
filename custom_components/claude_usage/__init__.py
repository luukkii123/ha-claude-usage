"""Claude Usage — claude.ai subscription usage limits as sensors."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import ClaudeUsageConfigEntry, ClaudeUsageCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: ClaudeUsageConfigEntry
) -> bool:
    """Set up the entry: fetch once, then load the platforms."""
    coordinator = ClaudeUsageCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ClaudeUsageConfigEntry
) -> bool:
    """Unload the entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant, entry: ClaudeUsageConfigEntry
) -> None:
    """Reload after an options change (e.g. interval or token)."""
    await hass.config_entries.async_reload(entry.entry_id)
