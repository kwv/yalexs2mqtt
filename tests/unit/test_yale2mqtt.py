import os
import sys
from unittest.mock import patch

# Add current directory to sys.path
sys.path.append(os.getcwd())

# Mock the config loading before importing the module
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
    from yalexs2mqtt import Yalexs2MqttBridge


@patch("yalexs2mqtt.mqtt.Client")
def test_onStatusUpdate(mock_client_class):
    # Setup
    mock_client = mock_client_class.return_value
    mock_client.publish.return_value = None

    # Instantiate bridge
    # (will use mocked config from import time or we need to mock again if it reloads)
    # The class loads config in __init__, so we need to mock open/json.load again
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
        bridge = Yalexs2MqttBridge()

    bridge.on_status_update("LOCKED")
    bridge.mqtt_client.publish.assert_called_once_with(
        "yalexs/ASDFGH1234/currentValue", "LOCKED", retain=True
    )
