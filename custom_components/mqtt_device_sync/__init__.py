"""MQTT Device Sync - Sync device metadata from MQTT discovery to HA device registry."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, device_registry as dr
from homeassistant.helpers.event import async_call_later

from .const import (
    CONF_DISCOVERY_PREFIX,
    CONF_NAME_DELIMITERS,
    CONF_OVERWRITE_EXISTING,
    CONF_PARSE_AREA_FROM_NAME,
    CONF_SYNC_AREA,
    CONF_SYNC_NAME,
    DEFAULT_DISCOVERY_PREFIX,
    DEFAULT_NAME_DELIMITERS,
    DEFAULT_OVERWRITE_EXISTING,
    DEFAULT_PARSE_AREA_FROM_NAME,
    DEFAULT_SYNC_AREA,
    DEFAULT_SYNC_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

RETRY_DELAY = 5  # seconds
MAX_RETRIES = 3


@dataclass
class PendingUpdate:
    """Pending device update waiting for device to appear."""

    identifiers: frozenset[tuple[str, str]]
    suggested_area: str | None
    device_name: str | None
    retries: int = 0


class MqttDeviceSyncCoordinator:
    """Coordinator for MQTT Device Sync."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.pending: dict[frozenset[tuple[str, str]], PendingUpdate] = {}
        self.synced_state: dict[str, tuple[str | None, str | None]] = {}
        self._retry_timers: dict[frozenset[tuple[str, str]], asyncio.TimerHandle] = {}

    @property
    def sync_area(self) -> bool:
        """Return sync_area option."""
        return self.entry.options.get(CONF_SYNC_AREA, DEFAULT_SYNC_AREA)

    @property
    def sync_name(self) -> bool:
        """Return sync_name option."""
        return self.entry.options.get(CONF_SYNC_NAME, DEFAULT_SYNC_NAME)

    @property
    def overwrite(self) -> bool:
        """Return overwrite_existing option."""
        return self.entry.options.get(CONF_OVERWRITE_EXISTING, DEFAULT_OVERWRITE_EXISTING)

    @property
    def parse_area_from_name(self) -> bool:
        """Return parse_area_from_name option."""
        return self.entry.options.get(CONF_PARSE_AREA_FROM_NAME, DEFAULT_PARSE_AREA_FROM_NAME)

    @property
    def name_delimiters(self) -> list[str]:
        """Return list of name delimiters."""
        delim_str = self.entry.options.get(CONF_NAME_DELIMITERS, DEFAULT_NAME_DELIMITERS)
        return [d.strip() for d in delim_str.split(",") if d.strip()]

    def parse_area_from_device_name(self, name: str) -> tuple[str | None, str | None]:
        """Parse area and device name from a device name string.

        Tries delimiter-based splitting first, then matches against existing areas.

        Returns:
            tuple of (area_name, parsed_device_name) or (None, None) if no match
        """
        if not name:
            return None, None

        # Try delimiter-based splitting
        for delimiter in self.name_delimiters:
            if delimiter in name:
                parts = name.split(delimiter, 1)
                area = parts[0].strip()
                device = parts[1].strip() if len(parts) > 1 else ""
                if area and device:
                    _LOGGER.debug(
                        "Parsed area from name: '%s' -> area='%s', name='%s'",
                        name, area, device
                    )
                    return area, device

        # Try matching against existing area names (for "Laundry Motion" style)
        area_registry = ar.async_get(self.hass)
        areas = area_registry.async_list_areas()

        # Sort by name length descending to match longest area name first
        # e.g., "Living Room" before "Living"
        sorted_areas = sorted(areas, key=lambda a: len(a.name), reverse=True)

        for area in sorted_areas:
            area_name = area.name
            # Check if name starts with area name (case-insensitive)
            if name.lower().startswith(area_name.lower()):
                remainder = name[len(area_name):].strip()
                if remainder:
                    _LOGGER.debug(
                        "Matched existing area in name: '%s' -> area='%s', name='%s'",
                        name, area_name, remainder
                    )
                    return area_name, remainder

        return None, None

    def cancel_pending(self) -> None:
        """Cancel all pending retry timers."""
        for timer in self._retry_timers.values():
            timer.cancel()
        self._retry_timers.clear()
        self.pending.clear()

    @callback
    def handle_message(self, msg: mqtt.ReceiveMessage) -> None:
        """Handle incoming MQTT discovery message."""
        try:
            payload = json.loads(msg.payload)
        except (json.JSONDecodeError, TypeError):
            return

        if not isinstance(payload, dict):
            return

        device_info = payload.get("device")
        if not device_info or not isinstance(device_info, dict):
            return

        identifiers = device_info.get("identifiers")
        if not identifiers:
            return

        # Normalize identifiers to frozenset of tuples
        if isinstance(identifiers, str):
            identifier_set = frozenset({("mqtt", identifiers)})
        elif isinstance(identifiers, list):
            identifier_set = frozenset(
                ("mqtt", i) if isinstance(i, str) else tuple(i)
                for i in identifiers
            )
        else:
            return

        suggested_area = device_info.get("suggested_area")
        device_name = device_info.get("name")
        parsed_name = None

        # If no suggested_area and parsing is enabled, try to extract from name
        if not suggested_area and self.parse_area_from_name and device_name:
            parsed_area, parsed_name = self.parse_area_from_device_name(device_name)
            if parsed_area:
                suggested_area = parsed_area
                _LOGGER.debug(
                    "Using parsed area '%s' from device name '%s'",
                    suggested_area,
                    device_name,
                )

        _LOGGER.debug(
            "Discovery: identifiers=%s, suggested_area=%s, name=%s",
            identifier_set,
            suggested_area,
            device_name,
        )

        self.hass.async_create_task(
            self.async_update_device(
                identifier_set, suggested_area, device_name, parsed_name=parsed_name
            )
        )

    async def async_update_device(
        self,
        identifiers: frozenset[tuple[str, str]],
        suggested_area: str | None,
        device_name: str | None,
        retry_count: int = 0,
        parsed_name: str | None = None,
    ) -> None:
        """Update device registry with metadata from MQTT discovery.

        Args:
            identifiers: Device identifiers
            suggested_area: Area name from discovery or parsed from name
            device_name: Original device name from discovery
            retry_count: Current retry attempt
            parsed_name: Device name parsed from "Area / Name" format (used if provided)
        """
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(identifiers=set(identifiers))

        if device is None:
            if retry_count < MAX_RETRIES:
                # Queue for retry
                self.pending[identifiers] = PendingUpdate(
                    identifiers=identifiers,
                    suggested_area=suggested_area,
                    device_name=device_name,
                    retries=retry_count,
                )
                _LOGGER.debug(
                    "Device not found for %s, scheduling retry %d/%d",
                    identifiers,
                    retry_count + 1,
                    MAX_RETRIES,
                )
                self._schedule_retry(
                    identifiers, suggested_area, device_name, retry_count, parsed_name
                )
            else:
                _LOGGER.warning(
                    "Device not found for %s after %d retries, giving up",
                    identifiers,
                    MAX_RETRIES,
                )
                self.pending.pop(identifiers, None)
            return

        # Device found - clear any pending retry
        self.pending.pop(identifiers, None)
        if identifiers in self._retry_timers:
            self._retry_timers.pop(identifiers).cancel()

        # Determine effective name (parsed_name takes precedence if area was parsed)
        effective_name = parsed_name if parsed_name else device_name

        # Deduplication: check if we'd make the same update
        cache_key = device.id
        cached = self.synced_state.get(cache_key)
        if cached == (suggested_area, effective_name):
            _LOGGER.debug("Skipping duplicate update for device %s", device.name)
            return

        updates: dict[str, Any] = {}

        # Handle area sync
        if self.sync_area and suggested_area:
            if self.overwrite or device.area_id is None:
                area_registry = ar.async_get(self.hass)
                area = area_registry.async_get_area_by_name(suggested_area)

                if area is None:
                    area = area_registry.async_create(suggested_area)
                    _LOGGER.info("Created area '%s'", suggested_area)

                if device.area_id != area.id:
                    updates["area_id"] = area.id

        # Handle name sync (use parsed_name if available from area parsing)
        name_to_sync = parsed_name if parsed_name else device_name
        if self.sync_name and name_to_sync:
            if self.overwrite or device.name_by_user is None:
                if device.name_by_user != name_to_sync:
                    updates["name_by_user"] = name_to_sync

        if updates:
            device_registry.async_update_device(device.id, **updates)
            _LOGGER.info("Updated device %s (%s): %s", device.name, device.id, updates)

        # Update cache
        self.synced_state[cache_key] = (suggested_area, effective_name)

    def _schedule_retry(
        self,
        identifiers: frozenset[tuple[str, str]],
        suggested_area: str | None,
        device_name: str | None,
        retry_count: int,
        parsed_name: str | None = None,
    ) -> None:
        """Schedule a retry for device update."""
        if identifiers in self._retry_timers:
            self._retry_timers.pop(identifiers).cancel()

        @callback
        def retry_callback(_now: Any) -> None:
            self._retry_timers.pop(identifiers, None)
            self.hass.async_create_task(
                self.async_update_device(
                    identifiers, suggested_area, device_name, retry_count + 1, parsed_name
                )
            )

        self._retry_timers[identifiers] = async_call_later(
            self.hass, RETRY_DELAY, retry_callback
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MQTT Device Sync from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = MqttDeviceSyncCoordinator(hass, entry)
    prefix = entry.options.get(CONF_DISCOVERY_PREFIX, DEFAULT_DISCOVERY_PREFIX)
    topic = f"{prefix}/+/+/config"

    unsubscribe = await mqtt.async_subscribe(hass, topic, coordinator.handle_message)

    entry.async_on_unload(unsubscribe)
    entry.async_on_unload(coordinator.cancel_pending)
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    _LOGGER.info("MQTT Device Sync subscribed to %s", topic)
    return True


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload to apply new settings."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
