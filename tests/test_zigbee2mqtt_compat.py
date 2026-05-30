"""Tests verifying compatibility with Zigbee2MQTT discovery messages.

These tests use real-world Z2M discovery payload formats to ensure
the integration correctly handles them.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from custom_components.mqtt_device_sync import MqttDeviceSyncCoordinator
from custom_components.mqtt_device_sync.const import (
    CONF_PARSE_AREA_FROM_NAME,
    CONF_SYNC_AREA,
    CONF_SYNC_NAME,
)


# Real Z2M discovery payload examples (from Z2M source code and docs)
Z2M_LIGHT_PAYLOAD = {
    "availability": [
        {"topic": "zigbee2mqtt/bridge/state", "value_template": "{{ value_json.state }}"}
    ],
    "brightness": True,
    "brightness_scale": 254,
    "command_topic": "zigbee2mqtt/bulb_living_room/set",
    "device": {
        "identifiers": ["zigbee2mqtt_0x0017880104e45553"],
        "manufacturer": "Sengled",
        "model": "Element classic (A19)",
        "model_id": "E11-G13",
        "name": "bulb_living_room",
        "via_device": "zigbee2mqtt_bridge_0x00124b00120144ae",
    },
    "name": None,
    "object_id": "bulb_living_room",
    "origin": {"name": "Zigbee2MQTT", "sw": "1.35.0", "url": "https://www.zigbee2mqtt.io"},
    "schema": "json",
    "state_topic": "zigbee2mqtt/bulb_living_room",
    "unique_id": "0x0017880104e45553_light_zigbee2mqtt",
}

Z2M_SENSOR_PAYLOAD = {
    "availability": [
        {"topic": "zigbee2mqtt/bridge/state", "value_template": "{{ value_json.state }}"}
    ],
    "device": {
        "identifiers": ["zigbee2mqtt_0x00158d0001234567"],
        "manufacturer": "Aqara",
        "model": "Temperature and humidity sensor",
        "model_id": "WSDCGQ11LM",
        "name": "weather_sensor",
    },
    "device_class": "temperature",
    "name": "Temperature",
    "state_class": "measurement",
    "state_topic": "zigbee2mqtt/weather_sensor",
    "unique_id": "0x00158d0001234567_temperature_zigbee2mqtt",
    "unit_of_measurement": "°C",
    "value_template": "{{ value_json.temperature }}",
}

Z2M_WITH_SUGGESTED_AREA = {
    "device": {
        "identifiers": ["zigbee2mqtt_0x00158d0001234567"],
        "manufacturer": "Aqara",
        "model": "Temperature and humidity sensor",
        "name": "bathroom_sensor",
        "suggested_area": "Bathroom",  # User configured in Z2M
    },
    "name": "Temperature",
    "state_topic": "zigbee2mqtt/bathroom_sensor",
    "unique_id": "0x00158d0001234567_temperature_zigbee2mqtt",
}

Z2M_GROUP_PAYLOAD = {
    "availability": [
        {"topic": "zigbee2mqtt/bridge/state", "value_template": "{{ value_json.state }}"}
    ],
    "command_topic": "zigbee2mqtt/living_room_lights/set",
    "device": {
        # Group identifiers include encoded base topic
        "identifiers": ["zigbee2mqtt_1221051039810110150109113116116_1"],
        "name": "living_room_lights",
        "sw_version": "Zigbee2MQTT 1.35.0",
    },
    "name": None,
    "schema": "json",
    "state_topic": "zigbee2mqtt/living_room_lights",
    "unique_id": "1_light_zigbee2mqtt",
}


class TestZigbee2MQTTIdentifiers:
    """Test that Z2M identifier formats are correctly parsed."""

    def test_device_identifier_format(self, hass, config_entry):
        """Z2M device identifiers should be parsed correctly."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(Z2M_LIGHT_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            identifiers = mock_update.call_args[0][0]

            # Should be frozenset with ("mqtt", "zigbee2mqtt_0x...") tuple
            assert identifiers == frozenset({("mqtt", "zigbee2mqtt_0x0017880104e45553")})

    def test_group_identifier_format(self, hass, config_entry):
        """Z2M group identifiers should be parsed correctly."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(Z2M_GROUP_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            identifiers = mock_update.call_args[0][0]

            # Group identifier format
            assert identifiers == frozenset(
                {("mqtt", "zigbee2mqtt_1221051039810110150109113116116_1")}
            )

    def test_sensor_identifier_format(self, hass, config_entry):
        """Z2M sensor identifiers should be parsed correctly."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(Z2M_SENSOR_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            identifiers = mock_update.call_args[0][0]

            assert identifiers == frozenset({("mqtt", "zigbee2mqtt_0x00158d0001234567")})


class TestZigbee2MQTTSuggestedArea:
    """Test suggested_area handling for Z2M payloads."""

    def test_suggested_area_extracted(self, hass, config_entry):
        """suggested_area from Z2M config should be extracted."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(Z2M_WITH_SUGGESTED_AREA)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            # suggested_area should be "Bathroom"
            assert mock_update.call_args[0][1] == "Bathroom"

    def test_no_suggested_area_is_none(self, hass, config_entry):
        """Payloads without suggested_area should pass None."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(Z2M_LIGHT_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            # No suggested_area in payload
            assert mock_update.call_args[0][1] is None


class TestZigbee2MQTTDeviceName:
    """Test device name handling for Z2M payloads."""

    def test_device_name_extracted(self, hass, config_entry):
        """Device name from Z2M should be extracted."""
        config_entry.options = {CONF_SYNC_NAME: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(Z2M_LIGHT_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            # device.name should be "bulb_living_room"
            assert mock_update.call_args[0][2] == "bulb_living_room"


class TestZigbee2MQTTAreaParsing:
    """Test area parsing from Z2M device names."""

    def test_parse_area_from_z2m_friendly_name_slash(self, hass, config_entry):
        """Z2M friendly_name with slash delimiter should parse area."""
        config_entry.options = {
            CONF_SYNC_AREA: True,
            CONF_PARSE_AREA_FROM_NAME: True,
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        # Modified payload with "Living Room / Light" naming
        payload = {
            "device": {
                "identifiers": ["zigbee2mqtt_0x0017880104e45553"],
                "name": "Living Room / Ceiling Light",
                "manufacturer": "Sengled",
            },
            "state_topic": "zigbee2mqtt/living_room_ceiling_light",
            "unique_id": "0x0017880104e45553_light_zigbee2mqtt",
        }

        msg = MagicMock()
        msg.payload = json.dumps(payload)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            # Area should be parsed from name
            assert mock_update.call_args[0][1] == "Living Room"
            # parsed_name should be "Ceiling Light"
            assert mock_update.call_args[1]["parsed_name"] == "Ceiling Light"

    def test_parse_area_from_z2m_friendly_name_dash(self, hass, config_entry):
        """Z2M friendly_name with dash delimiter should parse area."""
        config_entry.options = {
            CONF_SYNC_AREA: True,
            CONF_PARSE_AREA_FROM_NAME: True,
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        payload = {
            "device": {
                "identifiers": ["zigbee2mqtt_0x0017880104e45553"],
                "name": "Kitchen - Motion Sensor",
                "manufacturer": "Aqara",
            },
            "state_topic": "zigbee2mqtt/kitchen_motion",
            "unique_id": "0x0017880104e45553_sensor_zigbee2mqtt",
        }

        msg = MagicMock()
        msg.payload = json.dumps(payload)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            assert mock_update.call_args[0][1] == "Kitchen"
            assert mock_update.call_args[1]["parsed_name"] == "Motion Sensor"

    def test_suggested_area_takes_precedence_over_parsing(self, hass, config_entry):
        """Explicit suggested_area should override name parsing."""
        config_entry.options = {
            CONF_SYNC_AREA: True,
            CONF_PARSE_AREA_FROM_NAME: True,
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        # Has both suggested_area and parseable name
        payload = {
            "device": {
                "identifiers": ["zigbee2mqtt_0x0017880104e45553"],
                "name": "Kitchen / Light",  # Would parse to "Kitchen"
                "suggested_area": "Dining Room",  # Explicit area
            },
            "state_topic": "zigbee2mqtt/test",
            "unique_id": "test_unique",
        }

        msg = MagicMock()
        msg.payload = json.dumps(payload)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            # suggested_area takes precedence
            assert mock_update.call_args[0][1] == "Dining Room"
            # No parsed_name since we didn't parse
            assert mock_update.call_args[1]["parsed_name"] is None


class TestZigbee2MQTTTopicStructure:
    """Verify topic structure compatibility."""

    def test_topic_patterns_match_z2m(self):
        """Verify our subscription patterns match Z2M topics."""
        import re

        # Z2M topic format: {discovery_topic}/{type}/{node_id}/{object_id}/config
        # We subscribe to both:
        # - {prefix}/+/+/config (simple, no node_id)
        # - {prefix}/+/+/+/config (with node_id, used by Z2M)

        z2m_topics = [
            "homeassistant/light/0x0017880104e45553/light/config",
            "homeassistant/sensor/0x00158d0001234567/temperature/config",
            "homeassistant/switch/0x00158d0001234567/switch/config",
            "homeassistant/binary_sensor/0x00158d0001234567/occupancy/config",
            "homeassistant/device_automation/0x0017880104e45553/action_button/config",
        ]

        # Pattern for 4-segment topics (Z2M style with node_id)
        pattern_with_node = re.compile(r"^homeassistant/[^/]+/[^/]+/[^/]+/config$")

        for topic in z2m_topics:
            assert pattern_with_node.match(topic), f"Pattern should match: {topic}"

    def test_simple_topic_pattern(self):
        """Verify simple pattern matches non-Z2M topics."""
        import re

        simple_topics = [
            "homeassistant/light/my_light/config",
            "homeassistant/sensor/temp_sensor/config",
        ]

        pattern_simple = re.compile(r"^homeassistant/[^/]+/[^/]+/config$")

        for topic in simple_topics:
            assert pattern_simple.match(topic), f"Pattern should match: {topic}"


class TestZigbee2MQTTEdgeCases:
    """Test edge cases specific to Z2M."""

    def test_multiple_entities_same_device(self, hass, config_entry):
        """Multiple Z2M entities for same device should all work."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        # Same device, different entities (temperature, humidity, battery)
        device_id = "zigbee2mqtt_0x00158d0001234567"
        base_device = {
            "identifiers": [device_id],
            "manufacturer": "Aqara",
            "model": "Temperature and humidity sensor",
            "name": "bathroom_sensor",
            "suggested_area": "Bathroom",
        }

        entities = ["temperature", "humidity", "battery"]

        for entity in entities:
            payload = {
                "device": base_device,
                "name": entity.capitalize(),
                "state_topic": f"zigbee2mqtt/bathroom_sensor",
                "unique_id": f"0x00158d0001234567_{entity}_zigbee2mqtt",
            }

            msg = MagicMock()
            msg.payload = json.dumps(payload)

            with patch.object(coordinator, "async_update_device") as mock_update:
                coordinator.handle_message(msg)
                mock_update.assert_called_once()
                # All should have same identifiers
                assert mock_update.call_args[0][0] == frozenset({("mqtt", device_id)})
                # All should have same suggested_area
                assert mock_update.call_args[0][1] == "Bathroom"

    def test_via_device_in_payload_ignored(self, hass, config_entry):
        """via_device field should not affect our processing."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(Z2M_LIGHT_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)
            # Should still process correctly despite via_device
            mock_update.assert_called_once()

    def test_empty_identifiers_list_rejected(self, hass, config_entry):
        """Empty identifiers list should be rejected."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        payload = {
            "device": {
                "identifiers": [],  # Empty list
                "name": "test",
            },
            "state_topic": "test/topic",
        }

        msg = MagicMock()
        msg.payload = json.dumps(payload)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)
            # Should not be called due to empty identifiers
            mock_update.assert_not_called()
