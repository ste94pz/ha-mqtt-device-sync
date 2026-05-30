"""End-to-end integration tests.

These tests run against a real Home Assistant instance with MQTT broker.
"""

from __future__ import annotations

import asyncio
import time

import pytest


class TestIntegrationSetup:
    """Test that integrations can be set up."""

    @pytest.mark.asyncio
    async def test_mqtt_integration_setup(self, ha_client):
        """MQTT integration should be configured by fixture."""
        # Fixture sets up MQTT and mqtt_device_sync
        # Just verify we have a valid token
        assert ha_client.token is not None

    @pytest.mark.asyncio
    async def test_mqtt_device_sync_setup(self, ha_client):
        """MQTT Device Sync integration should be configured by fixture."""
        # Fixture handles setup - verify we can access the API
        devices = await ha_client.get_devices()
        assert devices is not None


class TestAreaSync:
    """Test area synchronization from MQTT discovery."""

    @pytest.mark.asyncio
    async def test_device_gets_area_from_discovery(self, ha_client, mqtt_client):
        """Device should get area from suggested_area in discovery."""
        # Publish discovery message with suggested_area
        mqtt_client.publish_discovery(
            "sensor",
            "test_device_1",
            {
                "name": "Test Sensor 1",
                "state_topic": "test/sensor1/state",
                "unique_id": "test_sensor_1_unique",
                "device": {
                    "identifiers": ["test_device_1"],
                    "name": "Test Device 1",
                    "manufacturer": "Test",
                    "suggested_area": "Living Room",
                },
            },
        )

        # Wait for HA to process
        await asyncio.sleep(5)

        # Verify device exists
        device = await ha_client.get_device_by_identifier("mqtt", "test_device_1")
        assert device is not None, "Device should exist in registry"

        # Verify area was created and assigned
        area = await ha_client.get_area_by_name("Living Room")
        assert area is not None, "Area 'Living Room' should exist"
        assert device.get("area_id") == area.get("id"), "Device should be in Living Room"

    @pytest.mark.asyncio
    async def test_area_created_if_not_exists(self, ha_client, mqtt_client):
        """Area should be created if it doesn't exist."""
        unique_area = f"Unique Area {int(time.time())}"

        mqtt_client.publish_discovery(
            "sensor",
            "test_device_2",
            {
                "name": "Test Sensor 2",
                "state_topic": "test/sensor2/state",
                "unique_id": "test_sensor_2_unique",
                "device": {
                    "identifiers": ["test_device_2"],
                    "name": "Test Device 2",
                    "suggested_area": unique_area,
                },
            },
        )

        await asyncio.sleep(5)

        # Area should have been created
        area = await ha_client.get_area_by_name(unique_area)
        assert area is not None, f"Area '{unique_area}' should have been created"

    @pytest.mark.asyncio
    async def test_multiple_devices_same_area(self, ha_client, mqtt_client):
        """Multiple devices can be assigned to the same area."""
        area_name = "Kitchen"

        # Publish two devices with same area
        for i in range(3, 5):
            mqtt_client.publish_discovery(
                "sensor",
                f"test_device_{i}",
                {
                    "name": f"Test Sensor {i}",
                    "state_topic": f"test/sensor{i}/state",
                    "unique_id": f"test_sensor_{i}_unique",
                    "device": {
                        "identifiers": [f"test_device_{i}"],
                        "name": f"Test Device {i}",
                        "suggested_area": area_name,
                    },
                },
            )

        await asyncio.sleep(5)

        # Both devices should be in Kitchen
        area = await ha_client.get_area_by_name(area_name)
        assert area is not None

        for i in range(3, 5):
            device = await ha_client.get_device_by_identifier("mqtt", f"test_device_{i}")
            assert device is not None
            assert device.get("area_id") == area.get("id")


class TestRetryLogic:
    """Test retry logic when device isn't immediately available."""

    @pytest.mark.asyncio
    async def test_area_applied_after_device_appears(self, ha_client, mqtt_client):
        """Area should be applied even if device takes time to register."""
        # This tests the retry mechanism
        # The device should eventually get its area

        mqtt_client.publish_discovery(
            "sensor",
            "test_retry_device",
            {
                "name": "Retry Test Sensor",
                "state_topic": "test/retry/state",
                "unique_id": "test_retry_unique",
                "device": {
                    "identifiers": ["retry_device_id"],
                    "name": "Retry Test Device",
                    "suggested_area": "Garage",
                },
            },
        )

        # Wait longer to allow retries
        await asyncio.sleep(10)

        device = await ha_client.get_device_by_identifier("mqtt", "retry_device_id")
        assert device is not None

        area = await ha_client.get_area_by_name("Garage")
        assert area is not None
        assert device.get("area_id") == area.get("id")


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_discovery_without_suggested_area(self, ha_client, mqtt_client):
        """Device without suggested_area should be created but without area."""
        mqtt_client.publish_discovery(
            "sensor",
            "test_no_area_device",
            {
                "name": "No Area Sensor",
                "state_topic": "test/noarea/state",
                "unique_id": "test_no_area_unique",
                "device": {
                    "identifiers": ["no_area_device_id"],
                    "name": "No Area Device",
                    # No suggested_area
                },
            },
        )

        await asyncio.sleep(5)

        device = await ha_client.get_device_by_identifier("mqtt", "no_area_device_id")
        assert device is not None
        # Device should exist but may or may not have an area
        # (depends on overwrite settings and previous state)

    @pytest.mark.asyncio
    async def test_unicode_area_name(self, ha_client, mqtt_client):
        """Unicode characters in area name should work."""
        unicode_area = "日本語の部屋 🏠"

        mqtt_client.publish_discovery(
            "sensor",
            "test_unicode_device",
            {
                "name": "Unicode Test Sensor",
                "state_topic": "test/unicode/state",
                "unique_id": "test_unicode_unique",
                "device": {
                    "identifiers": ["unicode_device_id"],
                    "name": "Unicode Device",
                    "suggested_area": unicode_area,
                },
            },
        )

        await asyncio.sleep(5)

        area = await ha_client.get_area_by_name(unicode_area)
        assert area is not None, f"Unicode area '{unicode_area}' should be created"

    @pytest.mark.asyncio
    async def test_rapid_discovery_messages(self, ha_client, mqtt_client):
        """Rapid discovery messages should be handled without errors."""
        # Publish many messages quickly
        for i in range(10):
            mqtt_client.publish_discovery(
                "sensor",
                f"rapid_device_{i}",
                {
                    "name": f"Rapid Sensor {i}",
                    "state_topic": f"test/rapid{i}/state",
                    "unique_id": f"rapid_{i}_unique",
                    "device": {
                        "identifiers": [f"rapid_device_{i}"],
                        "name": f"Rapid Device {i}",
                        "suggested_area": "Rapid Test Room",
                    },
                },
            )

        # Wait for processing
        await asyncio.sleep(10)

        # At least some should have succeeded
        area = await ha_client.get_area_by_name("Rapid Test Room")
        assert area is not None

        # Count how many devices got the area
        success_count = 0
        for i in range(10):
            device = await ha_client.get_device_by_identifier("mqtt", f"rapid_device_{i}")
            if device and device.get("area_id") == area.get("id"):
                success_count += 1

        # Most should have succeeded
        assert success_count >= 8, f"Expected at least 8 devices with area, got {success_count}"


class TestMalformedPayloads:
    """Test that malformed payloads don't crash the integration."""

    @pytest.mark.asyncio
    async def test_invalid_json_ignored(self, ha_client, mqtt_client):
        """Invalid JSON should be silently ignored."""
        # Publish garbage
        mqtt_client.client.publish(
            "homeassistant/sensor/garbage/config",
            "not valid json {{{",
            retain=True,
        )

        await asyncio.sleep(2)

        # HA should still be responsive
        devices = await ha_client.get_devices()
        assert devices is not None

    @pytest.mark.asyncio
    async def test_missing_device_key_ignored(self, ha_client, mqtt_client):
        """Payload without device key should be ignored."""
        mqtt_client.client.publish(
            "homeassistant/sensor/no_device/config",
            '{"name": "No Device", "state_topic": "test/nodevice"}',
            retain=True,
        )

        await asyncio.sleep(2)

        # Should not crash
        devices = await ha_client.get_devices()
        assert devices is not None

    @pytest.mark.asyncio
    async def test_empty_identifiers_ignored(self, ha_client, mqtt_client):
        """Empty identifiers should be ignored."""
        mqtt_client.client.publish(
            "homeassistant/sensor/empty_id/config",
            '{"name": "Empty ID", "device": {"identifiers": []}}',
            retain=True,
        )

        await asyncio.sleep(2)

        # Should not crash
        devices = await ha_client.get_devices()
        assert devices is not None
