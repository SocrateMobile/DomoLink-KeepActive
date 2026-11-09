"""OTA Keep-Awake Manager for DomoLink KeepActive.

Keeps battery-powered Zigbee / wireless devices awake during firmware OTA updates
by sending periodic read/get/poll requests so the device does not drop into deep sleep.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .const import (
    CONF_AUTO_OTA_TRIGGER,
    CONF_OTA_DURATION,
    CONF_PING_INTERVAL,
    CONF_PING_METHOD,
    CONF_RULE_ID,
    CONF_SOURCE_ENTITY,
    DEFAULT_AUTO_OTA_TRIGGER,
    DEFAULT_OTA_DURATION,
    DEFAULT_PING_INTERVAL,
    DEFAULT_PING_METHOD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class OtaKeepAwakeManager:
    """Manages active Keep-Awake sessions for devices undergoing OTA firmware updates."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the OTA manager."""
        self.hass = hass
        self._sessions: dict[str, dict[str, Any]] = {}
        self._logs: list[dict[str, Any]] = []
        self._update_listener: CALLBACK_TYPE | None = None
        self._rules_provider: Callable[[], list[dict[str, Any]]] | None = None

    def set_rules_provider(self, provider: Callable[[], list[dict[str, Any]]]) -> None:
        """Set callback to query currently configured rules."""
        self._rules_provider = provider

    def _get_all_rules(self) -> list[dict[str, Any]]:
        """Return all active rules across entries."""
        if self._rules_provider:
            return self._rules_provider()
        return []

    def _find_rule(self, rule_id: str) -> dict[str, Any] | None:
        """Find a rule by its rule_id or source_entity."""
        for r in self._get_all_rules():
            if r.get(CONF_RULE_ID) == rule_id or r.get(CONF_SOURCE_ENTITY) == rule_id:
                return r
        return None

    def _add_log(self, rule_id: str, message: str, level: str = "info") -> None:
        """Add an entry to the rolling OTA log (max 100 entries)."""
        log_entry = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "rule_id": rule_id,
            "message": message,
            "level": level,
        }
        self._logs.insert(0, log_entry)
        if len(self._logs) > 100:
            self._logs.pop()
        _LOGGER.debug("[OTA Keep-Awake %s] %s", rule_id, message)

    def get_logs(self) -> list[dict[str, Any]]:
        """Return the recent activity log."""
        return list(self._logs)

    def get_session_state(self, rule_id: str) -> dict[str, Any]:
        """Return the current session state for a rule."""
        session = self._sessions.get(rule_id)
        if not session or not session.get("active", False):
            return {
                "active": False,
                "remaining_seconds": 0,
                "elapsed_seconds": 0,
                "duration_minutes": DEFAULT_OTA_DURATION,
                "ping_interval": DEFAULT_PING_INTERVAL,
                "ping_count": 0,
                "last_ping_at": None,
                "last_ping_status": None,
                "method_used": DEFAULT_PING_METHOD,
            }

        now = time.time()
        end_time = session.get("end_time", now)
        start_time = session.get("start_time", now)
        remaining = max(0, int(end_time - now))
        elapsed = max(0, int(now - start_time))

        return {
            "active": True,
            "remaining_seconds": remaining,
            "elapsed_seconds": elapsed,
            "duration_minutes": session.get("duration_minutes", DEFAULT_OTA_DURATION),
            "ping_interval": session.get("ping_interval", DEFAULT_PING_INTERVAL),
            "ping_count": session.get("ping_count", 0),
            "last_ping_at": session.get("last_ping_at"),
            "last_ping_status": session.get("last_ping_status", "success"),
            "method_used": session.get("method_used", DEFAULT_PING_METHOD),
        }

    def get_all_sessions(self) -> dict[str, dict[str, Any]]:
        """Return states of all sessions."""
        return {r_id: self.get_session_state(r_id) for r_id in self._sessions}

    async def async_start_ota(
        self,
        rule_id: str,
        duration_minutes: int | None = None,
        ping_interval: int | None = None,
        ping_method: str | None = None,
    ) -> dict[str, Any]:
        """Start an active Keep-Awake session for a device."""
        rule = self._find_rule(rule_id)
        source_entity = rule.get(CONF_SOURCE_ENTITY, rule_id) if rule else rule_id

        # Cancel any running timer for this rule
        self._cancel_session_timer(rule_id)

        # Resolve parameters
        dur = duration_minutes or (rule.get(CONF_OTA_DURATION) if rule else DEFAULT_OTA_DURATION)
        interval = ping_interval or (rule.get(CONF_PING_INTERVAL) if rule else DEFAULT_PING_INTERVAL)
        method = ping_method or (rule.get(CONF_PING_METHOD) if rule else DEFAULT_PING_METHOD)

        now = time.time()
        end_time = now + (dur * 60)

        session = {
            "rule_id": rule_id,
            "source_entity": source_entity,
            "active": True,
            "start_time": now,
            "end_time": end_time,
            "duration_minutes": dur,
            "ping_interval": interval,
            "ping_count": 0,
            "last_ping_at": None,
            "last_ping_status": "pending",
            "method_used": method,
            "timer_cancel": None,
        }
        self._sessions[rule_id] = session

        self._add_log(
            rule_id,
            f"🚀 Mode OTA Keep-Awake activé pour {dur} min (Pings toutes les {interval}s via {method})",
            "success",
        )

        # Execute immediate first ping
        await self.async_send_ping(rule_id)

        # Schedule subsequent periodic pings
        self._schedule_next_ping(rule_id)

        return self.get_session_state(rule_id)

    def _schedule_next_ping(self, rule_id: str) -> None:
        """Schedule the next ping callback."""
        session = self._sessions.get(rule_id)
        if not session or not session.get("active"):
            return

        interval = session.get("ping_interval", DEFAULT_PING_INTERVAL)
        session["timer_cancel"] = async_call_later(
            self.hass,
            interval,
            lambda _now: self.hass.async_create_task(self._async_timer_step(rule_id)),
        )

    async def _async_timer_step(self, rule_id: str) -> None:
        """Step execution called by async_call_later."""
        session = self._sessions.get(rule_id)
        if not session or not session.get("active"):
            return

        now = time.time()
        if now >= session.get("end_time", now):
            self.async_stop_ota(rule_id, reason="durée expirée")
            return

        await self.async_send_ping(rule_id)
        self._schedule_next_ping(rule_id)

    def async_stop_ota(self, rule_id: str, reason: str = "manuel") -> dict[str, Any]:
        """Stop an active Keep-Awake session."""
        session = self._sessions.get(rule_id)
        if session:
            self._cancel_session_timer(rule_id)
            session["active"] = False
            count = session.get("ping_count", 0)
            self._add_log(
                rule_id,
                f"🛑 Mode OTA Keep-Awake désactivé ({reason}). Total pings envoyés: {count}",
                "info",
            )
        return self.get_session_state(rule_id)

    def _cancel_session_timer(self, rule_id: str) -> None:
        """Cancel the active timer for a session."""
        session = self._sessions.get(rule_id)
        if session and session.get("timer_cancel"):
            try:
                session["timer_cancel"]()
            except Exception:
                pass
            session["timer_cancel"] = None

    async def async_send_ping(self, rule_id: str) -> bool:
        """Send a single Keep-Awake wakeup request to the device."""
        session = self._sessions.get(rule_id)
        source_entity = (
            session.get("source_entity")
            if session
            else (self._find_rule(rule_id) or {}).get(CONF_SOURCE_ENTITY, rule_id)
        )
        method = session.get("method_used", DEFAULT_PING_METHOD) if session else DEFAULT_PING_METHOD

        success = False
        try:
            # 1. Zigbee2MQTT MQTT get ping (if method is z2m_get or auto with MQTT)
            if method in ("z2m_get", "auto") and self.hass.services.has_service("mqtt", "publish"):
                z2m_name = self._resolve_z2m_device_name(source_entity)
                if z2m_name:
                    await self.hass.services.async_call(
                        "mqtt",
                        "publish",
                        {
                            "topic": f"zigbee2mqtt/{z2m_name}/get",
                            "payload": '{"state": ""}',
                        },
                        blocking=False,
                    )
                    success = True

            # 2. Home Assistant update_entity ping (universal fallback / poll)
            if self.hass.services.has_service("homeassistant", "update_entity"):
                await self.hass.services.async_call(
                    "homeassistant",
                    "update_entity",
                    {ATTR_ENTITY_ID: source_entity},
                    blocking=False,
                )
                success = True

            if session:
                session["ping_count"] = session.get("ping_count", 0) + 1
                session["last_ping_at"] = time.time()
                session["last_ping_status"] = "success" if success else "failed"

            self._add_log(
                rule_id,
                f"⚡ Ping #{session.get('ping_count', 1) if session else 1} envoyé à {source_entity} ({method})",
                "debug",
            )
            return success

        except Exception as err:
            _LOGGER.warning("Erreur lors du ping OTA sur %s: %s", source_entity, err)
            if session:
                session["last_ping_status"] = "failed"
            self._add_log(rule_id, f"⚠️ Échec du ping vers {source_entity}: {err}", "warning")
            return False

    def _resolve_z2m_device_name(self, entity_id: str) -> str | None:
        """Resolve Zigbee2MQTT friendly name from Home Assistant registries."""
        ent_reg = er.async_get(self.hass)
        dev_reg = dr.async_get(self.hass)

        entry = ent_reg.async_get(entity_id)
        if entry and entry.device_id:
            device = dev_reg.async_get(entry.device_id)
            if device:
                # Zigbee2MQTT devices typically have an identifier (DOMAIN, "zigbee2mqtt_xxx")
                for domain, identifier in device.identifiers:
                    if domain == "mqtt" or "zigbee2mqtt" in identifier:
                        return identifier.replace("zigbee2mqtt_", "")
                if device.name:
                    return device.name

        # Fallback heuristic: clean object_id
        return entity_id.split(".", 1)[-1]

    def get_device_enrichment(self, source_entity_id: str) -> dict[str, Any]:
        """Retrieve battery, signal (LQI), and update.* entity for a device."""
        enrichment: dict[str, Any] = {
            "battery_level": None,
            "linkquality": None,
            "update_entity_id": None,
            "update_available": False,
            "installed_version": None,
            "latest_version": None,
            "in_progress": False,
        }

        try:
            ent_reg = er.async_get(self.hass)
            dev_reg = dr.async_get(self.hass)

            entry = ent_reg.async_get(source_entity_id)
            if not entry or not entry.device_id:
                return enrichment

            device_id = entry.device_id

            # Scan entities on the same device
            for e_id, e_entry in ent_reg.entities.items():
                if e_entry.device_id != device_id:
                    continue

                state = self.hass.states.get(e_id)
                if not state:
                    continue

                # Battery
                if (
                    e_entry.domain == "sensor"
                    and (
                        state.attributes.get("device_class") == "battery"
                        or e_id.endswith("_battery")
                    )
                ):
                    try:
                        enrichment["battery_level"] = int(float(state.state))
                    except (ValueError, TypeError):
                        pass

                # Signal strength / Linkquality
                if (
                    e_entry.domain == "sensor"
                    and (
                        state.attributes.get("device_class") == "signal_strength"
                        or "linkquality" in e_id
                        or "lqi" in e_id
                    )
                ):
                    try:
                        enrichment["linkquality"] = int(float(state.state))
                    except (ValueError, TypeError):
                        pass

                # Update entity
                if e_entry.domain == "update":
                    enrichment["update_entity_id"] = e_id
                    enrichment["installed_version"] = state.attributes.get("installed_version")
                    enrichment["latest_version"] = state.attributes.get("latest_version")
                    enrichment["in_progress"] = bool(state.attributes.get("in_progress", False))
                    enrichment["update_available"] = state.state == "on"

        except Exception as exc:
            _LOGGER.debug("Erreur enrichment pour %s: %s", source_entity_id, exc)

        return enrichment

    def async_setup_auto_ota_listener(self) -> None:
        """Listen to state change events from update.* entities to auto-trigger Keep-Awake."""
        if self._update_listener:
            return

        @callback
        def _handle_update_event(event: Event) -> None:
            entity_id = event.data.get("entity_id", "")
            if not entity_id.startswith("update."):
                return

            new_state = event.data.get("new_state")
            if not new_state:
                return

            in_progress = bool(new_state.attributes.get("in_progress", False))
            old_state = event.data.get("old_state")
            old_in_progress = bool(old_state.attributes.get("in_progress", False)) if old_state else False

            # Check if this update entity belongs to one of our rules
            for rule in self._get_all_rules():
                if not rule.get(CONF_AUTO_OTA_TRIGGER, DEFAULT_AUTO_OTA_TRIGGER):
                    continue

                source = rule.get(CONF_SOURCE_ENTITY, "")
                enrichment = self.get_device_enrichment(source)
                if enrichment.get("update_entity_id") == entity_id:
                    rule_id = rule.get(CONF_RULE_ID, source)
                    # Start OTA keep-awake on update launch
                    if in_progress and not old_in_progress:
                        self._add_log(
                            rule_id,
                            f"🔔 Détection automatique de mise à jour firmware en cours sur {entity_id} !",
                            "info",
                        )
                        self.hass.async_create_task(self.async_start_ota(rule_id))
                    # Stop OTA keep-awake on update finish
                    elif not in_progress and old_in_progress:
                        self._add_log(
                            rule_id,
                            f"✅ Mise à jour firmware terminée sur {entity_id}.",
                            "success",
                        )
                        self.async_stop_ota(rule_id, reason="mise à jour terminée")

        self._update_listener = async_track_state_change_event(
            self.hass,
            [],
            _handle_update_event,
        )

    def async_stop_all(self) -> None:
        """Cancel all active sessions and listeners on unload."""
        for rule_id in list(self._sessions.keys()):
            self._cancel_session_timer(rule_id)
        self._sessions.clear()

        if self._update_listener:
            self._update_listener()
            self._update_listener = None
