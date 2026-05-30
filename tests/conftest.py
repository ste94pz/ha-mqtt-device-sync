"""Pytest fixtures for MQTT Device Sync tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr

from custom_components.mqtt_device_sync.const import DOMAIN


@pytest.fixture
def hass() -> MagicMock:
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro)
    return hass


@pytest.fixture
def config_entry() -> MagicMock:
    """Create a mock ConfigEntry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.options = {}
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    return entry


@pytest.fixture
def device_registry() -> MagicMock:
    """Create a mock device registry."""
    registry = MagicMock(spec=dr.DeviceRegistry)
    registry.async_get_device = MagicMock(return_value=None)
    registry.async_update_device = MagicMock()
    return registry


@pytest.fixture
def area_registry() -> MagicMock:
    """Create a mock area registry."""
    registry = MagicMock(spec=ar.AreaRegistry)
    registry.async_get_area_by_name = MagicMock(return_value=None)
    registry.async_create = MagicMock()
    return registry


@pytest.fixture
def mock_device() -> MagicMock:
    """Create a mock device."""
    device = MagicMock()
    device.id = "device_123"
    device.name = "Test Device"
    device.area_id = None
    device.name_by_user = None
    return device


@pytest.fixture
def mock_area() -> MagicMock:
    """Create a mock area."""
    area = MagicMock()
    area.id = "area_456"
    area.name = "Living Room"
    return area


@pytest.fixture
def mock_mqtt_message() -> MagicMock:
    """Create a factory for mock MQTT messages."""
    def _create(payload: str | bytes) -> MagicMock:
        msg = MagicMock()
        msg.payload = payload
        msg.topic = "homeassistant/sensor/test/config"
        return msg
    return _create
