"""Switch platform for DomoLink KeepActive."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .entity import KeepActiveBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the KeepActive switch entry."""
    entity = KeepActiveSwitch(entry.entry_id, entry.data | entry.options)
    async_add_entities([entity], True)


class KeepActiveSwitch(KeepActiveBaseEntity, SwitchEntity):
    """Switch proxy with optimistic toggling, hold duration, and dropout protection."""

    def __init__(self, entry_id: str, config: dict[str, Any]) -> None:
        """Initialize the switch proxy."""
        super().__init__(entry_id, config)
        self._attr_is_on: bool = False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Forward turn_on to source entity, optimistically holding state."""
        if self._optimistic:
            self._cancel_hold_timer()
            self._attr_is_on = True
            self.async_write_ha_state()

        await self.hass.services.async_call(
            "homeassistant",
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self._source_entity_id},
            blocking=False,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Forward turn_off to source entity."""
        if self._hold_duration > 0 and self._attr_is_on:
            if self._timer_hold is None:
                self._timer_hold = async_call_later(
                    self.hass,
                    self._hold_duration,
                    self._async_hold_expired,
                )
            self.async_write_ha_state()
            # Also send command to physical device
            await self.hass.services.async_call(
                "homeassistant",
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: self._source_entity_id},
                blocking=False,
            )
            return

        if self._optimistic:
            self._cancel_hold_timer()
            self._attr_is_on = False
            self.async_write_ha_state()

        await self.hass.services.async_call(
            "homeassistant",
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self._source_entity_id},
            blocking=False,
        )

    @callback
    def _apply_valid_source_state(self, new_state_val: str, attributes: dict[str, Any]) -> None:
        """Handle incoming switch state."""
        is_source_on = (new_state_val == STATE_ON)

        if is_source_on:
            self._cancel_hold_timer()
            self._attr_is_on = True
            self.async_write_ha_state()
            return

        if self._attr_is_on:
            if self._hold_duration > 0:
                if self._timer_hold is None:
                    _LOGGER.debug(
                        "Source %s switched off. Holding active state (%ds) for %s",
                        self._source_entity_id,
                        self._hold_duration,
                        getattr(self, "entity_id", self._attr_name),
                    )
                    self._timer_hold = async_call_later(
                        self.hass,
                        self._hold_duration,
                        self._async_hold_expired,
                    )
                self.async_write_ha_state()
            else:
                self._attr_is_on = False
                self.async_write_ha_state()
        else:
            self._attr_is_on = False
            self.async_write_ha_state()

    @callback
    def _on_hold_expired(self) -> None:
        """Transition switch to off upon hold expiration."""
        self._attr_is_on = False
        self.async_write_ha_state()

    @callback
    def _handle_restored_state(self, restored_val: str, attributes: dict[str, Any]) -> None:
        """Restore previous state."""
        self._attr_is_on = (restored_val == STATE_ON)
