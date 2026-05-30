"""Fixtures for integration tests."""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

import aiohttp
import paho.mqtt.client as mqtt
import pytest
import pytest_asyncio
import websockets


HA_URL = os.environ.get("HA_URL", "http://localhost:8123")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))


class HomeAssistantClient:
    """Client for interacting with Home Assistant API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def wait_for_ready(self, timeout: int = 120) -> bool:
        """Wait for HA to be ready."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                # Use /api/onboarding which doesn't require auth on fresh install
                async with self._session.get(f"{self.base_url}/api/onboarding") as resp:
                    if resp.status == 200:
                        return True
            except aiohttp.ClientError:
                pass
            await asyncio.sleep(2)
        return False

    async def onboard(self) -> str:
        """Complete onboarding and get auth token."""
        client_id = f"{self.base_url}/"

        # Create owner account (step: user)
        async with self._session.post(
            f"{self.base_url}/api/onboarding/users",
            json={
                "client_id": client_id,
                "name": "Test User",
                "username": "test",
                "password": "testpassword123",
                "language": "en",
            },
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Failed to create user: {resp.status} - {text}")
            data = await resp.json()
            auth_code = data.get("auth_code")

        if not auth_code:
            raise RuntimeError("No auth_code returned from onboarding")

        # Exchange auth_code for access token
        async with self._session.post(
            f"{self.base_url}/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": client_id,
            },
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.token = data["access_token"]
            else:
                raise RuntimeError("Failed to exchange auth_code for token")

        # Complete remaining onboarding steps with auth
        headers = {"Authorization": f"Bearer {self.token}"}

        # Step: core_config
        async with self._session.post(
            f"{self.base_url}/api/onboarding/core_config",
            headers=headers,
            json={},
        ) as resp:
            if resp.status not in (200, 201):
                pass  # May already be done

        # Step: analytics
        async with self._session.post(
            f"{self.base_url}/api/onboarding/analytics",
            headers=headers,
            json={},
        ) as resp:
            if resp.status not in (200, 201):
                pass  # May already be done

        # Step: integration (skip default integrations)
        async with self._session.post(
            f"{self.base_url}/api/onboarding/integration",
            headers=headers,
            json={},
        ) as resp:
            if resp.status not in (200, 201):
                pass  # May already be done

        return self.token

    async def _request(
        self, method: str, endpoint: str, **kwargs
    ) -> dict[str, Any] | list | None:
        """Make authenticated request."""
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        headers["Content-Type"] = "application/json"

        async with self._session.request(
            method, f"{self.base_url}{endpoint}", headers=headers, **kwargs
        ) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise RuntimeError(f"API error {resp.status}: {text}")
            if resp.content_length and resp.content_length > 0:
                return await resp.json()
            return None

    async def get(self, endpoint: str) -> dict[str, Any] | list | None:
        return await self._request("GET", endpoint)

    async def post(
        self, endpoint: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any] | list | None:
        return await self._request("POST", endpoint, json=data)

    async def setup_mqtt_integration(self) -> bool:
        """Set up MQTT integration."""
        try:
            # Start config flow
            resp = await self.post(
                "/api/config/config_entries/flow",
                {"handler": "mqtt"},
            )
            flow_id = resp["flow_id"]

            # Complete with broker config
            await self.post(
                f"/api/config/config_entries/flow/{flow_id}",
                {"broker": MQTT_HOST, "port": MQTT_PORT},
            )
            return True
        except RuntimeError as e:
            if "already_configured" in str(e).lower():
                return True
            raise

    async def setup_mqtt_device_sync(self) -> bool:
        """Set up MQTT Device Sync integration."""
        try:
            # Start config flow
            resp = await self.post(
                "/api/config/config_entries/flow",
                {"handler": "mqtt_device_sync"},
            )
            flow_id = resp["flow_id"]

            # Complete flow (no config needed)
            await self.post(f"/api/config/config_entries/flow/{flow_id}", {})
            return True
        except RuntimeError as e:
            if "already_configured" in str(e).lower():
                return True
            raise

    async def _ws_call(self, msg_type: str) -> list[dict[str, Any]]:
        """Make a WebSocket call to Home Assistant."""
        ws_url = self.base_url.replace("http://", "ws://") + "/api/websocket"
        async with websockets.connect(ws_url) as ws:
            # Wait for auth_required
            msg = json.loads(await ws.recv())
            if msg.get("type") != "auth_required":
                raise RuntimeError(f"Expected auth_required, got {msg}")

            # Send auth
            await ws.send(json.dumps({
                "type": "auth",
                "access_token": self.token,
            }))

            # Wait for auth_ok
            msg = json.loads(await ws.recv())
            if msg.get("type") != "auth_ok":
                raise RuntimeError(f"Auth failed: {msg}")

            # Send request
            await ws.send(json.dumps({
                "id": 1,
                "type": msg_type,
            }))

            # Get response
            msg = json.loads(await ws.recv())
            if not msg.get("success"):
                raise RuntimeError(f"WebSocket call failed: {msg}")

            return msg.get("result", [])

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get all devices from registry via WebSocket."""
        return await self._ws_call("config/device_registry/list")

    async def get_areas(self) -> list[dict[str, Any]]:
        """Get all areas via WebSocket."""
        return await self._ws_call("config/area_registry/list")

    async def get_device_by_identifier(
        self, domain: str, identifier: str
    ) -> dict[str, Any] | None:
        """Find device by identifier."""
        devices = await self.get_devices()
        for device in devices:
            for id_domain, id_value in device.get("identifiers", []):
                if id_domain == domain and id_value == identifier:
                    return device
        return None

    async def get_area_by_name(self, name: str) -> dict[str, Any] | None:
        """Find area by name."""
        areas = await self.get_areas()
        for area in areas:
            if area.get("name") == name:
                # Normalize: add 'id' field from 'area_id' for test compatibility
                area["id"] = area.get("area_id")
                return area
        return None


class MQTTClient:
    """MQTT client for publishing discovery messages."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.client = mqtt.Client(client_id="test_publisher")

    def connect(self):
        self.client.connect(self.host, self.port, 60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish_discovery(
        self,
        component: str,
        object_id: str,
        config: dict[str, Any],
        prefix: str = "homeassistant",
    ):
        """Publish MQTT discovery message."""
        topic = f"{prefix}/{component}/{object_id}/config"
        payload = json.dumps(config)
        self.client.publish(topic, payload, retain=True)

    def clear_discovery(
        self,
        component: str,
        object_id: str,
        prefix: str = "homeassistant",
    ):
        """Clear MQTT discovery message."""
        topic = f"{prefix}/{component}/{object_id}/config"
        self.client.publish(topic, "", retain=True)


# Module-level storage so we only onboard/setup once
_cached_token: str | None = None
_mqtt_setup_done: bool = False
_mqtt_device_sync_setup_done: bool = False


@pytest_asyncio.fixture
async def ha_client():
    """Create and setup Home Assistant client with MQTT configured."""
    global _cached_token, _mqtt_setup_done, _mqtt_device_sync_setup_done

    async with HomeAssistantClient(HA_URL) as client:
        # Wait for HA to be ready
        assert await client.wait_for_ready(), "HA did not become ready"

        if _cached_token:
            # Reuse existing token
            client.token = _cached_token
        else:
            # First test - need to onboard
            try:
                token = await client.onboard()
                _cached_token = token
            except RuntimeError as e:
                # Already onboarded from a previous run - need fresh HA instance
                raise RuntimeError(
                    f"HA already onboarded but no cached token. "
                    f"Run 'podman-compose down -v' to reset. Error: {e}"
                )

        # Set up MQTT integration (required for mqtt_device_sync)
        if not _mqtt_setup_done:
            try:
                await client.setup_mqtt_integration()
                _mqtt_setup_done = True
                # Wait for MQTT integration to fully initialize
                await asyncio.sleep(3)
            except RuntimeError as e:
                if "already_configured" in str(e).lower():
                    _mqtt_setup_done = True
                else:
                    raise

        # Set up mqtt_device_sync integration
        if not _mqtt_device_sync_setup_done:
            try:
                await client.setup_mqtt_device_sync()
                _mqtt_device_sync_setup_done = True
                # Wait for integration to start subscribing
                await asyncio.sleep(2)
            except RuntimeError as e:
                if "already_configured" in str(e).lower():
                    _mqtt_device_sync_setup_done = True
                else:
                    raise

        yield client


@pytest.fixture
def mqtt_client():
    """Create MQTT client."""
    client = MQTTClient(MQTT_HOST, MQTT_PORT)
    client.connect()
    yield client
    client.disconnect()
