"""The DomoLink KeepActive integration."""
from __future__ import annotations

import logging
import os
from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import DomolinkKeepActiveApiView
from .const import (
    DOMAIN,
    FRONTEND_FILE_NAME,
    FRONTEND_URL_PATH,
    PANEL_ICON,
    PANEL_NAME,
    PANEL_TITLE,
    PANEL_URL_PATH,
    VERSION,
)
from .helpers import get_rules_from_entry
from .ota_manager import OtaKeepAwakeManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
]


def _get_all_rules_across_entries(hass: HomeAssistant) -> list[dict]:
    """Retrieve all rules configured across all DomoLink KeepActive entries."""
    all_rules = []
    if DOMAIN in hass.data:
        for entry_id, entry_data in hass.data[DOMAIN].items():
            if isinstance(entry_data, dict) and "rules" in entry_data:
                all_rules.extend(entry_data["rules"])
    return all_rules


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DomoLink KeepActive from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # 1. Initialize OTA Manager singleton
    if "ota_manager" not in hass.data[DOMAIN]:
        ota_manager = OtaKeepAwakeManager(hass)
        ota_manager.set_rules_provider(lambda: _get_all_rules_across_entries(hass))
        ota_manager.async_setup_auto_ota_listener()
        hass.data[DOMAIN]["ota_manager"] = ota_manager

        # Register REST API View
        if hasattr(hass, "http"):
            hass.http.register_view(DomolinkKeepActiveApiView(hass, ota_manager))

    rules = get_rules_from_entry(entry)
    hass.data[DOMAIN][entry.entry_id] = {
        "rules": rules,
    }

    # 2. Register frontend static path and panel in left sidebar
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    if hasattr(hass, "http"):
        if hasattr(hass.http, "async_register_static_paths"):
            from homeassistant.components.http import StaticPathConfig

            await hass.http.async_register_static_paths(
                [StaticPathConfig(FRONTEND_URL_PATH, frontend_dir, cache_headers=False)]
            )
        elif hasattr(hass.http, "register_static_path"):
            try:
                hass.http.register_static_path(FRONTEND_URL_PATH, frontend_dir, cache_headers=False)
            except Exception as err:
                _LOGGER.debug("register_static_path: %s", err)

    _async_register_panel(hass)

    # 3. Register listener for options updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # 4. Forward entry setups to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _async_register_panel(hass: HomeAssistant) -> None:
    """Register custom left sidebar panel with cache-busting."""
    import time
    panel_url = f"{FRONTEND_URL_PATH}/{FRONTEND_FILE_NAME}?v={VERSION}_{int(time.time())}"
    try:
        if hasattr(frontend, "add_extra_js_url"):
            frontend.add_extra_js_url(hass, panel_url)

        frontend.async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            frontend_url_path=PANEL_URL_PATH,
            config={
                "_panel_custom": {
                    "name": PANEL_NAME,
                    "module_url": panel_url,
                }
            },
            require_admin=False,
            update=True,
        )
        _LOGGER.debug("DomoLink KeepActive: Panneau latéral enregistré avec succès.")
    except Exception as err:
        _LOGGER.debug("Panneau latéral DomoLink KeepActive déjà enregistré ou avertissement: %s", err)


def _async_remove_panel(hass: HomeAssistant) -> None:
    """Remove custom left sidebar panel."""
    try:
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
    except Exception:
        pass


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # If no more entries, clean up manager and remove panel
        remaining_entries = [k for k in hass.data[DOMAIN] if k != "ota_manager"]
        if not remaining_entries:
            ota_manager: OtaKeepAwakeManager = hass.data[DOMAIN].pop("ota_manager", None)
            if ota_manager:
                ota_manager.async_stop_all()
            _async_remove_panel(hass)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are modified."""
    await hass.config_entries.async_reload(entry.entry_id)
