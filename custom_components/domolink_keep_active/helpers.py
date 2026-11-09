"""Helper utilities for DomoLink KeepActive."""
from __future__ import annotations

from typing import Any
from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_GRACE_PERIOD,
    CONF_HOLD_DURATION,
    CONF_NAME,
    CONF_OPTIMISTIC,
    CONF_RULES,
    CONF_RULE_ID,
    CONF_SOURCE_ENTITY,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_HOLD_DURATION,
    DEFAULT_OPTIMISTIC,
    SUPPORTED_DOMAINS,
)


def get_platform_from_entity(entity_id: str) -> str:
    """Extract platform domain from entity_id."""
    domain = entity_id.split(".", 1)[0]
    return domain if domain in SUPPORTED_DOMAINS else "binary_sensor"


def get_rules_from_entry(entry: ConfigEntry) -> list[dict[str, Any]]:
    """Retrieve normalized list of KeepActive rules from a config entry.

    Ensures 100% backward compatibility with v1.0.0 format.
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
            }
        ]
    return []
