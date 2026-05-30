#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "=== MQTT Device Sync Integration Tests ==="
echo ""

# Clean up any previous runs
cleanup() {
    echo ""
    echo "=== Cleaning up ==="
    docker compose down -v --remove-orphans 2>/dev/null || true
}

trap cleanup EXIT

# Parse arguments
KEEP_RUNNING=false
LOGS_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --keep)
            KEEP_RUNNING=true
            shift
            ;;
        --logs)
            LOGS_ONLY=true
            shift
            ;;
        --clean)
            cleanup
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--keep] [--logs] [--clean]"
            echo "  --keep   Keep containers running after tests"
            echo "  --logs   Show HA logs instead of running tests"
            echo "  --clean  Clean up containers and exit"
            exit 1
            ;;
    esac
done

# Build test runner
echo "=== Building test container ==="
docker compose build test-runner

# Start services
echo "=== Starting services ==="
docker compose up -d mosquitto homeassistant

# Wait for HA to be ready
echo "=== Waiting for Home Assistant to start ==="
echo "    This may take 1-2 minutes on first run..."

max_attempts=60
attempt=0
while ! curl -sf http://localhost:8123/api/ > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "ERROR: Home Assistant did not start in time"
        docker compose logs homeassistant
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo ""
echo "    Home Assistant is ready!"

if [ "$LOGS_ONLY" = true ]; then
    echo ""
    echo "=== Home Assistant Logs ==="
    docker compose logs -f homeassistant
    exit 0
fi

# Run tests
echo ""
echo "=== Running integration tests ==="
docker compose run --rm test-runner
test_result=$?

# Show HA logs on failure
if [ $test_result -ne 0 ]; then
    echo ""
    echo "=== Home Assistant Logs (last 100 lines) ==="
    docker compose logs --tail=100 homeassistant
fi

if [ "$KEEP_RUNNING" = true ]; then
    echo ""
    echo "=== Containers still running ==="
    echo "    Home Assistant: http://localhost:8123"
    echo "    MQTT Broker: localhost:1883"
    echo ""
    echo "    Run '$0 --clean' to stop"
    trap - EXIT  # Don't cleanup on exit
fi

exit $test_result
