# MQTT Device Sync

A Home Assistant custom integration that syncs device metadata from MQTT discovery payloads to the device registry.

## Problem

Home Assistant's MQTT integration supports `suggested_area` in discovery payloads, but it only works on **first discovery**. Subsequent updates are ignored because HA "preserves user customizations."

This affects Zigbee2MQTT, rtl-haos, Tasmota, ESPHome, and every other MQTT-based integration.

## Solution

This integration runs alongside HA's MQTT integration, listens to discovery messages, and applies `suggested_area` (and optionally `name`) to the device registry using HA's internal APIs.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → Custom repositories
3. Add `https://github.com/yourusername/ha-mqtt-device-sync` as an Integration
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
- **Tasmota** - Area assignment via `DeviceName` and templates
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

## License

MIT
