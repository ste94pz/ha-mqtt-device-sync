"""Tests for integration setup and teardown."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.mqtt_device_sync import (
    async_setup_entry,
    async_unload_entry,
    async_options_updated,
)
from custom_components.mqtt_device_sync.const import DOMAIN


class TestSetupEntry:
    """Test async_setup_entry."""

    @pytest.mark.asyncio
    async def test_setup_subscribes_to_mqtt(self, hass, config_entry):
        """Test setup subscribes to MQTT discovery topics (both patterns)."""
        mock_unsubscribe = MagicMock()

        with patch(
            "custom_components.mqtt_device_sync.mqtt.async_subscribe",
            new_callable=AsyncMock,
        ) as mock_subscribe:
            mock_subscribe.return_value = mock_unsubscribe

            result = await async_setup_entry(hass, config_entry)

            assert result is True
            # Should subscribe to both simple and node_id patterns
            assert mock_subscribe.call_count == 2

            # Check both topic patterns
            topics = [call[0][1] for call in mock_subscribe.call_args_list]
            assert "homeassistant/+/+/config" in topics
            assert "homeassistant/+/+/+/config" in topics

    @pytest.mark.asyncio
    async def test_setup_uses_custom_prefix(self, hass, config_entry):
        """Test setup uses custom discovery prefix."""
        config_entry.options = {"discovery_prefix": "my_ha"}

        with patch(
            "custom_components.mqtt_device_sync.mqtt.async_subscribe",
            new_callable=AsyncMock,
        ) as mock_subscribe:
            mock_subscribe.return_value = MagicMock()

            await async_setup_entry(hass, config_entry)

            # Should subscribe to both patterns with custom prefix
            assert mock_subscribe.call_count == 2
            topics = [call[0][1] for call in mock_subscribe.call_args_list]
            assert "my_ha/+/+/config" in topics
            assert "my_ha/+/+/+/config" in topics

    @pytest.mark.asyncio
    async def test_setup_registers_unload_callbacks(self, hass, config_entry):
        """Test setup registers cleanup callbacks."""
        with patch(
            "custom_components.mqtt_device_sync.mqtt.async_subscribe",
            new_callable=AsyncMock,
        ) as mock_subscribe:
            mock_subscribe.return_value = MagicMock()

            await async_setup_entry(hass, config_entry)

            # Should have registered unload callbacks
            assert config_entry.async_on_unload.call_count >= 2

    @pytest.mark.asyncio
    async def test_setup_stores_coordinator(self, hass, config_entry):
        """Test setup stores coordinator in hass.data."""
        with patch(
            "custom_components.mqtt_device_sync.mqtt.async_subscribe",
            new_callable=AsyncMock,
        ) as mock_subscribe:
            mock_subscribe.return_value = MagicMock()

            await async_setup_entry(hass, config_entry)

            assert DOMAIN in hass.data
            assert config_entry.entry_id in hass.data[DOMAIN]
            assert "coordinator" in hass.data[DOMAIN][config_entry.entry_id]


class TestUnloadEntry:
    """Test async_unload_entry."""

    @pytest.mark.asyncio
    async def test_unload_removes_data(self, hass, config_entry):
        """Test unload removes entry from hass.data."""
        hass.data[DOMAIN] = {config_entry.entry_id: {"coordinator": MagicMock()}}

        result = await async_unload_entry(hass, config_entry)

        assert result is True
        assert config_entry.entry_id not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_handles_missing_entry(self, hass, config_entry):
        """Test unload handles case where entry doesn't exist."""
        hass.data[DOMAIN] = {}

        # Should not raise
        result = await async_unload_entry(hass, config_entry)

        assert result is True


class TestOptionsUpdated:
    """Test async_options_updated."""

    @pytest.mark.asyncio
    async def test_options_updated_reloads_entry(self, hass, config_entry):
        """Test options update triggers reload."""
        hass.config_entries = MagicMock()
        hass.config_entries.async_reload = AsyncMock()

        await async_options_updated(hass, config_entry)

        hass.config_entries.async_reload.assert_called_once_with(config_entry.entry_id)
