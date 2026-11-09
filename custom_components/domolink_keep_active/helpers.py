"""Helper utilities for DomoLink KeepActive."""
from __future__ import annotations

from typing import Any
from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_AUTO_OTA_TRIGGER,
    CONF_GRACE_PERIOD,
    CONF_HOLD_DURATION,
    CONF_NAME,
    CONF_OPTIMISTIC,
    CONF_OTA_DURATION,
    CONF_PING_INTERVAL,
    CONF_PING_METHOD,
    CONF_RULES,
    CONF_RULE_ID,
    CONF_SOURCE_ENTITY,
    DEFAULT_AUTO_OTA_TRIGGER,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_HOLD_DURATION,
    DEFAULT_OPTIMISTIC,
    DEFAULT_OTA_DURATION,
    DEFAULT_PING_INTERVAL,
    DEFAULT_PING_METHOD,
    MAX_OTA_DURATION,
    MAX_PING_INTERVAL,
    MIN_OTA_DURATION,
    MIN_PING_INTERVAL,
    SUPPORTED_DOMAINS,
)


def get_platform_from_entity(entity_id: str) -> str:
    """Extract platform domain from entity_id."""
    domain = entity_id.split(".", 1)[0]
    return domain if domain in SUPPORTED_DOMAINS else "binary_sensor"


def normalize_ota_duration(val: Any) -> int:
    """Clamp OTA duration to valid range (10 - 90 min)."""
    try:
        minutes = int(val)
        return max(MIN_OTA_DURATION, min(MAX_OTA_DURATION, minutes))
    except (ValueError, TypeError):
        return DEFAULT_OTA_DURATION


def normalize_ping_interval(val: Any) -> int:
    """Clamp ping interval to valid range (1 - 60 s)."""
    try:
        secs = int(val)
        return max(MIN_PING_INTERVAL, min(MAX_PING_INTERVAL, secs))
    except (ValueError, TypeError):
        return DEFAULT_PING_INTERVAL


def get_rules_from_entry(entry: ConfigEntry) -> list[dict[str, Any]]:
    """Retrieve normalized list of KeepActive rules from a config entry.

    Ensures 100% backward compatibility with v1.0.0 and v1.1.0 formats.
    """
    rules = entry.options.get(CONF_RULES)
    if rules is None:
        rules = entry.data.get(CONF_RULES)

    if rules is not None:
        normalized: list[dict[str, Any]] = []
        for r in rules:
            rule_copy = dict(r)
            if not rule_copy.get(CONF_RULE_ID):
                rule_copy[CONF_RULE_ID] = rule_copy.get(CONF_SOURCE_ENTITY, "")
            # Ensure OTA fields exist
            rule_copy[CONF_OTA_DURATION] = normalize_ota_duration(
                rule_copy.get(CONF_OTA_DURATION, DEFAULT_OTA_DURATION)
            )
            rule_copy[CONF_PING_INTERVAL] = normalize_ping_interval(
                rule_copy.get(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL)
            )
            rule_copy[CONF_PING_METHOD] = rule_copy.get(
                CONF_PING_METHOD, DEFAULT_PING_METHOD
            )
            rule_copy[CONF_AUTO_OTA_TRIGGER] = bool(
                rule_copy.get(CONF_AUTO_OTA_TRIGGER, DEFAULT_AUTO_OTA_TRIGGER)
            )
            normalized.append(rule_copy)
        return normalized

    # Backward compatibility with v1.0.0 single entity format
    if CONF_SOURCE_ENTITY in entry.data:
        source = entry.data[CONF_SOURCE_ENTITY]
        return [
            {
                CONF_RULE_ID: source,
                CONF_SOURCE_ENTITY: source,
                CONF_NAME: entry.data.get(CONF_NAME, ""),
                CONF_HOLD_DURATION: entry.options.get(
                    CONF_HOLD_DURATION,
                    entry.data.get(CONF_HOLD_DURATION, DEFAULT_HOLD_DURATION),
                ),
                CONF_GRACE_PERIOD: entry.options.get(
                    CONF_GRACE_PERIOD,
                    entry.data.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD),
                ),
                CONF_OPTIMISTIC: entry.options.get(
                    CONF_OPTIMISTIC,
                    entry.data.get(CONF_OPTIMISTIC, DEFAULT_OPTIMISTIC),
                ),
                CONF_OTA_DURATION: normalize_ota_duration(
                    entry.options.get(CONF_OTA_DURATION, DEFAULT_OTA_DURATION)
                ),
                CONF_PING_INTERVAL: normalize_ping_interval(
                    entry.options.get(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL)
                ),
                CONF_PING_METHOD: entry.options.get(
                    CONF_PING_METHOD, DEFAULT_PING_METHOD
                ),
                CONF_AUTO_OTA_TRIGGER: bool(
                    entry.options.get(
                        CONF_AUTO_OTA_TRIGGER, DEFAULT_AUTO_OTA_TRIGGER
                    )
                ),
            }
        ]
    return []
