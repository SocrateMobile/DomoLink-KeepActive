"""Config flow for DomoLink KeepActive integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    ACTION_ADD,
    ACTION_DELETE,
    ACTION_EDIT,
    ACTION_VIEW,
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
    MAX_OTA_DURATION,
    MAX_PING_INTERVAL,
    MIN_OTA_DURATION,
    MIN_PING_INTERVAL,
    OTA_FAILURE_KEEP_ALIVE,
    OTA_FAILURE_RETRY,
    OTA_FAILURE_STOP,
    OTA_TIMEOUT_EXTEND,
    OTA_TIMEOUT_STOP,
    PING_METHODS,
    SUPPORTED_DOMAINS,
)
from .helpers import (
    get_platform_from_entity,
    get_rules_from_entry,
    normalize_ota_duration,
    normalize_ping_interval,
)

_LOGGER = logging.getLogger(__name__)


class DomoLinkKeepActiveConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DomoLink KeepActive."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            source_entity = user_input[CONF_SOURCE_ENTITY]
            domain = source_entity.split(".", 1)[0]

            if domain not in SUPPORTED_DOMAINS:
                errors["base"] = "unsupported_domain"
            else:
                await self.async_set_unique_id(f"{DOMAIN}_{source_entity}")
                self._abort_if_unique_id_configured()

                title = user_input.get(CONF_NAME) or f"KeepActive {source_entity}"
                rule = {
                    CONF_RULE_ID: source_entity,
                    CONF_SOURCE_ENTITY: source_entity,
                    CONF_NAME: user_input.get(CONF_NAME, "").strip(),
                    CONF_HOLD_DURATION: user_input.get(CONF_HOLD_DURATION, DEFAULT_HOLD_DURATION),
                    CONF_GRACE_PERIOD: user_input.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD),
                    CONF_OPTIMISTIC: user_input.get(CONF_OPTIMISTIC, DEFAULT_OPTIMISTIC),
                    CONF_OTA_DURATION: normalize_ota_duration(
                        user_input.get(CONF_OTA_DURATION, DEFAULT_OTA_DURATION)
                    ),
                    CONF_PING_INTERVAL: normalize_ping_interval(
                        user_input.get(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL)
                    ),
                    CONF_PING_METHOD: user_input.get(CONF_PING_METHOD, DEFAULT_PING_METHOD),
                    CONF_AUTO_OTA_TRIGGER: bool(
                        user_input.get(CONF_AUTO_OTA_TRIGGER, DEFAULT_AUTO_OTA_TRIGGER)
                    ),
                }
                entry_data = {
                    **user_input,
                    CONF_RULES: [rule],
                }
                return self.async_create_entry(title=title, data=entry_data)

        schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=SUPPORTED_DOMAINS)
                ),
                vol.Optional(CONF_NAME): selector.TextSelector(),
                vol.Optional(
                    CONF_HOLD_DURATION, default=DEFAULT_HOLD_DURATION
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_GRACE_PERIOD, default=DEFAULT_GRACE_PERIOD
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_OPTIMISTIC, default=DEFAULT_OPTIMISTIC
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_OTA_DURATION, default=DEFAULT_OTA_DURATION
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_OTA_DURATION,
                        max=MAX_OTA_DURATION,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="min",
                    )
                ),
                vol.Optional(
                    CONF_PING_INTERVAL, default=DEFAULT_PING_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_PING_INTERVAL,
                        max=MAX_PING_INTERVAL,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(
                    CONF_AUTO_OTA_TRIGGER, default=DEFAULT_AUTO_OTA_TRIGGER
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_ON_OTA_FAILURE, default=DEFAULT_ON_OTA_FAILURE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=OTA_FAILURE_KEEP_ALIVE, label="Maintenir actif pour relancer (Recommandé)"),
                            selector.SelectOptionDict(value=OTA_FAILURE_STOP, label="Arrêter immédiatement le défibrillateur"),
                            selector.SelectOptionDict(value=OTA_FAILURE_RETRY, label="Relancer automatiquement l'OTA (max 2 fois)"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_ON_OTA_TIMEOUT, default=DEFAULT_ON_OTA_TIMEOUT
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=OTA_TIMEOUT_EXTEND, label="Prolonger de +15 min si toujours en cours (Recommandé)"),
                            selector.SelectOptionDict(value=OTA_TIMEOUT_STOP, label="Arrêter strictement à l'échéance"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create options flow handler."""
        return DomoLinkKeepActiveOptionsFlowHandler(config_entry)


class DomoLinkKeepActiveOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for DomoLink KeepActive."""

    def __init__(self, config_entry: config_entries.ConfigEntry | None = None) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._selected_rule_id: str | None = None

    @property
    def config_entry(self) -> config_entries.ConfigEntry:
        """Return config entry, prioritizing HA base property with fallback."""
        try:
            entry = super().config_entry
            if entry is not None:
                return entry
        except (AttributeError, KeyError, Exception):
            pass
        return self._config_entry

    def _get_rules(self) -> list[dict[str, Any]]:
        """Return normalized list of rules."""
        return get_rules_from_entry(self.config_entry)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage main options menu."""
        rules = self._get_rules()

        if user_input is not None:
            choice = user_input.get("choice")
            if choice == ACTION_VIEW:
                return await self.async_step_view()
            if choice == ACTION_ADD:
                return await self.async_step_add()
            if choice == ACTION_EDIT:
                return await self.async_step_edit_select()
            if choice == ACTION_DELETE:
                return await self.async_step_delete()

        options = [
            selector.SelectOptionDict(value=ACTION_VIEW, label="🔍 Visualiser la configuration"),
            selector.SelectOptionDict(value=ACTION_ADD, label="➕ Ajouter une entité KeepActive"),
        ]
        if rules:
            options.append(
                selector.SelectOptionDict(value=ACTION_EDIT, label="✏️ Modifier une entité existante")
            )
            options.append(
                selector.SelectOptionDict(value=ACTION_DELETE, label="🗑️ Supprimer une entité")
            )

        schema = vol.Schema(
            {
                vol.Required("choice", default=ACTION_VIEW if rules else ACTION_ADD): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.LIST)
                )
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={"count": str(len(rules))},
        )

    async def async_step_view(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """View configured entities."""
        if user_input is not None:
            action = user_input.get("view_action", "menu")
            if action == "menu":
                return await self.async_step_init()
            return self.async_create_entry(title="", data=self.config_entry.options)

        rules = self._get_rules()
        summary_lines = []
        for idx, r in enumerate(rules, 1):
            source = r.get(CONF_SOURCE_ENTITY, "")
            name = r.get(CONF_NAME) or f"KeepActive {source}"
            hold = r.get(CONF_HOLD_DURATION, DEFAULT_HOLD_DURATION)
            grace = r.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD)
            optimistic = "Oui" if r.get(CONF_OPTIMISTIC, DEFAULT_OPTIMISTIC) else "Non"
            ota_dur = r.get(CONF_OTA_DURATION, DEFAULT_OTA_DURATION)
            ping_int = r.get(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL)
            domain = get_platform_from_entity(source)
            summary_lines.append(
                f"{idx}. {name} ({source}) | Type: {domain} | Maintien: {hold}s | Grâce: {grace}s | "
                f"OTA Max: {ota_dur}m | Ping: {ping_int}s | Optimiste: {optimistic}"
            )

        summary = "\n".join(summary_lines) if summary_lines else "Aucune entité configurée."

        schema = vol.Schema(
            {
                vol.Optional("view_action", default="menu"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="menu", label="Retour au menu principal"),
                            selector.SelectOptionDict(value="close", label="Fermer la configuration"),
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )

        return self.async_show_form(
            step_id="view",
            data_schema=schema,
            description_placeholders={"summary": summary, "count": str(len(rules))},
        )

    async def async_step_add(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new KeepActive entity."""
        errors: dict[str, str] = {}

        if user_input is not None:
            source_entity = user_input[CONF_SOURCE_ENTITY]
            domain = source_entity.split(".", 1)[0]

            if domain not in SUPPORTED_DOMAINS:
                errors["base"] = "unsupported_domain"
            else:
                rules = self._get_rules()
                if any(r.get(CONF_SOURCE_ENTITY) == source_entity for r in rules):
                    errors[CONF_SOURCE_ENTITY] = "already_configured"
                else:
                    new_rule = {
                        CONF_RULE_ID: source_entity,
                        CONF_SOURCE_ENTITY: source_entity,
                        CONF_NAME: user_input.get(CONF_NAME, "").strip(),
                        CONF_HOLD_DURATION: user_input.get(CONF_HOLD_DURATION, DEFAULT_HOLD_DURATION),
                        CONF_GRACE_PERIOD: user_input.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD),
                        CONF_OPTIMISTIC: user_input.get(CONF_OPTIMISTIC, DEFAULT_OPTIMISTIC),
                        CONF_OTA_DURATION: normalize_ota_duration(
                            user_input.get(CONF_OTA_DURATION, DEFAULT_OTA_DURATION)
                        ),
                        CONF_PING_INTERVAL: normalize_ping_interval(
                            user_input.get(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL)
                        ),
                        CONF_PING_METHOD: user_input.get(CONF_PING_METHOD, DEFAULT_PING_METHOD),
                        CONF_AUTO_OTA_TRIGGER: bool(
                            user_input.get(CONF_AUTO_OTA_TRIGGER, DEFAULT_AUTO_OTA_TRIGGER)
                        ),
                    }
                    rules.append(new_rule)
                    new_options = {**self.config_entry.options, CONF_RULES: rules}
                    return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=SUPPORTED_DOMAINS)
                ),
                vol.Optional(CONF_NAME): selector.TextSelector(),
                vol.Optional(
                    CONF_HOLD_DURATION, default=DEFAULT_HOLD_DURATION
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_GRACE_PERIOD, default=DEFAULT_GRACE_PERIOD
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_OPTIMISTIC, default=DEFAULT_OPTIMISTIC
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_OTA_DURATION, default=DEFAULT_OTA_DURATION
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_OTA_DURATION,
                        max=MAX_OTA_DURATION,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="min",
                    )
                ),
                vol.Optional(
                    CONF_PING_INTERVAL, default=DEFAULT_PING_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_PING_INTERVAL,
                        max=MAX_PING_INTERVAL,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(
                    CONF_PING_METHOD, default=DEFAULT_PING_METHOD
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="auto", label="Automatique (Recommandé)"),
                            selector.SelectOptionDict(value="z2m_get", label="Zigbee2MQTT (/get)"),
                            selector.SelectOptionDict(value="zha_ping", label="ZHA Ping"),
                            selector.SelectOptionDict(value="ha_update", label="Home Assistant Entity Update"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_AUTO_OTA_TRIGGER, default=DEFAULT_AUTO_OTA_TRIGGER
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_ON_OTA_FAILURE, default=DEFAULT_ON_OTA_FAILURE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=OTA_FAILURE_KEEP_ALIVE, label="Maintenir actif pour relancer (Recommandé)"),
                            selector.SelectOptionDict(value=OTA_FAILURE_STOP, label="Arrêter immédiatement le défibrillateur"),
                            selector.SelectOptionDict(value=OTA_FAILURE_RETRY, label="Relancer automatiquement l'OTA (max 2 fois)"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_ON_OTA_TIMEOUT, default=DEFAULT_ON_OTA_TIMEOUT
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=OTA_TIMEOUT_EXTEND, label="Prolonger de +15 min si toujours en cours (Recommandé)"),
                            selector.SelectOptionDict(value=OTA_TIMEOUT_STOP, label="Arrêter strictement à l'échéance"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="add", data_schema=schema, errors=errors)

    async def async_step_edit_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which entity to edit."""
        rules = self._get_rules()
        if not rules:
            return await self.async_step_init()

        if len(rules) == 1:
            self._selected_rule_id = rules[0][CONF_RULE_ID]
            return await self.async_step_edit()

        if user_input is not None:
            self._selected_rule_id = user_input.get("rule_to_edit")
            return await self.async_step_edit()

        options = [
            selector.SelectOptionDict(
                value=r[CONF_RULE_ID],
                label=f"{r.get(CONF_NAME) or r[CONF_SOURCE_ENTITY]} ({r[CONF_SOURCE_ENTITY]})",
            )
            for r in rules
        ]

        schema = vol.Schema(
            {
                vol.Required("rule_to_edit", default=rules[0][CONF_RULE_ID]): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.LIST)
                )
            }
        )

        return self.async_show_form(step_id="edit_select", data_schema=schema)

    async def async_step_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit parameters of selected entity."""
        rules = self._get_rules()
        current_rule = next((r for r in rules if r[CONF_RULE_ID] == self._selected_rule_id), None)
        if not current_rule:
            return await self.async_step_init()

        errors: dict[str, str] = {}

        if user_input is not None:
            source_entity = user_input.get(CONF_SOURCE_ENTITY, current_rule[CONF_SOURCE_ENTITY])
            domain = source_entity.split(".", 1)[0]

            if domain not in SUPPORTED_DOMAINS:
                errors["base"] = "unsupported_domain"
            else:
                updated_rules = []
                for r in rules:
                    if r[CONF_RULE_ID] == self._selected_rule_id:
                        updated_rules.append(
                            {
                                CONF_RULE_ID: source_entity,
                                CONF_SOURCE_ENTITY: source_entity,
                                CONF_NAME: user_input.get(CONF_NAME, "").strip(),
                                CONF_HOLD_DURATION: user_input.get(
                                    CONF_HOLD_DURATION, DEFAULT_HOLD_DURATION
                                ),
                                CONF_GRACE_PERIOD: user_input.get(
                                    CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD
                                ),
                                CONF_OPTIMISTIC: user_input.get(
                                    CONF_OPTIMISTIC, DEFAULT_OPTIMISTIC
                                ),
                                CONF_OTA_DURATION: normalize_ota_duration(
                                    user_input.get(
                                        CONF_OTA_DURATION,
                                        r.get(CONF_OTA_DURATION, DEFAULT_OTA_DURATION),
                                    )
                                ),
                                CONF_PING_INTERVAL: normalize_ping_interval(
                                    user_input.get(
                                        CONF_PING_INTERVAL,
                                        r.get(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL),
                                    )
                                ),
                                CONF_PING_METHOD: user_input.get(
                                    CONF_PING_METHOD,
                                    r.get(CONF_PING_METHOD, DEFAULT_PING_METHOD),
                                ),
                                CONF_AUTO_OTA_TRIGGER: bool(
                                    user_input.get(
                                        CONF_AUTO_OTA_TRIGGER,
                                        r.get(CONF_AUTO_OTA_TRIGGER, DEFAULT_AUTO_OTA_TRIGGER),
                                    )
                                ),
                                CONF_ON_OTA_FAILURE: user_input.get(
                                    CONF_ON_OTA_FAILURE,
                                    r.get(CONF_ON_OTA_FAILURE, DEFAULT_ON_OTA_FAILURE),
                                ),
                                CONF_ON_OTA_TIMEOUT: user_input.get(
                                    CONF_ON_OTA_TIMEOUT,
                                    r.get(CONF_ON_OTA_TIMEOUT, DEFAULT_ON_OTA_TIMEOUT),
                                ),
                            }
                        )
                    else:
                        updated_rules.append(r)

                new_options = {**self.config_entry.options, CONF_RULES: updated_rules}
                return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SOURCE_ENTITY, default=current_rule[CONF_SOURCE_ENTITY]
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=SUPPORTED_DOMAINS)
                ),
                vol.Optional(
                    CONF_NAME, default=current_rule.get(CONF_NAME, "")
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_HOLD_DURATION,
                    default=current_rule.get(CONF_HOLD_DURATION, DEFAULT_HOLD_DURATION),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_GRACE_PERIOD,
                    default=current_rule.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_OPTIMISTIC,
                    default=current_rule.get(CONF_OPTIMISTIC, DEFAULT_OPTIMISTIC),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_OTA_DURATION,
                    default=current_rule.get(CONF_OTA_DURATION, DEFAULT_OTA_DURATION),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_OTA_DURATION,
                        max=MAX_OTA_DURATION,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="min",
                    )
                ),
                vol.Optional(
                    CONF_PING_INTERVAL,
                    default=current_rule.get(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_PING_INTERVAL,
                        max=MAX_PING_INTERVAL,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(
                    CONF_PING_METHOD,
                    default=current_rule.get(CONF_PING_METHOD, DEFAULT_PING_METHOD),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="auto", label="Automatique (Recommandé)"),
                            selector.SelectOptionDict(value="z2m_get", label="Zigbee2MQTT (/get)"),
                            selector.SelectOptionDict(value="zha_ping", label="ZHA Ping"),
                            selector.SelectOptionDict(value="ha_update", label="Home Assistant Entity Update"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_AUTO_OTA_TRIGGER,
                    default=current_rule.get(CONF_AUTO_OTA_TRIGGER, DEFAULT_AUTO_OTA_TRIGGER),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_ON_OTA_FAILURE,
                    default=current_rule.get(CONF_ON_OTA_FAILURE, DEFAULT_ON_OTA_FAILURE),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=OTA_FAILURE_KEEP_ALIVE, label="Maintenir actif pour relancer (Recommandé)"),
                            selector.SelectOptionDict(value=OTA_FAILURE_STOP, label="Arrêter immédiatement le défibrillateur"),
                            selector.SelectOptionDict(value=OTA_FAILURE_RETRY, label="Relancer automatiquement l'OTA (max 2 fois)"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_ON_OTA_TIMEOUT,
                    default=current_rule.get(CONF_ON_OTA_TIMEOUT, DEFAULT_ON_OTA_TIMEOUT),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=OTA_TIMEOUT_EXTEND, label="Prolonger de +15 min si toujours en cours (Recommandé)"),
                            selector.SelectOptionDict(value=OTA_TIMEOUT_STOP, label="Arrêter strictement à l'échéance"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="edit",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "source": current_rule[CONF_SOURCE_ENTITY],
                "name": current_rule.get(CONF_NAME) or current_rule[CONF_SOURCE_ENTITY],
            },
        )

    async def async_step_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Delete a KeepActive entity."""
        rules = self._get_rules()
        if not rules:
            return await self.async_step_init()

        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get("confirm_delete", False):
                errors["base"] = "must_confirm_delete"
            else:
                rule_to_delete = user_input["rule_to_delete"]
                updated_rules = [r for r in rules if r[CONF_RULE_ID] != rule_to_delete]

                # Attempt clean removal from Home Assistant Entity Registry
                if hasattr(self, "hass") and self.hass:
                    try:
                        from homeassistant.helpers import entity_registry as er

                        ent_reg = er.async_get(self.hass)
                        unique_id = f"{DOMAIN}_{self.config_entry.entry_id}_{rule_to_delete}"
                        platform = get_platform_from_entity(rule_to_delete)
                        entity_id = ent_reg.async_get_entity_id(platform, DOMAIN, unique_id)
                        if entity_id:
                            ent_reg.async_remove(entity_id)
                    except Exception as exc:
                        _LOGGER.debug("Could not remove entity from registry: %s", exc)

                new_options = {**self.config_entry.options, CONF_RULES: updated_rules}
                return self.async_create_entry(title="", data=new_options)

        options = [
            selector.SelectOptionDict(
                value=r[CONF_RULE_ID],
                label=f"{r.get(CONF_NAME) or r[CONF_SOURCE_ENTITY]} ({r[CONF_SOURCE_ENTITY]})",
            )
            for r in rules
        ]

        schema = vol.Schema(
            {
                vol.Required("rule_to_delete", default=rules[0][CONF_RULE_ID]): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.LIST)
                ),
                vol.Required("confirm_delete", default=False): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="delete", data_schema=schema, errors=errors)
