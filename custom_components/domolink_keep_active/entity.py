"""Base entity logic for DomoLink KeepActive."""
from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    ATTR_DEVICE_CLASS,
    ATTR_ICON,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ATTR_GRACE_ACTIVE,
    ATTR_HOLD_ACTIVE,
    ATTR_SOURCE_ENTITY,
    ATTR_SOURCE_STATE,
    CONF_GRACE_PERIOD,
    CONF_HOLD_DURATION,
    CONF_NAME,
    CONF_OPTIMISTIC,
    CONF_SOURCE_ENTITY,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_HOLD_DURATION,
    DEFAULT_OPTIMISTIC,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class KeepActiveBaseEntity(RestoreEntity):
    """Base class providing hold-active and grace-period filtering."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry_id: str, config: dict[str, Any]) -> None:
        """Initialize the base keep-active proxy entity."""
        self._entry_id = entry_id
        self._source_entity_id: str = config[CONF_SOURCE_ENTITY]
        self._hold_duration: int = int(config.get(CONF_HOLD_DURATION, DEFAULT_HOLD_DURATION))
        self._grace_period: int = int(config.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD))
        self._optimistic: bool = bool(config.get(CONF_OPTIMISTIC, DEFAULT_OPTIMISTIC))
        
        custom_name = config.get(CONF_NAME)
        self._attr_name = custom_name if custom_name else f"KeepActive {self._source_entity_id}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{self._source_entity_id}"

        self._timer_hold: CALLBACK_TYPE | None = None
        self._timer_grace: CALLBACK_TYPE | None = None
        self._remove_listener: CALLBACK_TYPE | None = None

        self._source_state_str: str | None = None
        self._attr_available: bool = True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic state attributes."""
        return {
            ATTR_SOURCE_ENTITY: self._source_entity_id,
            ATTR_SOURCE_STATE: self._source_state_str,
            ATTR_HOLD_ACTIVE: self._timer_hold is not None,
            ATTR_GRACE_ACTIVE: self._timer_grace is not None,
            "hold_duration": self._hold_duration,
            "grace_period": self._grace_period,
        }

    async def async_added_to_hass(self) -> None:
        """Register listeners and restore last state."""
        await super().async_added_to_hass()

        # Listen to source entity state changes
        self._remove_listener = async_track_state_change_event(
            self.hass,
            [self._source_entity_id],
            self._async_source_state_changed_event,
        )

        # Sync initial state from source entity if already present in HA
        current_state = self.hass.states.get(self._source_entity_id)
        if current_state is not None:
            self._handle_new_source_state(current_state.state, current_state.attributes)
        else:
            # Fallback to restored state if source is not yet initialized
            last_state = await self.async_get_last_state()
            if last_state:
                self._handle_restored_state(last_state.state, last_state.attributes)

    async def async_will_remove_from_hass(self) -> None:
        """Cancel timers and event listeners on removal."""
        self._cancel_hold_timer()
        self._cancel_grace_timer()
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None
        await super().async_will_remove_from_hass()

    @callback
    def _cancel_hold_timer(self) -> None:
        """Cancel the hold timer if running."""
        if self._timer_hold:
            self._timer_hold()
            self._timer_hold = None

    @callback
    def _cancel_grace_timer(self) -> None:
        """Cancel the grace period timer if running."""
        if self._timer_grace:
            self._timer_grace()
            self._timer_grace = None

    @callback
    def _async_source_state_changed_event(self, event: Event) -> None:
        """Handle state change event from Home Assistant event bus."""
        new_state = event.data.get("new_state")
        if new_state is None:
            self._handle_new_source_state(STATE_UNAVAILABLE, {})
        else:
            self._handle_new_source_state(new_state.state, new_state.attributes)

    @callback
    def _handle_new_source_state(self, new_state_val: str, attributes: dict[str, Any]) -> None:
        """Core state machine handling transitions, timers, and grace periods."""
        self._source_state_str = new_state_val

        # Mirror device_class and icon if present
        if ATTR_DEVICE_CLASS in attributes and not getattr(self, "_attr_device_class", None):
            self._attr_device_class = attributes[ATTR_DEVICE_CLASS]
        if ATTR_ICON in attributes and not getattr(self, "_attr_icon", None):
            self._attr_icon = attributes[ATTR_ICON]

        # Case 1: Source is unavailable or unknown (reconnection, Zigbee OTA, restart)
        if new_state_val in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            if self._grace_period > 0:
                if self._timer_grace is None:
                    _LOGGER.debug(
                        "Source %s went %s. Starting grace period (%ds) for %s",
                        self._source_entity_id,
                        new_state_val,
                        self._grace_period,
                        getattr(self, "entity_id", self._attr_name),
                    )
                    self._timer_grace = async_call_later(
                        self.hass,
                        self._grace_period,
                        self._async_grace_expired,
                    )
                # Keep current value and available status during grace
                self.async_write_ha_state()
            else:
                self._attr_available = False
                self.async_write_ha_state()
            return

        # Case 2: Source is back online with a valid state
        if self._timer_grace:
            _LOGGER.debug(
                "Source %s recovered from unavailable/unknown. Canceling grace timer for %s",
                self._source_entity_id,
                getattr(self, "entity_id", self._attr_name),
            )
            self._cancel_grace_timer()

        self._attr_available = True
        self._apply_valid_source_state(new_state_val, attributes)

    @callback
    def _apply_valid_source_state(self, new_state_val: str, attributes: dict[str, Any]) -> None:
        """Override in subclasses to handle domain-specific state logic."""
        raise NotImplementedError

    @callback
    def _handle_restored_state(self, restored_val: str, attributes: dict[str, Any]) -> None:
        """Override in subclasses to restore initial state."""
        raise NotImplementedError

    @callback
    def _async_grace_expired(self, _now: Any) -> None:
        """Grace period expired while source entity is still unavailable."""
        self._timer_grace = None
        _LOGGER.warning(
            "Grace period expired for %s. Source %s is confirmed unavailable.",
            getattr(self, "entity_id", self._attr_name),
            self._source_entity_id,
        )
        self._attr_available = False
        self.async_write_ha_state()

    @callback
    def _async_hold_expired(self, _now: Any) -> None:
        """Hold period expired. Transition to inactive state."""
        self._timer_hold = None
        _LOGGER.debug(
            "Hold duration expired for %s. Releasing to inactive state.",
            getattr(self, "entity_id", self._attr_name),
        )
        self._on_hold_expired()

    @callback
    def _on_hold_expired(self) -> None:
        """Override in subclasses to transition entity to inactive."""
        raise NotImplementedError
