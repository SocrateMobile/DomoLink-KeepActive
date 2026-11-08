"""Constants for the DomoLink KeepActive integration."""
from __future__ import annotations

DOMAIN = "domolink_keep_active"

CONF_SOURCE_ENTITY = "source_entity"
CONF_HOLD_DURATION = "hold_duration"
CONF_GRACE_PERIOD = "grace_period"
CONF_OPTIMISTIC = "optimistic"
CONF_NAME = "name"

DEFAULT_HOLD_DURATION = 30  # seconds
DEFAULT_GRACE_PERIOD = 60   # seconds
DEFAULT_OPTIMISTIC = True

ATTR_SOURCE_ENTITY = "source_entity"
ATTR_SOURCE_STATE = "source_state"
ATTR_HOLD_ACTIVE = "hold_active"
ATTR_GRACE_ACTIVE = "grace_active"
ATTR_REMAINING_HOLD_SECONDS = "remaining_hold_seconds"

SUPPORTED_DOMAINS = ["binary_sensor", "sensor", "switch"]
