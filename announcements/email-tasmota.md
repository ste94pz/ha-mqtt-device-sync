**To:** Tasmota maintainers
**Subject:** HA integration for automatic area assignment - works with Tasmota via naming convention

---

Hi,

Quick heads up on a Home Assistant integration that helps with device organization.

**Problem:** Tasmota's native HA integration doesn't support area assignment. Users have to manually assign each device to a room in HA.

**Solution:** mqtt_device_sync - an HA integration that can parse area from device names using a convention:

```
"Living Room / Smart Plug"  →  area: Living Room, name: Smart Plug
"Kitchen / Ceiling Light"   →  area: Kitchen, name: Ceiling Light
```

Users just set their Tasmota DeviceName to follow this pattern. The integration handles the rest - creates the area if needed and assigns the device.

GitHub: [link]

No changes needed to Tasmota itself. Could be worth mentioning in the HA integration docs as a workaround for area assignment.

Cheers
