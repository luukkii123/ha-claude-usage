"""Fixed list of sensors for the claude.ai subscription usage limits."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ClaudeUsageConfigEntry, ClaudeUsageCoordinator

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="five_hour_utilization",
        name="Five-hour utilization",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key="seven_day_utilization",
        name="Seven-day utilization",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key="five_hour_reset",
        name="Five-hour reset",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="seven_day_reset",
        name="Seven-day reset",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="five_hour_status",
        name="Five-hour status",
    ),
    SensorEntityDescription(
        key="seven_day_status",
        name="Seven-day status",
    ),
    SensorEntityDescription(
        key="status",
        name="Overall status",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClaudeUsageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the fixed set of sensors from the coordinator."""
    coordinator = entry.runtime_data
    async_add_entities(
        ClaudeUsageSensor(coordinator, description) for description in SENSORS
    )


class ClaudeUsageSensor(CoordinatorEntity[ClaudeUsageCoordinator], SensorEntity):
    """One rate-limit sensor, fed by the coordinator's parsed headers."""

    _attr_has_entity_name = True

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: ClaudeUsageCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Name and unique ID come from the description's key."""
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Anthropic",
            model="claude.ai subscription",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        """Current value; missing headers stay None (HA shows unknown)."""
        return (self.coordinator.data or {}).get(self.entity_description.key)
