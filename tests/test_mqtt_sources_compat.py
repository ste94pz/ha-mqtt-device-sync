"""Tests verifying compatibility with various MQTT discovery sources.

Tests real-world payload formats from:
- Tasmota
- ESPHome
- rtl_433
- OpenMQTTGateway
- IOTLink
- room-assistant
- Valetudo
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from custom_components.mqtt_device_sync import MqttDeviceSyncCoordinator
from custom_components.mqtt_device_sync.const import (
    CONF_SYNC_AREA,
    CONF_SYNC_NAME,
)


# Real payload examples from various MQTT sources


TASMOTA_SENSOR_PAYLOAD = {
    "name": "Tasmota Temperature",
    "state_topic": "tele/tasmota_1C91EA/SENSOR",
    "availability_topic": "tele/tasmota_1C91EA/LWT",
    "payload_available": "Online",
    "payload_not_available": "Offline",
    "device_class": "temperature",
    "unit_of_measurement": "°C",
    "value_template": "{{ value_json.AM2301.Temperature }}",
    "unique_id": "1C91EA_AM2301_Temperature",
    "device": {
        "identifiers": ["1C91EA"],
        "name": "Tasmota Sensor",
        "model": "Generic",
        "manufacturer": "Tasmota",
        "sw_version": "14.4.1",
    },
}

ESPHOME_SENSOR_PAYLOAD = {
    "name": "Living Room Temperature",
    "state_topic": "esphome/living_room_sensor/sensor/temperature/state",
    "availability_topic": "esphome/living_room_sensor/status",
    "device_class": "temperature",
    "unit_of_measurement": "°C",
    "unique_id": "dc4f22ded8f3-temperature",
    "device": {
        "identifiers": ["dc4f22ded8f3"],
        "name": "Living Room Sensor",
        "model": "ESP32",
        "manufacturer": "Espressif",
        "sw_version": "2024.12.0",
        "suggested_area": "Living Room",
        "connections": [["mac", "dc:4f:22:de:d8:f3"]],
    },
}

# ESPHome with abbreviated fields (as actually sent over MQTT)
ESPHOME_ABBREVIATED_PAYLOAD = {
    "name": "Kitchen Humidity",
    "stat_t": "esphome/kitchen/sensor/humidity/state",
    "avty_t": "esphome/kitchen/status",
    "dev_cla": "humidity",
    "unit_of_meas": "%",
    "uniq_id": "aabbccddeeff-humidity",
    "dev": {
        "ids": ["aabbccddeeff"],
        "name": "Kitchen Sensor",
        "mf": "Espressif",
        "mdl": "ESP8266",
        "sw": "2024.12.0",
        "sa": "Kitchen",
        "cns": [["mac", "aa:bb:cc:dd:ee:ff"]],
    },
}

RTL433_SENSOR_PAYLOAD = {
    "name": "Acurite Tower Temperature",
    "state_topic": "rtl_433/devices/Acurite-Tower/12345/temperature_C",
    "device_class": "temperature",
    "unit_of_measurement": "°C",
    "state_class": "measurement",
    "unique_id": "Acurite-Tower-12345-T",
    "device": {
        "identifiers": ["rtl_433_Acurite-Tower_12345"],
        "name": "Acurite Tower 12345",
        "model": "Acurite-Tower",
        "manufacturer": "Acurite",
    },
}

OPENMQTTGATEWAY_BLE_PAYLOAD = {
    "name": "Xiaomi Temperature",
    "state_topic": "home/OpenMQTTGateway/BTtoMQTT/A4C138AABBCC",
    "device_class": "temperature",
    "unit_of_measurement": "°C",
    "value_template": "{{ value_json.tempc }}",
    "unique_id": "OMG_A4C138AABBCC_tempc",
    "device": {
        "identifiers": ["A4C138AABBCC"],
        "name": "Xiaomi Sensor",
        "model": "LYWSD03MMC",
        "manufacturer": "Xiaomi",
        "connections": [["mac", "A4:C1:38:AA:BB:CC"]],
    },
}

IOTLINK_PAYLOAD = {
    "name": "PC CPU Usage",
    "state_topic": "iotlink/workgroup/desktop-pc/windows-monitor/stats/cpu/usage",
    "availability_topic": "iotlink/workgroup/desktop-pc/lwt",
    "unit_of_measurement": "%",
    "unique_id": "desktop-pc_cpu_usage",
    "device": {
        "identifiers": ["iotlink_desktop-pc"],
        "name": "Desktop PC",
        "model": "Windows 11",
        "manufacturer": "IOTLink",
    },
}

VALETUDO_VACUUM_PAYLOAD = {
    "name": "Vacuum",
    "schema": "state",
    "supported_features": ["start", "stop", "return_home", "battery", "status"],
    "command_topic": "valetudo/rockrobo/command",
    "state_topic": "valetudo/rockrobo/state",
    "unique_id": "rockrobo_vacuum",
    "device": {
        "identifiers": ["valetudo_rockrobo"],
        "name": "Rockrobo Vacuum",
        "model": "S5",
        "manufacturer": "Roborock",
        "sw_version": "2024.01.0",
        "suggested_area": "Utility Room",
    },
}

# Device with ONLY connections (no identifiers) - valid per HA spec
CONNECTIONS_ONLY_PAYLOAD = {
    "name": "Smart Plug",
    "state_topic": "smartplug/aabbccddeeff/state",
    "unique_id": "smartplug_aabbccddeeff",
    "device": {
        "connections": [["mac", "aa:bb:cc:dd:ee:ff"]],
        "name": "Smart Plug",
        "manufacturer": "Generic",
    },
}


class TestTasmotaPayloads:
    """Test Tasmota payload handling."""

    def test_tasmota_chipid_identifier(self, hass, config_entry):
        """Tasmota 6-char ChipID should be parsed correctly."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(TASMOTA_SENSOR_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            identifiers = mock_update.call_args[0][0]
            assert identifiers == frozenset({("mqtt", "1C91EA")})


class TestESPHomePayloads:
    """Test ESPHome payload handling."""

    def test_esphome_mac_identifier(self, hass, config_entry):
        """ESPHome MAC address identifier should be parsed correctly."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(ESPHOME_SENSOR_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            identifiers = mock_update.call_args[0][0]
            assert identifiers == frozenset({("mqtt", "dc4f22ded8f3")})

    def test_esphome_suggested_area(self, hass, config_entry):
        """ESPHome suggested_area should be extracted."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(ESPHOME_SENSOR_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            suggested_area = mock_update.call_args[0][1]
            assert suggested_area == "Living Room"

    def test_esphome_abbreviated_identifiers(self, hass, config_entry):
        """ESPHome abbreviated 'ids' field should be parsed correctly."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(ESPHOME_ABBREVIATED_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            # This test will FAIL if we don't handle 'ids' abbreviation
            mock_update.assert_called_once()
            identifiers = mock_update.call_args[0][0]
            assert identifiers == frozenset({("mqtt", "aabbccddeeff")})

    def test_esphome_abbreviated_suggested_area(self, hass, config_entry):
        """ESPHome abbreviated 'sa' field should be parsed correctly."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(ESPHOME_ABBREVIATED_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            # This test will FAIL if we don't handle 'sa' abbreviation
            mock_update.assert_called_once()
            suggested_area = mock_update.call_args[0][1]
            assert suggested_area == "Kitchen"


class TestRtl433Payloads:
    """Test rtl_433 payload handling."""

    def test_rtl433_identifier_format(self, hass, config_entry):
        """rtl_433 model+ID identifier should be parsed correctly."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(RTL433_SENSOR_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            identifiers = mock_update.call_args[0][0]
            assert identifiers == frozenset({("mqtt", "rtl_433_Acurite-Tower_12345")})


class TestOpenMQTTGatewayPayloads:
    """Test OpenMQTTGateway payload handling."""

    def test_omg_ble_identifier(self, hass, config_entry):
        """OpenMQTTGateway BLE MAC identifier should be parsed correctly."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(OPENMQTTGATEWAY_BLE_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            identifiers = mock_update.call_args[0][0]
            assert identifiers == frozenset({("mqtt", "A4C138AABBCC")})


class TestIOTLinkPayloads:
    """Test IOTLink payload handling."""

    def test_iotlink_identifier(self, hass, config_entry):
        """IOTLink computer identifier should be parsed correctly."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(IOTLINK_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            identifiers = mock_update.call_args[0][0]
            assert identifiers == frozenset({("mqtt", "iotlink_desktop-pc")})


class TestValetudoPayloads:
    """Test Valetudo payload handling."""

    def test_valetudo_identifier(self, hass, config_entry):
        """Valetudo vacuum identifier should be parsed correctly."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(VALETUDO_VACUUM_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            identifiers = mock_update.call_args[0][0]
            assert identifiers == frozenset({("mqtt", "valetudo_rockrobo")})

    def test_valetudo_suggested_area(self, hass, config_entry):
        """Valetudo suggested_area should be extracted."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(VALETUDO_VACUUM_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            mock_update.assert_called_once()
            suggested_area = mock_update.call_args[0][1]
            assert suggested_area == "Utility Room"


class TestConnectionsOnlyDevices:
    """Test devices that only provide connections, not identifiers."""

    def test_connections_only_device(self, hass, config_entry):
        """Devices with only connections (no identifiers) should still work."""
        config_entry.options = {CONF_SYNC_AREA: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = json.dumps(CONNECTIONS_ONLY_PAYLOAD)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            # This test will FAIL if we don't handle connections-only devices
            # The expected behavior is to use connections as identifiers
            mock_update.assert_called_once()
            identifiers = mock_update.call_args[0][0]
            # Should extract MAC from connections
            assert identifiers == frozenset({("mac", "aa:bb:cc:dd:ee:ff")})


class TestAbbreviatedFieldNames:
    """Test that abbreviated field names are handled correctly.

    HA MQTT discovery supports these abbreviations:
    - ids -> identifiers
    - cns -> connections
    - sa -> suggested_area
    - mf -> manufacturer
    - mdl -> model
    - sw -> sw_version
    - hw -> hw_version
    """

    def test_abbreviated_device_block(self, hass, config_entry):
        """Test 'dev' abbreviation for 'device'."""
        config_entry.options = {CONF_SYNC_AREA: True, CONF_SYNC_NAME: True}
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        payload = {
            "name": "Test Sensor",
            "state_topic": "test/state",
            "unique_id": "test_123",
            "dev": {  # abbreviated 'device'
                "ids": ["test_device_123"],
                "name": "Test Device",
                "sa": "Bedroom",
            },
        }

        msg = MagicMock()
        msg.payload = json.dumps(payload)

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)

            # This will FAIL if we don't handle 'dev' abbreviation
            mock_update.assert_called_once()
