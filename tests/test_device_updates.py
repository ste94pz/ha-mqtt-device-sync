"""Tests for device registry update logic."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from custom_components.mqtt_device_sync import MqttDeviceSyncCoordinator
from custom_components.mqtt_device_sync.const import (
    CONF_OVERWRITE_EXISTING,
    CONF_SYNC_AREA,
    CONF_SYNC_NAME,
)


class TestDeviceNotFound:
    """Test behavior when device is not in registry."""

    @pytest.mark.asyncio
    async def test_device_not_found_schedules_retry(self, hass, config_entry):
        """When device not found, should schedule retry."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.mqtt_device_sync.async_call_later"
        ) as mock_call_later:
            mock_registry = MagicMock()
            mock_registry.async_get_device.return_value = None
            mock_dr.return_value = mock_registry

            await coordinator.async_update_device(identifiers, "Kitchen", "Device")

            # Should have scheduled a retry
            mock_call_later.assert_called_once()
            assert identifiers in coordinator.pending

    @pytest.mark.asyncio
    async def test_max_retries_reached(self, hass, config_entry):
        """After max retries, should give up with warning."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.mqtt_device_sync._LOGGER"
        ) as mock_logger:
            mock_registry = MagicMock()
            mock_registry.async_get_device.return_value = None
            mock_dr.return_value = mock_registry

            # Simulate max retries reached
            await coordinator.async_update_device(identifiers, "Kitchen", "Device", retry_count=3)

            # Should have logged warning
            mock_logger.warning.assert_called()
            # Should not be in pending
            assert identifiers not in coordinator.pending


class TestAreaSync:
    """Test area synchronization."""

    @pytest.mark.asyncio
    async def test_area_updated_when_unset(self, hass, config_entry, mock_device, mock_area):
        """Area should be updated when device has no area."""
        config_entry.options = {CONF_SYNC_AREA: True, CONF_OVERWRITE_EXISTING: False}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})
        mock_device.area_id = None

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            mock_area_registry = MagicMock()
            mock_area_registry.async_get_area_by_name.return_value = mock_area
            mock_ar.return_value = mock_area_registry

            await coordinator.async_update_device(identifiers, "Living Room", None)

            mock_device_registry.async_update_device.assert_called_once()
            call_kwargs = mock_device_registry.async_update_device.call_args[1]
            assert call_kwargs["area_id"] == mock_area.id

    @pytest.mark.asyncio
    async def test_area_not_updated_when_set_and_no_overwrite(
        self, hass, config_entry, mock_device, mock_area
    ):
        """Area should NOT be updated when already set and overwrite is false."""
        config_entry.options = {CONF_SYNC_AREA: True, CONF_OVERWRITE_EXISTING: False}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})
        mock_device.area_id = "existing_area"  # Already has area

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            await coordinator.async_update_device(identifiers, "New Area", None)

            # Should not have updated
            mock_device_registry.async_update_device.assert_not_called()

    @pytest.mark.asyncio
    async def test_area_updated_when_set_and_overwrite_enabled(
        self, hass, config_entry, mock_device, mock_area
    ):
        """Area SHOULD be updated when overwrite is enabled."""
        config_entry.options = {CONF_SYNC_AREA: True, CONF_OVERWRITE_EXISTING: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})
        mock_device.area_id = "old_area"

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            mock_area_registry = MagicMock()
            mock_area_registry.async_get_area_by_name.return_value = mock_area
            mock_ar.return_value = mock_area_registry

            await coordinator.async_update_device(identifiers, "New Area", None)

            mock_device_registry.async_update_device.assert_called_once()

    @pytest.mark.asyncio
    async def test_area_created_when_not_exists(self, hass, config_entry, mock_device):
        """Area should be created if it doesn't exist."""
        config_entry.options = {CONF_SYNC_AREA: True, CONF_OVERWRITE_EXISTING: False}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})
        mock_device.area_id = None

        new_area = MagicMock()
        new_area.id = "new_area_id"

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            mock_area_registry = MagicMock()
            mock_area_registry.async_get_area_by_name.return_value = None  # Doesn't exist
            mock_area_registry.async_create.return_value = new_area
            mock_ar.return_value = mock_area_registry

            await coordinator.async_update_device(identifiers, "Brand New Area", None)

            # Should have created the area
            mock_area_registry.async_create.assert_called_once_with("Brand New Area")
            # Should have updated device with new area
            mock_device_registry.async_update_device.assert_called_once()

    @pytest.mark.asyncio
    async def test_area_sync_disabled(self, hass, config_entry, mock_device, mock_area):
        """Area should not be updated when sync_area is false."""
        config_entry.options = {CONF_SYNC_AREA: False}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})
        mock_device.area_id = None

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            await coordinator.async_update_device(identifiers, "Kitchen", None)

            mock_device_registry.async_update_device.assert_not_called()


class TestNameSync:
    """Test name synchronization."""

    @pytest.mark.asyncio
    async def test_name_updated_when_enabled(self, hass, config_entry, mock_device):
        """Name should be updated when sync_name is enabled."""
        config_entry.options = {CONF_SYNC_NAME: True, CONF_OVERWRITE_EXISTING: False}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})
        mock_device.area_id = "some_area"  # Has area, won't trigger area update
        mock_device.name_by_user = None

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            await coordinator.async_update_device(identifiers, None, "New Name")

            mock_device_registry.async_update_device.assert_called_once()
            call_kwargs = mock_device_registry.async_update_device.call_args[1]
            assert call_kwargs["name_by_user"] == "New Name"

    @pytest.mark.asyncio
    async def test_name_not_updated_when_disabled(self, hass, config_entry, mock_device):
        """Name should not be updated when sync_name is disabled."""
        config_entry.options = {CONF_SYNC_NAME: False}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})
        mock_device.area_id = "some_area"
        mock_device.name_by_user = None

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            await coordinator.async_update_device(identifiers, None, "New Name")

            mock_device_registry.async_update_device.assert_not_called()

    @pytest.mark.asyncio
    async def test_name_not_overwritten_without_flag(self, hass, config_entry, mock_device):
        """Name should not be overwritten when overwrite is false."""
        config_entry.options = {CONF_SYNC_NAME: True, CONF_OVERWRITE_EXISTING: False}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})
        mock_device.area_id = "some_area"
        mock_device.name_by_user = "Existing Name"

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            await coordinator.async_update_device(identifiers, None, "New Name")

            mock_device_registry.async_update_device.assert_not_called()


class TestDeduplication:
    """Test deduplication logic."""

    @pytest.mark.asyncio
    async def test_duplicate_update_skipped(self, hass, config_entry, mock_device, mock_area):
        """Duplicate updates should be skipped."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})
        mock_device.area_id = None

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            mock_area_registry = MagicMock()
            mock_area_registry.async_get_area_by_name.return_value = mock_area
            mock_ar.return_value = mock_area_registry

            # First update
            await coordinator.async_update_device(identifiers, "Kitchen", "Device")
            assert mock_device_registry.async_update_device.call_count == 1

            # Second update with same values - should be skipped
            await coordinator.async_update_device(identifiers, "Kitchen", "Device")
            # Still only called once
            assert mock_device_registry.async_update_device.call_count == 1

    @pytest.mark.asyncio
    async def test_different_values_not_skipped(self, hass, config_entry, mock_device, mock_area):
        """Different values should trigger update."""
        config_entry.options = {CONF_SYNC_AREA: True, CONF_OVERWRITE_EXISTING: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})

        new_area = MagicMock()
        new_area.id = "new_area_id"

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            mock_area_registry = MagicMock()
            mock_area_registry.async_get_area_by_name.side_effect = [mock_area, new_area]
            mock_ar.return_value = mock_area_registry

            # First update
            mock_device.area_id = None
            await coordinator.async_update_device(identifiers, "Kitchen", "Device")

            # Second update with different area
            mock_device.area_id = mock_area.id
            await coordinator.async_update_device(identifiers, "Bedroom", "Device")

            # Should have been called twice
            assert mock_device_registry.async_update_device.call_count == 2


class TestNoOpUpdates:
    """Test that no-op updates don't call the registry."""

    @pytest.mark.asyncio
    async def test_no_changes_no_update(self, hass, config_entry, mock_device, mock_area):
        """When no changes needed, don't call update."""
        config_entry.options = {CONF_SYNC_AREA: True, CONF_OVERWRITE_EXISTING: False}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})
        mock_device.area_id = mock_area.id  # Already has correct area

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            mock_area_registry = MagicMock()
            mock_area_registry.async_get_area_by_name.return_value = mock_area
            mock_ar.return_value = mock_area_registry

            await coordinator.async_update_device(identifiers, "Living Room", None)

            # Area already set to same value - no update needed
            mock_device_registry.async_update_device.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_suggested_area_no_update(self, hass, config_entry, mock_device):
        """When no suggested_area provided, don't update area."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = frozenset({("mqtt", "test_device")})
        mock_device.area_id = None

        with patch(
            "custom_components.mqtt_device_sync.dr.async_get"
        ) as mock_dr:
            mock_device_registry = MagicMock()
            mock_device_registry.async_get_device.return_value = mock_device
            mock_dr.return_value = mock_device_registry

            await coordinator.async_update_device(identifiers, None, None)

            mock_device_registry.async_update_device.assert_not_called()


class TestCancelPending:
    """Test cleanup of pending retries."""

    def test_cancel_pending_clears_timers(self, hass, config_entry):
        """cancel_pending should cancel all timers."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        # Add some fake pending entries and timers
        mock_timer1 = MagicMock()
        mock_timer2 = MagicMock()
        id1 = frozenset({("mqtt", "device1")})
        id2 = frozenset({("mqtt", "device2")})

        coordinator._retry_timers[id1] = mock_timer1
        coordinator._retry_timers[id2] = mock_timer2
        coordinator.pending[id1] = MagicMock()
        coordinator.pending[id2] = MagicMock()

        coordinator.cancel_pending()

        mock_timer1.cancel.assert_called_once()
        mock_timer2.cancel.assert_called_once()
        assert len(coordinator._retry_timers) == 0
        assert len(coordinator.pending) == 0
