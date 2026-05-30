**To:** Koenkk (Z2M maintainer)
**Subject:** MQTT Device Sync - makes suggested_area work for existing devices

---

Hi,

I built a small Home Assistant integration that might be relevant to Z2M users.

**The problem:** HA's MQTT integration ignores `suggested_area` after first discovery. Users can set it in Z2M config, but if the device was already discovered, HA won't apply it. The HA team closed this as "not planned" and suggested MQTT integrations use the WebSocket API instead.

**The fix:** mqtt_device_sync subscribes to discovery topics and uses HA's internal device registry API to actually apply `suggested_area`. Works with existing Z2M setups - no changes needed on the Z2M side.

GitHub: [link]

This addresses the long-standing request in issue #19388. Users can now set areas in Z2M config and have them sync to HA, similar to how ZHA works natively.

Thought you might want to know about it, or mention it in the Z2M docs as a workaround. Happy to answer questions or take feedback.

Cheers
