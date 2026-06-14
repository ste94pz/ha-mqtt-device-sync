"""Constants for MQTT Device Sync."""

DOMAIN = "mqtt_device_sync"

CONF_DISCOVERY_PREFIX = "discovery_prefix"
CONF_SYNC_AREA = "sync_area"
CONF_SYNC_NAME = "sync_name"
CONF_OVERWRITE_EXISTING = "overwrite_existing"
CONF_PARSE_AREA_FROM_NAME = "parse_area_from_name"
CONF_NAME_DELIMITERS = "name_delimiters"
CONF_CAPITALIZE_PARSED_NAME = "capitalize_parsed_name"

DEFAULT_DISCOVERY_PREFIX = "homeassistant"
DEFAULT_SYNC_AREA = True
DEFAULT_SYNC_NAME = False
DEFAULT_OVERWRITE_EXISTING = False
DEFAULT_PARSE_AREA_FROM_NAME = False
DEFAULT_NAME_DELIMITERS = " / , - "
DEFAULT_CAPITALIZE_PARSED_NAME = False
