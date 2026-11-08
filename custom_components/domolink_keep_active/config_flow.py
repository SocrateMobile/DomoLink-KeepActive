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
    CONF_GRACE_PERIOD,
    CONF_HOLD_DURATION,
    CONF_NAME,
    CONF_OPTIMISTIC,
    CONF_SOURCE_ENTITY,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_HOLD_DURATION,
    DEFAULT_OPTIMISTIC,
    DOMAIN,
    SUPPORTED_DOMAINS,
)

_LOGGER = logging.getLogger(__name__)


def get_platform_from_entity(entity_id: str) -> str:
    """Extract platform domain from entity_id."""
    domain = entity_id.split(".", 1)[0]
    return domain if domain in SUPPORTED_DOMAINS else "binary_sensor"


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
                return self.async_create_entry(title=title, data=user_input)

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

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage KeepActive options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_hold = self.config_entry.options.get(
            CONF_HOLD_DURATION,
            self.config_entry.data.get(CONF_HOLD_DURATION, DEFAULT_HOLD_DURATION),
        )
        current_grace = self.config_entry.options.get(
            CONF_GRACE_PERIOD,
            self.config_entry.data.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD),
        )
        current_optimistic = self.config_entry.options.get(
            CONF_OPTIMISTIC,
            self.config_entry.data.get(CONF_OPTIMISTIC, DEFAULT_OPTIMISTIC),
        )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_HOLD_DURATION, default=current_hold
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_GRACE_PERIOD, default=current_grace
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_OPTIMISTIC, default=current_optimistic
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
