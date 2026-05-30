# MQTT Device Sync - Automatic Area Assignment for MQTT-Discovered Devices

**TL;DR:** A custom integration that makes `suggested_area` in MQTT discovery actually work, even for devices that were already discovered.

---

## The Problem

If you use Zigbee2MQTT, Tasmota, rtl_433, or any other MQTT-based integration, you've probably noticed that the `suggested_area` field in MQTT discovery only works on *first* discovery. If you:

- Add area assignments to your Z2M config after devices are already in HA
- Delete and re-add a device
- Want to bulk-assign areas from your MQTT source

...Home Assistant ignores the `suggested_area` because it "preserves user customizations." This is by design ([core#162557](https://github.com/home-assistant/core/issues/162557)).

Native integrations like Z-Wave JS and ZHA don't have this problem - they can sync areas directly because they run inside HA. MQTT-based integrations are told to "use the WebSocket API" which is a significant implementation burden.

## The Solution

**mqtt_device_sync** is a small integration that:

1. Subscribes to MQTT discovery topics (`homeassistant/+/+/config`)
2. Extracts `suggested_area` from device payloads
3. Actually applies it to the device registry using HA's internal APIs

It works with any MQTT discovery source - no changes needed to Z2M, Tasmota, or your devices.

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Install "MQTT Device Sync"
3. Restart Home Assistant
4. Add the integration via Settings → Devices & Services

### Manual

Copy `custom_components/mqtt_device_sync` to your `config/custom_components/` directory.

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| Discovery prefix | `homeassistant` | MQTT discovery prefix (change if you customized it) |
| Sync areas | Yes | Apply `suggested_area` from discovery |
| Sync names | No | Apply device `name` from discovery |
| Overwrite existing | No | Update even if area/name already set |

## Usage with Zigbee2MQTT

In your Z2M `configuration.yaml`:

```yaml
devices:
  '0x00158d0001234567':
    friendly_name: living_room_motion
    homeassistant:
      device:
        suggested_area: 'Living Room'
```

Restart Z2M. The integration will pick up the discovery message and assign the device to "Living Room" - even if it was already discovered.

## Usage with Tasmota

In Tasmota console:

```
DeviceName Living Room Plug
```

Then configure MQTT discovery. The integration handles the rest.

## Usage with rtl_433 / rtl-haos

In your device mappings, include the `area` field - rtl-haos publishes this as `suggested_area` in discovery.

## Source

GitHub: [link]

## Feedback

This scratches my own itch - I have 50+ Z2M devices and a bunch of rtl_433 sensors, and manually assigning areas was tedious. Happy to take issues/PRs if you run into problems.
