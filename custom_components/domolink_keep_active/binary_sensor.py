"""Binary sensor platform for DomoLink KeepActive."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import CONF_SOURCE_ENTITY
from .entity import KeepActiveBaseEntity
from .helpers import get_platform_from_entity, get_rules_from_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the KeepActive binary sensor entries."""
    rules = get_rules_from_entry(entry)
    entities = [
        KeepActiveBinarySensor(entry.entry_id, rule)
        for rule in rules
        if get_platform_from_entity(rule[CONF_SOURCE_ENTITY]) == "binary_sensor"
    ]
    if entities:
        async_add_entities(entities, True)


class KeepActiveBinarySensor(KeepActiveBaseEntity, BinarySensorEntity):
    """Binary sensor proxy maintaining active state and smoothing disconnects."""

    def __init__(self, entry_id: str, config: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(entry_id, config)
        self._attr_is_on: bool = False

    @callback
    def _apply_valid_source_state(self, new_state_val: str, attributes: dict[str, Any]) -> None:
        """Handle binary state changes with hold timer."""
        is_source_on = new_state_val == STATE_ON

        if is_source_on:
            # Source became active: cancel hold timer immediately and set state to ON
            self._cancel_hold_timer()
            self._attr_is_on = True
            self.async_write_ha_state()
            return

        # Source became inactive (OFF)
        if self._attr_is_on:
            if self._hold_duration > 0:
                if self._timer_hold is None:
                    _LOGGER.debug(
                        "Source %s turned off. Holding active state (%ds) for %s",
                        self._source_entity_id,
                        self._hold_duration,
                        getattr(self, "entity_id", self._attr_name),
                    )
                    self._timer_hold = async_call_later(
                        self.hass,
                        self._hold_duration,
                        self._async_hold_expired,
                    )
                # Keep is_on = True during hold duration
                self.async_write_ha_state()
            else:
                self._attr_is_on = False
                self.async_write_ha_state()
        else:
            self._attr_is_on = False
            self.async_write_ha_state()

    @callback
    def _on_hold_expired(self) -> None:
        """Called when hold duration finishes."""
        self._attr_is_on = False
        self.async_write_ha_state()

    @callback
    def _handle_restored_state(self, restored_val: str, attributes: dict[str, Any]) -> None:
        """Restore previous state."""
        self._attr_is_on = (restored_val == STATE_ON)
