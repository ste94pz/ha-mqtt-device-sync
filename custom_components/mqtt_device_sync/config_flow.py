"""Config flow for MQTT Device Sync."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    CONF_DISCOVERY_PREFIX,
    CONF_NAME_DELIMITERS,
    CONF_OVERWRITE_EXISTING,
    CONF_PARSE_AREA_FROM_NAME,
    CONF_SYNC_AREA,
    CONF_SYNC_NAME,
    DEFAULT_DISCOVERY_PREFIX,
    DEFAULT_NAME_DELIMITERS,
    DEFAULT_OVERWRITE_EXISTING,
    DEFAULT_PARSE_AREA_FROM_NAME,
    DEFAULT_SYNC_AREA,
    DEFAULT_SYNC_NAME,
    DOMAIN,
)


class MqttDeviceSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MQTT Device Sync."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="MQTT Device Sync", data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return MqttDeviceSyncOptionsFlow(config_entry)


class MqttDeviceSyncOptionsFlow(OptionsFlow):
    """Handle options flow for MQTT Device Sync."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DISCOVERY_PREFIX,
                        default=options.get(
                            CONF_DISCOVERY_PREFIX, DEFAULT_DISCOVERY_PREFIX
                        ),
                    ): str,
                    vol.Optional(
                        CONF_SYNC_AREA,
                        default=options.get(CONF_SYNC_AREA, DEFAULT_SYNC_AREA),
                    ): bool,
                    vol.Optional(
                        CONF_SYNC_NAME,
                        default=options.get(CONF_SYNC_NAME, DEFAULT_SYNC_NAME),
                    ): bool,
                    vol.Optional(
                        CONF_OVERWRITE_EXISTING,
                        default=options.get(
                            CONF_OVERWRITE_EXISTING, DEFAULT_OVERWRITE_EXISTING
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_PARSE_AREA_FROM_NAME,
                        default=options.get(
                            CONF_PARSE_AREA_FROM_NAME, DEFAULT_PARSE_AREA_FROM_NAME
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_NAME_DELIMITERS,
                        default=options.get(
                            CONF_NAME_DELIMITERS, DEFAULT_NAME_DELIMITERS
                        ),
                    ): str,
                }
            ),
        )
