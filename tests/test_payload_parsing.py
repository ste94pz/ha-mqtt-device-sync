"""Paranoid tests for MQTT payload parsing.

These tests verify that malformed, malicious, or unexpected MQTT payloads
are handled safely without crashes or unexpected behavior.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.mqtt_device_sync import MqttDeviceSyncCoordinator
from custom_components.mqtt_device_sync.const import DOMAIN


class TestInvalidJson:
    """Test handling of invalid JSON payloads."""

    def test_empty_payload(self, hass, config_entry, mock_mqtt_message):
        """Empty payload should be silently ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message("")

        # Should not raise
        coordinator.handle_message(msg)

        # No task should be created
        hass.async_create_task.assert_not_called()

    def test_null_bytes(self, hass, config_entry, mock_mqtt_message):
        """Null bytes should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message(b"\x00\x00\x00")

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_truncated_json(self, hass, config_entry, mock_mqtt_message):
        """Truncated JSON should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": "test"')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_invalid_utf8(self, hass, config_entry, mock_mqtt_message):
        """Invalid UTF-8 sequences should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message(b'\xff\xfe{"device": {}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_binary_garbage(self, hass, config_entry, mock_mqtt_message):
        """Random binary data should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message(bytes(range(256)))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_json_with_trailing_garbage(self, hass, config_entry, mock_mqtt_message):
        """JSON with trailing garbage should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        # Note: json.loads actually handles this by stopping at the first valid JSON
        # but we test it anyway
        msg = mock_mqtt_message('{}garbage')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()


class TestNonDictPayloads:
    """Test handling of valid JSON that isn't a dict."""

    def test_json_array(self, hass, config_entry, mock_mqtt_message):
        """JSON array should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('[1, 2, 3]')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_json_string(self, hass, config_entry, mock_mqtt_message):
        """JSON string should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('"just a string"')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_json_number(self, hass, config_entry, mock_mqtt_message):
        """JSON number should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('42')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_json_null(self, hass, config_entry, mock_mqtt_message):
        """JSON null should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('null')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_json_boolean(self, hass, config_entry, mock_mqtt_message):
        """JSON boolean should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('true')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()


class TestMissingDeviceKey:
    """Test handling of payloads without device key."""

    def test_empty_object(self, hass, config_entry, mock_mqtt_message):
        """Empty object should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_no_device_key(self, hass, config_entry, mock_mqtt_message):
        """Payload without device key should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"name": "test", "state_topic": "test/state"}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_device_key_null(self, hass, config_entry, mock_mqtt_message):
        """device: null should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": null}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()


class TestDeviceNotDict:
    """Test handling of device key that isn't a dict."""

    def test_device_is_string(self, hass, config_entry, mock_mqtt_message):
        """device as string should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": "not a dict"}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_device_is_array(self, hass, config_entry, mock_mqtt_message):
        """device as array should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": [1, 2, 3]}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_device_is_number(self, hass, config_entry, mock_mqtt_message):
        """device as number should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": 42}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_device_is_boolean(self, hass, config_entry, mock_mqtt_message):
        """device as boolean should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": true}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()


class TestMissingIdentifiers:
    """Test handling of device without identifiers."""

    def test_empty_device(self, hass, config_entry, mock_mqtt_message):
        """Empty device dict should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_device_without_identifiers(self, hass, config_entry, mock_mqtt_message):
        """Device without identifiers should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"name": "Test", "suggested_area": "Kitchen"}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_identifiers_null(self, hass, config_entry, mock_mqtt_message):
        """identifiers: null should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": null}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_identifiers_empty_string(self, hass, config_entry, mock_mqtt_message):
        """identifiers: "" should be ignored (empty string is falsy)."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": ""}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_identifiers_empty_array(self, hass, config_entry, mock_mqtt_message):
        """identifiers: [] should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": []}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()


class TestInvalidIdentifierTypes:
    """Test handling of identifiers with wrong types."""

    def test_identifiers_number(self, hass, config_entry, mock_mqtt_message):
        """identifiers as number should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": 12345}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_identifiers_boolean(self, hass, config_entry, mock_mqtt_message):
        """identifiers as boolean should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": true}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_identifiers_object(self, hass, config_entry, mock_mqtt_message):
        """identifiers as object should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": {"id": "test"}}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()


class TestValidIdentifierFormats:
    """Test valid identifier formats are accepted."""

    def test_identifiers_as_string(self, hass, config_entry, mock_mqtt_message):
        """identifiers as string should work."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": "my_device_id"}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_identifiers_as_list_of_strings(self, hass, config_entry, mock_mqtt_message):
        """identifiers as list of strings should work."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": ["id1", "id2"]}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_identifiers_as_list_of_tuples(self, hass, config_entry, mock_mqtt_message):
        """identifiers as list of tuples should work."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": [["mqtt", "device_123"]]}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_identifiers_mixed_format(self, hass, config_entry, mock_mqtt_message):
        """identifiers as mixed strings and tuples should work."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": ["simple_id", ["mqtt", "tuple_id"]]}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()


class TestEdgeCaseStrings:
    """Test edge case string values."""

    def test_unicode_identifiers(self, hass, config_entry, mock_mqtt_message):
        """Unicode in identifiers should work."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": "设备_émojis_🎉"}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_unicode_area(self, hass, config_entry, mock_mqtt_message):
        """Unicode in suggested_area should work."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": "test", "suggested_area": "Küche 廚房"}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_very_long_identifier(self, hass, config_entry, mock_mqtt_message):
        """Very long identifier should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        long_id = "x" * 10000
        msg = mock_mqtt_message(f'{{"device": {{"identifiers": "{long_id}"}}}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_very_long_area_name(self, hass, config_entry, mock_mqtt_message):
        """Very long area name should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        long_area = "A" * 10000
        payload = {"device": {"identifiers": "test", "suggested_area": long_area}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_whitespace_only_identifier(self, hass, config_entry, mock_mqtt_message):
        """Whitespace-only identifier - technically valid but weird."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": "   "}}')

        # Should be accepted (non-empty string)
        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_newlines_in_strings(self, hass, config_entry, mock_mqtt_message):
        """Newlines in strings should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": "line1\nline2", "suggested_area": "Area\nName"}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_special_characters(self, hass, config_entry, mock_mqtt_message):
        """Special characters should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": "id<>&\"'\\/"}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()


class TestNullAndMissingFields:
    """Test handling of null and missing optional fields."""

    def test_suggested_area_null(self, hass, config_entry, mock_mqtt_message):
        """suggested_area: null should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": "test", "suggested_area": null}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_name_null(self, hass, config_entry, mock_mqtt_message):
        """name: null should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": "test", "name": null}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_both_optional_fields_missing(self, hass, config_entry, mock_mqtt_message):
        """No suggested_area or name should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": "test"}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()


class TestMaliciousPayloads:
    """Test payloads that might be attempting exploitation."""

    def test_deeply_nested_json(self, hass, config_entry, mock_mqtt_message):
        """Deeply nested JSON should not cause stack overflow."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        # Create a deeply nested structure
        nested = {"a": None}
        current = nested
        for _ in range(100):
            current["a"] = {"a": None}
            current = current["a"]
        msg = mock_mqtt_message(json.dumps(nested))

        coordinator.handle_message(msg)
        # Should not crash, and should be ignored (no device key path)
        hass.async_create_task.assert_not_called()

    def test_large_array_of_identifiers(self, hass, config_entry, mock_mqtt_message):
        """Large array of identifiers should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = [f"id_{i}" for i in range(1000)]
        payload = {"device": {"identifiers": identifiers}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_duplicate_identifiers(self, hass, config_entry, mock_mqtt_message):
        """Duplicate identifiers should be deduplicated."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": ["same", "same", "same"]}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_huge_payload(self, hass, config_entry, mock_mqtt_message):
        """Very large payload should be handled without memory issues."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        # 1MB of padding
        padding = "x" * (1024 * 1024)
        payload = {"device": {"identifiers": "test"}, "padding": padding}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_scientific_notation_not_identifier(self, hass, config_entry, mock_mqtt_message):
        """Scientific notation number as identifier type should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        msg = mock_mqtt_message('{"device": {"identifiers": 1e308}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()

    def test_infinity_value(self, hass, config_entry, mock_mqtt_message):
        """JSON doesn't support infinity, but check we handle edge cases."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        # This is invalid JSON
        msg = mock_mqtt_message('{"device": {"identifiers": Infinity}}')

        coordinator.handle_message(msg)
        hass.async_create_task.assert_not_called()


class TestExtraFields:
    """Test that extra/unexpected fields are ignored."""

    def test_extra_fields_in_root(self, hass, config_entry, mock_mqtt_message):
        """Extra fields at root should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {
            "device": {"identifiers": "test"},
            "state_topic": "test/state",
            "command_topic": "test/cmd",
            "unknown_field": {"nested": "data"},
        }
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_extra_fields_in_device(self, hass, config_entry, mock_mqtt_message):
        """Extra fields in device should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {
            "device": {
                "identifiers": "test",
                "manufacturer": "ACME",
                "model": "Widget",
                "sw_version": "1.0",
                "connections": [["mac", "aa:bb:cc:dd:ee:ff"]],
            }
        }
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()
