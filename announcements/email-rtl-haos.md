**To:** jaronmcd (rtl-haos maintainer)
**Subject:** PR incoming: suggested_area support + companion HA integration

---

Hi,

I've been using rtl-haos and noticed the `device_mappings.json` already has an `area` field per device, but it's not wired into the MQTT discovery payload.

I'm planning to submit a PR that:
1. Reads the `area` field from device mappings
2. Includes it as `suggested_area` in the MQTT discovery device config

However, there's a catch: Home Assistant ignores `suggested_area` after first discovery. So I also built a companion HA integration (mqtt_device_sync) that subscribes to discovery and actually applies the area using HA's device registry API.

With both pieces:
- rtl-haos publishes `suggested_area` in discovery
- mqtt_device_sync applies it to the HA device registry
- Areas stay in sync, even for existing devices

GitHub (HA integration): [link]
PR for rtl-haos: [link when ready]

The rtl-haos change is minimal - just adding `suggested_area` to the device_registry dict in `mqtt_handler.py`. The HA integration handles the rest.

Let me know if you have questions or want to discuss the approach.

Cheers
