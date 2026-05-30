"""Tests for parsing area from device name."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.mqtt_device_sync import MqttDeviceSyncCoordinator
from custom_components.mqtt_device_sync.const import (
    CONF_NAME_DELIMITERS,
    CONF_PARSE_AREA_FROM_NAME,
    DEFAULT_NAME_DELIMITERS,
)


class TestDelimiterParsing:
    """Test delimiter-based area parsing."""

    def test_slash_delimiter(self, hass, config_entry):
        """Test parsing with slash delimiter."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: DEFAULT_NAME_DELIMITERS,
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        area, name = coordinator.parse_area_from_device_name("Living Room / Plug")
        assert area == "Living Room"
        assert name == "Plug"

    def test_dash_delimiter(self, hass, config_entry):
        """Test parsing with dash delimiter."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: DEFAULT_NAME_DELIMITERS,
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        area, name = coordinator.parse_area_from_device_name("Dining Hall - Shades")
        assert area == "Dining Hall"
        assert name == "Shades"

    def test_custom_delimiter(self, hass, config_entry):
        """Test parsing with custom delimiter."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: " :: , | ",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        area, name = coordinator.parse_area_from_device_name("Kitchen :: Ceiling Light")
        assert area == "Kitchen"
        assert name == "Ceiling Light"

    def test_multiple_delimiters_first_wins(self, hass, config_entry):
        """Test that first matching delimiter is used."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: " / , - ",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        # Has both delimiters, first one (/) should win
        area, name = coordinator.parse_area_from_device_name("A / B - C")
        assert area == "A"
        assert name == "B - C"

    def test_no_delimiter_returns_none(self, hass, config_entry):
        """Test that no delimiter returns None."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: DEFAULT_NAME_DELIMITERS,
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        # Mock area registry with no matching areas
        with patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_registry = MagicMock()
            mock_registry.async_list_areas.return_value = []
            mock_ar.return_value = mock_registry

            area, name = coordinator.parse_area_from_device_name("SimpleDevice")
            assert area is None
            assert name is None

    def test_empty_area_after_split(self, hass, config_entry):
        """Test that empty area after split returns None."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: " / ",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        with patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_registry = MagicMock()
            mock_registry.async_list_areas.return_value = []
            mock_ar.return_value = mock_registry

            area, name = coordinator.parse_area_from_device_name(" / Device")
            assert area is None
            assert name is None

    def test_empty_name_after_split(self, hass, config_entry):
        """Test that empty name after split returns None."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: " / ",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        with patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_registry = MagicMock()
            mock_registry.async_list_areas.return_value = []
            mock_ar.return_value = mock_registry

            area, name = coordinator.parse_area_from_device_name("Area / ")
            assert area is None
            assert name is None

    def test_empty_string_input(self, hass, config_entry):
        """Test that empty string returns None."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: DEFAULT_NAME_DELIMITERS,
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        area, name = coordinator.parse_area_from_device_name("")
        assert area is None
        assert name is None

    def test_none_input(self, hass, config_entry):
        """Test that None input returns None."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: DEFAULT_NAME_DELIMITERS,
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        area, name = coordinator.parse_area_from_device_name(None)
        assert area is None
        assert name is None


class TestExistingAreaMatching:
    """Test matching against existing HA areas."""

    def test_match_existing_area(self, hass, config_entry):
        """Test matching against existing area name."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: " / , - ",  # No delimiter will match
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        with patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_area = MagicMock()
            mock_area.name = "Laundry"
            mock_registry = MagicMock()
            mock_registry.async_list_areas.return_value = [mock_area]
            mock_ar.return_value = mock_registry

            area, name = coordinator.parse_area_from_device_name("Laundry Motion")
            assert area == "Laundry"
            assert name == "Motion"

    def test_match_longest_area_first(self, hass, config_entry):
        """Test that longest matching area name is used."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: "",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        with patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_area1 = MagicMock()
            mock_area1.name = "Living"
            mock_area2 = MagicMock()
            mock_area2.name = "Living Room"
            mock_registry = MagicMock()
            mock_registry.async_list_areas.return_value = [mock_area1, mock_area2]
            mock_ar.return_value = mock_registry

            area, name = coordinator.parse_area_from_device_name("Living Room Light")
            assert area == "Living Room"
            assert name == "Light"

    def test_case_insensitive_match(self, hass, config_entry):
        """Test that area matching is case-insensitive."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: "",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        with patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_area = MagicMock()
            mock_area.name = "Kitchen"
            mock_registry = MagicMock()
            mock_registry.async_list_areas.return_value = [mock_area]
            mock_ar.return_value = mock_registry

            area, name = coordinator.parse_area_from_device_name("KITCHEN Fridge")
            assert area == "Kitchen"  # Returns the actual area name, not the input case
            assert name == "Fridge"

    def test_no_match_without_remainder(self, hass, config_entry):
        """Test that exact area name without remainder returns None."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: "",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        with patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_area = MagicMock()
            mock_area.name = "Kitchen"
            mock_registry = MagicMock()
            mock_registry.async_list_areas.return_value = [mock_area]
            mock_ar.return_value = mock_registry

            # Just "Kitchen" with no device name part
            area, name = coordinator.parse_area_from_device_name("Kitchen")
            assert area is None
            assert name is None


class TestDelimiterPrecedence:
    """Test that delimiter parsing takes precedence over area matching."""

    def test_delimiter_before_area_match(self, hass, config_entry):
        """Test that delimiter parsing happens before area matching."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: " / ",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        # Even if "Office" is an existing area, the delimiter should win
        with patch(
            "custom_components.mqtt_device_sync.ar.async_get"
        ) as mock_ar:
            mock_area = MagicMock()
            mock_area.name = "Office"
            mock_registry = MagicMock()
            mock_registry.async_list_areas.return_value = [mock_area]
            mock_ar.return_value = mock_registry

            area, name = coordinator.parse_area_from_device_name("Bedroom / Lamp")
            assert area == "Bedroom"  # From delimiter, not area match
            assert name == "Lamp"


class TestIntegrationWithDiscovery:
    """Test that parsing integrates with MQTT discovery flow."""

    @pytest.mark.asyncio
    async def test_parse_used_when_no_suggested_area(self, hass, config_entry):
        """Test that parsing is used when suggested_area is missing."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: " / ",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        # Create mock message without suggested_area
        msg = MagicMock()
        msg.payload = '{"device": {"identifiers": ["test"], "name": "Living Room / Plug"}}'

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)
            # Should have called with parsed area
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            # suggested_area should be "Living Room" (parsed)
            assert call_args[0][1] == "Living Room"
            # parsed_name should be "Plug"
            assert call_args[1]["parsed_name"] == "Plug"

    @pytest.mark.asyncio
    async def test_suggested_area_takes_precedence(self, hass, config_entry):
        """Test that explicit suggested_area is used over parsing."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: " / ",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        # Create mock message WITH suggested_area
        msg = MagicMock()
        msg.payload = '{"device": {"identifiers": ["test"], "name": "Kitchen / Plug", "suggested_area": "Office"}}'

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            # suggested_area should be "Office" (from payload), not "Kitchen"
            assert call_args[0][1] == "Office"
            # parsed_name should be None since we didn't parse
            assert call_args[1]["parsed_name"] is None

    @pytest.mark.asyncio
    async def test_parsing_disabled_by_default(self, hass, config_entry):
        """Test that parsing is disabled when option is off."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: False,
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        msg = MagicMock()
        msg.payload = '{"device": {"identifiers": ["test"], "name": "Living Room / Plug"}}'

        with patch.object(coordinator, "async_update_device") as mock_update:
            coordinator.handle_message(msg)
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            # suggested_area should be None (parsing disabled)
            assert call_args[0][1] is None


class TestEdgeCases:
    """Test edge cases in name parsing."""

    def test_unicode_area_name(self, hass, config_entry):
        """Test parsing with unicode characters."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: " / ",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        area, name = coordinator.parse_area_from_device_name("日本語の部屋 / センサー")
        assert area == "日本語の部屋"
        assert name == "センサー"

    def test_whitespace_handling(self, hass, config_entry):
        """Test that whitespace is properly stripped."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: " / ",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        area, name = coordinator.parse_area_from_device_name("  Kitchen  /  Light  ")
        assert area == "Kitchen"
        assert name == "Light"

    def test_multiple_words_in_area_and_name(self, hass, config_entry):
        """Test parsing with multiple words on both sides."""
        config_entry.options = {
            CONF_PARSE_AREA_FROM_NAME: True,
            CONF_NAME_DELIMITERS: " / ",
        }
        coordinator = MqttDeviceSyncCoordinator(hass, config_entry)

        area, name = coordinator.parse_area_from_device_name(
            "Master Bedroom Suite / Ceiling Fan Light"
        )
        assert area == "Master Bedroom Suite"
        assert name == "Ceiling Fan Light"
