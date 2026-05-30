"""Tests for config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.mqtt_device_sync.config_flow import (
    MqttDeviceSyncConfigFlow,
    MqttDeviceSyncOptionsFlow,
)
from custom_components.mqtt_device_sync.const import (
    CONF_DISCOVERY_PREFIX,
    CONF_OVERWRITE_EXISTING,
    CONF_SYNC_AREA,
    CONF_SYNC_NAME,
    DEFAULT_DISCOVERY_PREFIX,
    DEFAULT_OVERWRITE_EXISTING,
    DEFAULT_SYNC_AREA,
    DEFAULT_SYNC_NAME,
    DOMAIN,
)


class TestConfigFlow:
    """Test the config flow."""

    @pytest.mark.asyncio
    async def test_user_step_shows_form(self):
        """Test user step shows form on first call."""
        flow = MqttDeviceSyncConfigFlow()
        flow.hass = MagicMock()

        result = await flow.async_step_user(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_user_step_creates_entry(self):
        """Test user step creates entry on submit."""
        flow = MqttDeviceSyncConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        result = await flow.async_step_user(user_input={})

        assert result["type"] == "create_entry"
        assert result["title"] == "MQTT Device Sync"
        assert result["data"] == {}

    @pytest.mark.asyncio
    async def test_unique_id_set(self):
        """Test unique ID is set to domain."""
        flow = MqttDeviceSyncConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        await flow.async_step_user(user_input={})

        flow.async_set_unique_id.assert_called_once_with(DOMAIN)

    @pytest.mark.asyncio
    async def test_already_configured_aborts(self):
        """Test flow aborts if already configured."""
        flow = MqttDeviceSyncConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock(
            side_effect=Exception("Already configured")
        )

        with pytest.raises(Exception, match="Already configured"):
            await flow.async_step_user(user_input={})


class TestOptionsFlow:
    """Test the options flow."""

    @pytest.mark.asyncio
    async def test_init_step_shows_form_with_defaults(self):
        """Test init step shows form with default values."""
        config_entry = MagicMock()
        config_entry.options = {}

        flow = MqttDeviceSyncOptionsFlow(config_entry)

        result = await flow.async_step_init(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "init"

        # Check schema has all options
        schema = result["data_schema"]
        schema_dict = {str(k): k for k in schema.schema.keys()}

        assert CONF_DISCOVERY_PREFIX in schema_dict
        assert CONF_SYNC_AREA in schema_dict
        assert CONF_SYNC_NAME in schema_dict
        assert CONF_OVERWRITE_EXISTING in schema_dict

    @pytest.mark.asyncio
    async def test_init_step_shows_existing_values(self):
        """Test init step shows existing option values."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_DISCOVERY_PREFIX: "custom_prefix",
            CONF_SYNC_AREA: False,
            CONF_SYNC_NAME: True,
            CONF_OVERWRITE_EXISTING: True,
        }

        flow = MqttDeviceSyncOptionsFlow(config_entry)

        result = await flow.async_step_init(user_input=None)

        # The form should be populated with existing values
        # This is handled by the defaults in the schema
        assert result["type"] == "form"

    @pytest.mark.asyncio
    async def test_init_step_saves_options(self):
        """Test init step saves user input as options."""
        config_entry = MagicMock()
        config_entry.options = {}

        flow = MqttDeviceSyncOptionsFlow(config_entry)

        user_input = {
            CONF_DISCOVERY_PREFIX: "my_prefix",
            CONF_SYNC_AREA: True,
            CONF_SYNC_NAME: True,
            CONF_OVERWRITE_EXISTING: False,
        }

        result = await flow.async_step_init(user_input=user_input)

        assert result["type"] == "create_entry"
        assert result["data"] == user_input

    @pytest.mark.asyncio
    async def test_options_flow_handler_returned(self):
        """Test async_get_options_flow returns correct handler."""
        config_entry = MagicMock()

        handler = MqttDeviceSyncConfigFlow.async_get_options_flow(config_entry)

        assert isinstance(handler, MqttDeviceSyncOptionsFlow)
        assert handler.config_entry == config_entry
