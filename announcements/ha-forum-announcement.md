# Home Assistant Community Forum Announcement

**Category:** Share your Projects!
**Title:** MQTT Device Sync - Finally sync suggested_area after first discovery

---

## The Problem

You've probably hit this: you set `suggested_area` in Zigbee2MQTT, ESPHome, or another MQTT source, but Home Assistant ignores it after the first discovery. The device stays in "No Area" forever unless you manually fix it.

This has been requested for years:
- [Z2M: suggested_area not updating](https://github.com/zigbee2mqtt/hassio-zigbee2mqtt/issues/84)
- [HA Core: MQTT discovery should update suggested_area](https://github.com/home-assistant/core/issues/XXXXX)
- Countless forum threads asking "why doesn't my area update?"

HA's position is that it "preserves user customizations" - which makes sense, but leaves no option for those of us who want the MQTT source to be authoritative.

## The Solution

**MQTT Device Sync** is a custom integration that runs alongside HA's MQTT integration and actually applies `suggested_area` (and optionally device name) to the device registry.

### Features

- Syncs `suggested_area` from any MQTT discovery source
- Optionally syncs device name
- Auto-creates missing areas
- **Parse area from device name** - for sources like Tasmota that don't support `suggested_area`, extract it from names like "Living Room / Plug"
- Works with Zigbee2MQTT, ESPHome, Tasmota, rtl_433, OpenMQTTGateway, Valetudo, and more

### Installation

Available via HACS (pending approval) or manual install:
https://github.com/MarkAtwood/ha-mqtt-device-sync

### Configuration

After install, add the integration and configure:
- Which fields to sync (area, name, or both)
- Whether to overwrite existing values
- Name parsing delimiters for Tasmota-style naming

## How It Works

Subscribes to the same MQTT discovery topics as HA, parses the `device` block, and updates the device registry via HA's internal APIs. Simple, no YAML, no restart required after config changes.

---

Hope this helps others who've been fighting this for years. PRs and issues welcome on GitHub.
