"""Constants for the DomoLink KeepActive integration."""
from __future__ import annotations

DOMAIN = "domolink_keep_active"
NAME = "DomoLink KeepActive"
VERSION = "1.2.5"

PANEL_TITLE = "DomoLink KeepActive"
PANEL_ICON = "mdi:heart-flash"
PANEL_NAME = "domolink-keep-active-panel"
PANEL_URL_PATH = "domolink_keep_active"
FRONTEND_URL_PATH = "/domolink_keep_active_panel"
FRONTEND_FILE_NAME = "domolink-keep-active-panel.js"

CONF_ENABLE_PANEL = "enable_panel"
CONF_SOURCE_ENTITY = "source_entity"
CONF_HOLD_DURATION = "hold_duration"
CONF_GRACE_PERIOD = "grace_period"
CONF_OPTIMISTIC = "optimistic"
CONF_NAME = "name"
CONF_RULES = "rules"
CONF_RULE_ID = "rule_id"

CONF_OTA_DURATION = "ota_duration"
CONF_PING_INTERVAL = "ping_interval"
CONF_PING_METHOD = "ping_method"
CONF_AUTO_OTA_TRIGGER = "auto_ota_trigger"
CONF_ON_OTA_FAILURE = "on_ota_failure"
CONF_ON_OTA_TIMEOUT = "on_ota_timeout"

DEFAULT_HOLD_DURATION = 30  # seconds
DEFAULT_GRACE_PERIOD = 60   # seconds
DEFAULT_OPTIMISTIC = True

DEFAULT_OTA_DURATION = 30   # minutes (range 10 - 90)
DEFAULT_PING_INTERVAL = 5   # seconds (range 1 - 60)
DEFAULT_PING_METHOD = "auto"
DEFAULT_AUTO_OTA_TRIGGER = True

# OTA Failure & Timeout Behaviors
OTA_FAILURE_KEEP_ALIVE = "keep_alive"
OTA_FAILURE_STOP = "stop"
OTA_FAILURE_RETRY = "retry"
DEFAULT_ON_OTA_FAILURE = OTA_FAILURE_KEEP_ALIVE

OTA_TIMEOUT_EXTEND = "auto_extend"
OTA_TIMEOUT_STOP = "stop"
DEFAULT_ON_OTA_TIMEOUT = OTA_TIMEOUT_EXTEND

AUTO_EXTEND_MINUTES = 15
MAX_OTA_RETRIES = 2

OTA_FAILURE_MODES = [OTA_FAILURE_KEEP_ALIVE, OTA_FAILURE_STOP, OTA_FAILURE_RETRY]
OTA_TIMEOUT_MODES = [OTA_TIMEOUT_EXTEND, OTA_TIMEOUT_STOP]

MIN_OTA_DURATION = 10       # minutes
MAX_OTA_DURATION = 90       # minutes
MIN_PING_INTERVAL = 1       # seconds
MAX_PING_INTERVAL = 60      # seconds

PING_METHODS = ["auto", "z2m_get", "zha_ping", "ha_update"]

ACTION_VIEW = "view"
ACTION_ADD = "add"
ACTION_EDIT = "edit"
ACTION_DELETE = "delete"

ATTR_SOURCE_ENTITY = "source_entity"
ATTR_SOURCE_STATE = "source_state"
ATTR_HOLD_ACTIVE = "hold_active"
ATTR_GRACE_ACTIVE = "grace_active"
ATTR_REMAINING_HOLD_SECONDS = "remaining_hold_seconds"

SUPPORTED_DOMAINS = ["binary_sensor", "sensor", "switch"]
