"""REST API views for the DomoLink KeepActive panel."""
from __future__ import annotations

import logging
from typing import Any
from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import entity_registry as er

from .const import (
    AUTO_EXTEND_MINUTES,
    CONF_AUTO_OTA_TRIGGER,
    CONF_GRACE_PERIOD,
    CONF_HOLD_DURATION,
    CONF_NAME,
    CONF_ON_OTA_FAILURE,
    CONF_ON_OTA_TIMEOUT,
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
    DEFAULT_ON_OTA_FAILURE,
    DEFAULT_ON_OTA_TIMEOUT,
    DEFAULT_OPTIMISTIC,
    DEFAULT_OTA_DURATION,
    DEFAULT_PING_INTERVAL,
    DEFAULT_PING_METHOD,
    DOMAIN,
    SUPPORTED_DOMAINS,
)
from .helpers import get_platform_from_entity, get_rules_from_entry, normalize_ota_duration, normalize_ping_interval
from .ota_manager import OtaKeepAwakeManager

_LOGGER = logging.getLogger(__name__)


class DomolinkKeepActiveApiView(HomeAssistantView):
    """API view handling actions for the DomoLink KeepActive frontend panel."""

    url = "/api/domolink_keep_active/{action}"
    name = "api:domolink_keep_active"
    requires_auth = True

    def __init__(self, hass: HomeAssistant, ota_manager: OtaKeepAwakeManager) -> None:
        """Initialize the API view."""
        self.hass = hass
        self.ota_manager = ota_manager

    def _get_active_entry(self):
        """Return the first active DomoLink KeepActive config entry."""
        entries = self.hass.config_entries.async_entries(DOMAIN)
        return entries[0] if entries else None

    async def get(self, request: web.Request, action: str) -> web.Response:
        """Handle GET requests from the panel."""
        user = request.get("hass_user")
        if not user:
            raise Unauthorized()

        if action in ("data", "state"):
            entry = self._get_active_entry()
            raw_rules = get_rules_from_entry(entry) if entry else []

            enriched_rules = []
            for r in raw_rules:
                rule_id = r.get(CONF_RULE_ID, r.get(CONF_SOURCE_ENTITY, ""))
                source = r.get(CONF_SOURCE_ENTITY, "")
                enrichment = self.ota_manager.get_device_enrichment(source)
                session = self.ota_manager.get_session_state(rule_id)

                # Get live state of the source entity in HA
                ha_state = self.hass.states.get(source)

                enriched_rules.append(
                    {
                        **r,
                        "source_state": ha_state.state if ha_state else "unavailable",
                        "source_attributes": dict(ha_state.attributes) if ha_state else {},
                        "platform": get_platform_from_entity(source),
                        "device_enrichment": enrichment,
                        "ota_session": session,
                    }
                )

            # Available candidates for adding new entities
            available_entities = []
            for s in self.hass.states.async_all():
                domain = s.entity_id.split(".", 1)[0]
                if domain in SUPPORTED_DOMAINS:
                    name = s.attributes.get("friendly_name") or s.entity_id
                    available_entities.append(
                        {
                            "entity_id": s.entity_id,
                            "name": name,
                            "domain": domain,
                            "state": s.state,
                        }
                    )
            available_entities.sort(key=lambda x: x["name"].lower())

            return self.json(
                {
                    "status": "ok",
                    "rules": enriched_rules,
                    "logs": self.ota_manager.get_logs(),
                    "available_entities": available_entities,
                }
            )

        return self.json({"error": "Action inconnue"}, status=400)

    async def post(self, request: web.Request, action: str) -> web.Response:
        """Handle POST command actions from the panel."""
        user = request.get("hass_user")
        if not user:
            raise Unauthorized()

        try:
            body: dict[str, Any] = await request.json()
        except Exception:
            body = {}

        entry = self._get_active_entry()
        if not entry:
            return self.json({"error": "Aucune entrée de configuration KeepActive active"}, status=404)

        rules = get_rules_from_entry(entry)

        # 1. TOGGLE OTA
        if action == "toggle_ota":
            rule_id = body.get("rule_id")
            if not rule_id:
                return self.json({"error": "rule_id manquant"}, status=400)

            activate = body.get("active")
            duration = body.get("duration")
            interval = body.get("interval")

            if activate is False or (activate is None and self.ota_manager.get_session_state(rule_id).get("active")):
                session = self.ota_manager.async_stop_ota(rule_id, reason="bouton panel")
            else:
                session = await self.ota_manager.async_start_ota(
                    rule_id,
                    duration_minutes=duration,
                    ping_interval=interval,
                )
            return self.json({"status": "ok", "session": session})

        # 2. UPDATE OTA PARAMS
        if action == "update_ota_params":
            rule_id = body.get("rule_id")
            if not rule_id:
                return self.json({"error": "rule_id manquant"}, status=400)

            dur = normalize_ota_duration(body.get("duration", DEFAULT_OTA_DURATION))
            interval = normalize_ping_interval(body.get("interval", DEFAULT_PING_INTERVAL))
            method = body.get("ping_method", DEFAULT_PING_METHOD)
            auto_trigger = bool(body.get("auto_ota_trigger", DEFAULT_AUTO_OTA_TRIGGER))

            for r in rules:
                if r.get(CONF_RULE_ID) == rule_id:
                    r[CONF_OTA_DURATION] = dur
                    r[CONF_PING_INTERVAL] = interval
                    r[CONF_PING_METHOD] = method
                    r[CONF_AUTO_OTA_TRIGGER] = auto_trigger
                    break

            new_options = {**entry.options, CONF_RULES: rules}
            self.hass.config_entries.async_update_entry(entry, options=new_options)

            # Update live session if running
            session = self.ota_manager.get_session_state(rule_id)
            if session.get("active"):
                await self.ota_manager.async_start_ota(
                    rule_id,
                    duration_minutes=dur,
                    ping_interval=interval,
                    ping_method=method,
                )

            return self.json({"status": "ok", "rule_id": rule_id, "duration": dur, "interval": interval})

        # 3. PING NOW
        if action == "ping_now":
            rule_id = body.get("rule_id")
            if not rule_id:
                return self.json({"error": "rule_id manquant"}, status=400)

            success = await self.ota_manager.async_send_ping(rule_id)
            return self.json(
                {
                    "status": "ok" if success else "failed",
                    "session": self.ota_manager.get_session_state(rule_id),
                }
            )

        # 3b. EXTEND OTA SESSION
        if action == "extend_ota":
            rule_id = body.get("rule_id")
            if not rule_id:
                return self.json({"error": "rule_id manquant"}, status=400)
            minutes = int(body.get("minutes", AUTO_EXTEND_MINUTES))
            session = self.ota_manager.async_extend_session(rule_id, minutes)
            return self.json({"status": "ok", "session": session})

        # 3c. BURST OTA SESSION (RAPID PINGS 15s)
        if action == "burst_ota":
            rule_id = body.get("rule_id")
            if not rule_id:
                return self.json({"error": "rule_id manquant"}, status=400)
            seconds = int(body.get("seconds", 15))
            session = await self.ota_manager.async_start_burst(rule_id, duration_seconds=seconds)
            return self.json({"status": "ok", "session": session})

        # 3d. CLEAR LOGS
        if action == "clear_logs":
            self.ota_manager.clear_logs()
            return self.json({"status": "ok", "logs": self.ota_manager.get_logs()})

        # 4. SAVE RULE (ADD OR MODIFY)
        if action == "save_rule":
            source_entity = body.get("source_entity")
            if not source_entity:
                return self.json({"error": "source_entity requis"}, status=400)

            rule_id = body.get("rule_id") or source_entity
            name = body.get("name", "").strip()
            hold = int(body.get("hold_duration", DEFAULT_HOLD_DURATION))
            grace = int(body.get("grace_period", DEFAULT_GRACE_PERIOD))
            optimistic = bool(body.get("optimistic", DEFAULT_OPTIMISTIC))
            ota_dur = normalize_ota_duration(body.get("ota_duration", DEFAULT_OTA_DURATION))
            ping_int = normalize_ping_interval(body.get("ping_interval", DEFAULT_PING_INTERVAL))
            ping_meth = body.get("ping_method", DEFAULT_PING_METHOD)
            auto_ota = bool(body.get("auto_ota_trigger", DEFAULT_AUTO_OTA_TRIGGER))
            on_failure = body.get("on_ota_failure", DEFAULT_ON_OTA_FAILURE)
            on_timeout = body.get("on_ota_timeout", DEFAULT_ON_OTA_TIMEOUT)

            updated = False
            for i, r in enumerate(rules):
                if r.get(CONF_RULE_ID) == rule_id or r.get(CONF_SOURCE_ENTITY) == source_entity:
                    rules[i] = {
                        CONF_RULE_ID: rule_id,
                        CONF_SOURCE_ENTITY: source_entity,
                        CONF_NAME: name,
                        CONF_HOLD_DURATION: hold,
                        CONF_GRACE_PERIOD: grace,
                        CONF_OPTIMISTIC: optimistic,
                        CONF_OTA_DURATION: ota_dur,
                        CONF_PING_INTERVAL: ping_int,
                        CONF_PING_METHOD: ping_meth,
                        CONF_AUTO_OTA_TRIGGER: auto_ota,
                        CONF_ON_OTA_FAILURE: on_failure,
                        CONF_ON_OTA_TIMEOUT: on_timeout,
                    }
                    updated = True
                    break

            if not updated:
                rules.append(
                    {
                        CONF_RULE_ID: rule_id,
                        CONF_SOURCE_ENTITY: source_entity,
                        CONF_NAME: name,
                        CONF_HOLD_DURATION: hold,
                        CONF_GRACE_PERIOD: grace,
                        CONF_OPTIMISTIC: optimistic,
                        CONF_OTA_DURATION: ota_dur,
                        CONF_PING_INTERVAL: ping_int,
                        CONF_PING_METHOD: ping_meth,
                        CONF_AUTO_OTA_TRIGGER: auto_ota,
                        CONF_ON_OTA_FAILURE: on_failure,
                        CONF_ON_OTA_TIMEOUT: on_timeout,
                    }
                )

            new_options = {**entry.options, CONF_RULES: rules}
            self.hass.config_entries.async_update_entry(entry, options=new_options)
            await self.hass.config_entries.async_reload(entry.entry_id)

            return self.json({"status": "ok", "rule_id": rule_id, "rules_count": len(rules)})

        # 5. DELETE RULE
        if action == "delete_rule":
            rule_id = body.get("rule_id")
            if not rule_id:
                return self.json({"error": "rule_id requis"}, status=400)

            # Stop OTA if running
            self.ota_manager.async_stop_ota(rule_id, reason="règle supprimée")

            # Remove from list
            updated_rules = [r for r in rules if r.get(CONF_RULE_ID) != rule_id and r.get(CONF_SOURCE_ENTITY) != rule_id]

            # Clean registry
            try:
                ent_reg = er.async_get(self.hass)
                unique_id = f"{DOMAIN}_{entry.entry_id}_{rule_id}"
                platform = get_platform_from_entity(rule_id)
                e_id = ent_reg.async_get_entity_id(platform, DOMAIN, unique_id)
                if e_id:
                    ent_reg.async_remove(e_id)
            except Exception as exc:
                _LOGGER.debug("Erreur nettoyage registre: %s", exc)

            new_options = {**entry.options, CONF_RULES: updated_rules}
            self.hass.config_entries.async_update_entry(entry, options=new_options)
            await self.hass.config_entries.async_reload(entry.entry_id)

            return self.json({"status": "ok", "deleted": rule_id, "rules_count": len(updated_rules)})

        # 6. START OTA UPDATE & KEEP-AWAKE
        if action == "start_ota_update":
            rule_id = body.get("rule_id")
            update_entity_id = body.get("update_entity_id")
            if not rule_id or not update_entity_id:
                return self.json({"error": "rule_id et update_entity_id requis"}, status=400)

            # Start keep-awake & launch initial burst
            session = await self.ota_manager.async_start_ota(rule_id)
            await self.ota_manager.async_start_burst(rule_id, duration_seconds=15)

            # Trigger update.install safely only if not already in progress
            update_state = self.hass.states.get(update_entity_id)
            is_in_progress = bool(update_state and update_state.attributes.get("in_progress"))
            if not is_in_progress and self.hass.services.has_service("update", "install"):
                try:
                    await self.hass.services.async_call(
                        "update",
                        "install",
                        {"entity_id": update_entity_id},
                        blocking=False,
                    )
                except Exception as err:
                    _LOGGER.warning("Impossible de lancer update.install sur %s: %s", update_entity_id, err)

            return self.json({"status": "ok", "session": session, "update_entity_id": update_entity_id})

        return self.json({"error": "Action inconnue"}, status=400)
