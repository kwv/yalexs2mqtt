import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add current directory to sys.path
sys.path.append(os.getcwd())

# Mock config loading
with patch("builtins.open", create=True) as mock_open, patch(
    "json.load"
) as mock_json_load:
    mock_json_load.return_value = {
        "lock": {
            "serial": "ASDFGH1234",
            "bluetoothAddress": "0A:1B:2C:3D:4E:5F",
            "handshakeKey": "1798AF9EA2E0B3E86D94809A3483E716",
            "handshakeKeyIndex": 1,
        },
        "mqtt": {
            "broker_address": "127.0.0.1",
            "mqtt_user": "test",
            "mqtt_password": "test",
        },
    }
    from yalexs2mqtt import DisconnectedError, Yalexs2MqttBridge


@pytest.fixture
def mock_client():
    with patch("yalexs2mqtt.mqtt.Client") as mock:
        yield mock.return_value


@pytest.fixture
def mock_push_lock():
    with patch("yalexs2mqtt.PushLock") as mock:
        instance = mock.return_value
        instance.start = AsyncMock()
        instance.stop = AsyncMock()
        instance.lock = AsyncMock()
        instance.unlock = AsyncMock()
        instance.update = AsyncMock()
        instance.wait_for_first_update = AsyncMock()
        instance.register_callback = MagicMock()
        yield instance


@pytest.fixture
def mock_scanner():
    with patch("yalexs2mqtt.BleakScanner") as mock:
        instance = mock.return_value
        instance.start = AsyncMock()
        instance.stop = AsyncMock()
        yield instance


@pytest.fixture
def bridge(mock_client):
    # We need to mock open/json.load again for the class instantiation
    # if it loads config in init
    with patch("builtins.open", create=True), patch("json.load") as mock_json_load:
        mock_json_load.return_value = {
            "lock": {
                "serial": "ASDFGH1234",
                "bluetoothAddress": "0A:1B:2C:3D:4E:5F",
                "handshakeKey": "1798AF9EA2E0B3E86D94809A3483E716",
                "handshakeKeyIndex": 1,
            },
            "mqtt": {
                "broker_address": "127.0.0.1",
                "mqtt_user": "test",
                "mqtt_password": "test",
            },
        }
        return Yalexs2MqttBridge()


def test_on_mqtt_message_lock(bridge):
    message = MagicMock()
    message.payload.decode.return_value = "LOCK"
    bridge.on_mqtt_message(bridge.mqtt_client, None, message)
    assert bridge.mqtt_message == "LOCK"
    assert bridge.mqtt_command_event.is_set()


def test_on_mqtt_message_unlock(bridge):
    message = MagicMock()
    message.payload.decode.return_value = "UNLOCK"
    bridge.on_mqtt_message(bridge.mqtt_client, None, message)
    assert bridge.mqtt_message == "UNLOCK"
    assert bridge.mqtt_command_event.is_set()


def test_on_mqtt_connect(bridge):
    bridge.on_mqtt_connect(bridge.mqtt_client, None, {}, 0, None)
    bridge.mqtt_client.subscribe.assert_called_with("yalexs/ASDFGH1234/set")


def test_new_state_publishing(bridge):
    status_json = json.dumps(
        {
            "state": {"lock": "LOCKED"},
            "connection_info": {"rssi": -70},
            "last_updated": "2025-01-01T12:00:00",
        }
    )

    bridge.on_status_update(status_json)
    bridge.mqtt_client.publish.assert_called_with(
        "yalexs/ASDFGH1234/currentValue", status_json, retain=True
    )


@pytest.mark.asyncio
async def test_run_loop_lock_command(bridge, mock_push_lock, mock_scanner):
    # Simulate a LOCK command coming from MQTT
    original_wait = asyncio.wait

    call_count = 0

    async def side_effect_wait(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First wait, let's set the event
            bridge.mqtt_message = "LOCK"
            bridge.mqtt_command_event.set()
            return await original_wait(*args, **kwargs)
        else:
            # Break the loop
            raise Exception("Break Loop")

    with patch("asyncio.wait", side_effect=side_effect_wait), patch("sys.exit"):
        try:
            await bridge.run()
        except Exception as e:
            if str(e) != "Break Loop":
                raise e

    mock_push_lock.lock.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnected_error_handling(bridge, mock_push_lock, mock_scanner):
    # Simulate DisconnectedError
    mock_push_lock.start.side_effect = DisconnectedError("Disconnected")

    with patch("sys.exit") as mock_exit, patch(
        "yalexs2mqtt._LOGGER.critical"
    ) as mock_log:
        await bridge.run()

        mock_log.assert_called_with(
            "Disconnected Error: "
            "Disconnected. Check your handshakeKey and handshakeKeyIndex in config.json."
        )
        mock_exit.assert_called_with(1)
