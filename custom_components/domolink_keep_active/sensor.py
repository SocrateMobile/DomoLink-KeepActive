"""Sensor platform for DomoLink KeepActive."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import KeepActiveBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the KeepActive sensor entry."""
    entity = KeepActiveSensor(entry.entry_id, entry.data | entry.options)
    async_add_entities([entity], True)


class KeepActiveSensor(KeepActiveBaseEntity, SensorEntity):
    """Sensor proxy maintaining last valid value across brief dropouts."""

    def __init__(self, entry_id: str, config: dict[str, Any]) -> None:
        """Initialize the sensor proxy."""
        super().__init__(entry_id, config)
        self._attr_native_value: Any = None

    @callback
    def _apply_valid_source_state(self, new_state_val: str, attributes: dict[str, Any]) -> None:
        """Apply valid sensor state and copy unit if available."""
        if ATTR_UNIT_OF_MEASUREMENT in attributes:
            self._attr_native_unit_of_measurement = attributes[ATTR_UNIT_OF_MEASUREMENT]
        if "state_class" in attributes:
            self._attr_state_class = attributes["state_class"]

        self._attr_native_value = new_state_val
        self.async_write_ha_state()

    @callback
    def _on_hold_expired(self) -> None:
        """Sensor does not clear value on hold expiration; maintained for API parity."""
        self.async_write_ha_state()

    @callback
    def _handle_restored_state(self, restored_val: str, attributes: dict[str, Any]) -> None:
        """Restore previous sensor value."""
        self._attr_native_value = restored_val
        if ATTR_UNIT_OF_MEASUREMENT in attributes:
            self._attr_native_unit_of_measurement = attributes[ATTR_UNIT_OF_MEASUREMENT]
