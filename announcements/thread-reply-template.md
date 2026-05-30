# Reply Template for Existing Threads

Use this for replying to old forum threads or GitHub issues where people asked for this feature.

---

## Short Version (for quick replies)

This is now possible with a custom integration: [MQTT Device Sync](https://github.com/MarkAtwood/ha-mqtt-device-sync)

It runs alongside HA's MQTT integration and applies `suggested_area` (and optionally device name) to the device registry whenever discovery messages arrive. Works with Zigbee2MQTT, ESPHome, Tasmota, rtl_433, and others.

Available via HACS or manual install.

---

## Longer Version (for detailed threads)

I built a custom integration that solves this: [MQTT Device Sync](https://github.com/MarkAtwood/ha-mqtt-device-sync)

**What it does:**
- Listens to MQTT discovery messages (same topics as HA)
- Extracts `suggested_area` and device name from the payload
- Updates the device registry via HA's internal APIs
- Auto-creates missing areas

**Bonus feature:** For sources like Tasmota that don't support `suggested_area`, it can parse the area from device names like "Kitchen / Coffee Maker" → area: Kitchen, name: Coffee Maker.

Works with Zigbee2MQTT, ESPHome, Tasmota, rtl_433, OpenMQTTGateway, Valetudo, IOTLink, room-assistant, and anything else using HA MQTT discovery.

Install via HACS (pending approval) or copy `custom_components/mqtt_device_sync` to your config directory.
