# MQTT Device Sync

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/MarkAtwood/ha-mqtt-device-sync)](https://github.com/MarkAtwood/ha-mqtt-device-sync/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Home Assistant custom integration that syncs device metadata from MQTT discovery payloads to the device registry.

## Problem

Home Assistant's MQTT integration supports `suggested_area` in discovery payloads, but it only works on **first discovery**. Subsequent updates are ignored because HA "preserves user customizations."

This affects Zigbee2MQTT, rtl-haos, Tasmota, ESPHome, and every other MQTT-based integration.

## Solution

This integration runs alongside HA's MQTT integration, listens to discovery messages, and applies `suggested_area` (and optionally `name`) to the device registry using HA's internal APIs.

## Features

- **Sync `suggested_area`** - Update device areas from MQTT discovery
- **Sync device name** - Optionally update device names
- **Auto-create areas** - Missing areas are created automatically
- **Parse area from name** - Extract area from device names like "Living Room / Plug" or "Kitchen Motion"
- **Retry logic** - Handles devices that aren't immediately registered
- **Deduplication** - Ignores repeated messages with same values

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → Custom repositories
3. Add `https://github.com/MarkAtwood/ha-mqtt-device-sync` as an Integration
4. Search for "MQTT Device Sync" and install
5. Restart Home Assistant
6. Go to Settings → Devices & Services → Add Integration → MQTT Device Sync

### Manual

1. Copy `custom_components/mqtt_device_sync` to your `config/custom_components/` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration → MQTT Device Sync

## Configuration

After adding the integration, click Configure to set options:

| Option | Default | Description |
|--------|---------|-------------|
| Discovery prefix | `homeassistant` | MQTT discovery topic prefix |
| Sync area | ✓ | Update device area from `suggested_area` |
| Sync name | ✗ | Update device name from `name` |
| Overwrite existing | ✗ | Overwrite values even if already set |
| Parse area from name | ✗ | Extract area from device name (see below) |
| Name delimiters | ` / , - ` | Delimiters for parsing area from name |

## Parse Area from Device Name

For MQTT sources that don't support `suggested_area` (like Tasmota), you can extract the area from the device name itself.

### Delimiter-based Parsing

If your devices are named with a delimiter:
- `"Living Room / Plug"` → area: **Living Room**, name: **Plug**
- `"Kitchen - Ceiling Light"` → area: **Kitchen**, name: **Ceiling Light**

Configure delimiters as a comma-separated list. Default: ` / , - ` (space-slash-space and space-dash-space).

### Existing Area Matching

If no delimiter is found, the integration tries to match the start of the device name against your existing Home Assistant areas:

- `"Laundry Motion"` → area: **Laundry**, name: **Motion** (if "Laundry" area exists)
- `"Master Bedroom Fan"` → area: **Master Bedroom**, name: **Fan** (if "Master Bedroom" area exists)

Matching is case-insensitive and longest match wins (so "Living Room" matches before "Living").

## How It Works

1. Subscribes to `{prefix}/+/+/config` MQTT topics
2. Parses device info from discovery payloads
3. Looks up device in HA's device registry by identifiers
4. Updates area and/or name if configured
5. Creates missing areas automatically

### Timing

Discovery messages may arrive before HA registers the device. The integration retries up to 3 times with a 5-second delay.

### Deduplication

Repeated discovery messages with the same values are ignored to avoid spamming the device registry.

## Compatibility

Works with any MQTT discovery source:

- **Zigbee2MQTT** - Set `homeassistant.legacy_entity_attributes: false` and configure `suggested_area` in device settings
- **rtl-haos** - Uses `suggested_area` for auto-discovered sensors
- **Tasmota** - Use "Parse area from name" with naming convention like "Room / Device"
- **ESPHome** - Set `suggested_area` in device config

## Troubleshooting

Enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.mqtt_device_sync: debug
```

### Device not updating

1. Check that the MQTT discovery message includes a `device` dict with `identifiers`
2. Verify the device exists in HA's device registry
3. If "Overwrite existing" is off, only unset values will be updated

### Area not created

Areas are created automatically when `suggested_area` references a name that doesn't exist.

### Parse area not working

1. Ensure "Parse area from name" is enabled in options
2. Check your delimiter configuration
3. For existing area matching, the area must already exist in HA

## License

MIT
