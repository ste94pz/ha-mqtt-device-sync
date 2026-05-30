# Integration Tests

End-to-end tests using Docker to run a real Home Assistant instance with MQTT broker.

## Requirements

- Docker
- Docker Compose

## Quick Start

```bash
./run-tests.sh
```

This will:
1. Build the test container
2. Start Mosquitto (MQTT broker)
3. Start Home Assistant (with the integration mounted)
4. Wait for HA to be ready
5. Run the integration tests
6. Clean up containers

## Options

```bash
# Run tests and keep containers running afterwards
./run-tests.sh --keep

# Just show Home Assistant logs (for debugging)
./run-tests.sh --logs

# Clean up containers
./run-tests.sh --clean
```

## Manual Testing

With `--keep`, you can:

- Access Home Assistant at http://localhost:8123
- Publish MQTT messages to `localhost:1883`
- Watch logs with `docker compose logs -f homeassistant`

### Manual MQTT Testing

```bash
# Install mosquitto clients
brew install mosquitto  # macOS
apt install mosquitto-clients  # Debian/Ubuntu

# Publish a discovery message
mosquitto_pub -h localhost -t "homeassistant/sensor/manual_test/config" -m '{
  "name": "Manual Test Sensor",
  "state_topic": "test/manual/state",
  "unique_id": "manual_test_unique",
  "device": {
    "identifiers": ["manual_test_device"],
    "name": "Manual Test Device",
    "suggested_area": "Office"
  }
}'

# Check HA logs for sync activity
docker compose logs -f homeassistant | grep mqtt_device_sync
```

## Test Structure

```
integration_tests/
├── docker-compose.yml    # Service definitions
├── Dockerfile.test       # Test runner container
├── mosquitto.conf        # MQTT broker config
├── run-tests.sh          # Main test script
├── config/               # Home Assistant config
│   └── configuration.yaml
└── tests/                # Test files
    ├── conftest.py       # Fixtures (HA client, MQTT client)
    └── test_e2e.py       # End-to-end tests
```

## What's Tested

- Integration setup via config flow
- Area sync from `suggested_area`
- Area auto-creation
- Multiple devices to same area
- Retry logic when device isn't immediately registered
- Unicode area names
- Rapid message handling
- Malformed payload handling (invalid JSON, missing fields)

## Troubleshooting

### HA Not Starting

Check logs:
```bash
docker compose logs homeassistant
```

Common issues:
- Port 8123 already in use
- Docker not running
- Permission issues with mounted volumes

### Tests Failing

1. Check if integration loaded:
   ```bash
   docker compose logs homeassistant | grep mqtt_device_sync
   ```

2. Check MQTT connectivity:
   ```bash
   docker compose exec homeassistant mosquitto_sub -h mosquitto -t '#' -v
   ```

3. Run with keep flag and manually verify:
   ```bash
   ./run-tests.sh --keep
   # Open http://localhost:8123 and check device registry
   ```
