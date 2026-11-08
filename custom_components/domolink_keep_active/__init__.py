"""The DomoLink KeepActive integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SOURCE_ENTITY, DOMAIN, SUPPORTED_DOMAINS

_LOGGER = logging.getLogger(__name__)


def _get_platform_for_entry(entry: ConfigEntry) -> Platform:
    """Determine the platform based on the source entity domain."""
    source_entity: str = entry.data[CONF_SOURCE_ENTITY]
    domain = source_entity.split(".", 1)[0]
    if domain == "binary_sensor":
        return Platform.BINARY_SENSOR
    if domain == "sensor":
        return Platform.SENSOR
    if domain == "switch":
        return Platform.SWITCH
    return Platform.BINARY_SENSOR


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DomoLink KeepActive from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    platform = _get_platform_for_entry(entry)
    hass.data[DOMAIN][entry.entry_id] = {
        "platform": platform,
    }

    # Register listener for options flow updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, [platform])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if entry_data:
        platform = entry_data["platform"]
        unload_ok = await hass.config_entries.async_unload_platforms(entry, [platform])
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id)
        return unload_ok
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are modified."""
    await hass.config_entries.async_reload(entry.entry_id)
