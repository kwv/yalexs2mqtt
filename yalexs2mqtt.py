import sys
import asyncio
import logging
import json
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
from bleak import BleakScanner
from yalexs_ble import LockState, PushLock
from yalexs_ble.const import ConnectionInfo, LockInfo
from yalexs_ble.session import DisconnectedError

# Constants for configuration keys
CONFIG_LOCK = "lock"
CONFIG_MQTT = "mqtt"
LOCK_SERIAL_KEY = "serial"
LOCK_ADDRESS_KEY = "bluetoothAddress"
LOCK_KEY_KEY = "handshakeKey"
LOCK_KEY_INDEX_KEY = "handshakeKeyIndex"
MQTT_USER_KEY = "mqtt_user"
MQTT_PASSWORD_KEY = "mqtt_password"
MQTT_BROKER_ADDRESS_KEY = "broker_address"

# Set up logging
_LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger("yalexs_ble").setLevel(logging.INFO)
logging.getLogger("bleak_retry_connector").setLevel(logging.INFO)

@dataclass
class LockConfig:
    serial: str
    address: str
    key: str
    key_index: int

@dataclass
class MqttConfig:
    user: str
    password: str
    broker_address: str

class Yalexs2MqttBridge:
    def __init__(self, config_path: str = "config/config.json"):
        self.config = self._load_config(config_path)
        self.lock_config = self._parse_lock_config(self.config)
        self.mqtt_config = self._parse_mqtt_config(self.config)
        
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_command_event = asyncio.Event()
        self.mqtt_message: Optional[str] = None
        self.push_lock: Optional[PushLock] = None
        self.scanner: Optional[BleakScanner] = None

    def _load_config(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r") as config_file:
                return json.load(config_file)
        except FileNotFoundError:
            _LOGGER.fatal(f"Configuration file not found at {path}")
            sys.exit(1)
        except json.JSONDecodeError:
            _LOGGER.fatal(f"Invalid JSON in configuration file at {path}")
            sys.exit(1)

    def _parse_lock_config(self, config: Dict[str, Any]) -> LockConfig:
        try:
            lock_data = config[CONFIG_LOCK]
            return LockConfig(
                serial=lock_data[LOCK_SERIAL_KEY],
                address=lock_data[LOCK_ADDRESS_KEY],
                key=lock_data[LOCK_KEY_KEY],
                key_index=lock_data[LOCK_KEY_INDEX_KEY]
            )
        except KeyError as e:
            _LOGGER.fatal(f"Missing lock configuration key: {e}")
            sys.exit(1)

    def _parse_mqtt_config(self, config: Dict[str, Any]) -> MqttConfig:
        try:
            mqtt_data = config[CONFIG_MQTT]
            return MqttConfig(
                user=mqtt_data[MQTT_USER_KEY],
                password=mqtt_data[MQTT_PASSWORD_KEY],
                broker_address=mqtt_data[MQTT_BROKER_ADDRESS_KEY]
            )
        except KeyError as e:
            _LOGGER.fatal(f"Missing MQTT configuration key: {e}")
            sys.exit(1)

    def _custom_asdict_factory(self, data: Any) -> Dict[str, Any]:
        def convert_value(obj: Any) -> Any:
            if isinstance(obj, Enum):
                return obj.name
            return obj   
        return {k: convert_value(v) for k, v in data.__dict__.items()}

    def on_status_update(self, status: str) -> None:
        self.mqtt_client.publish(f"yalexs/{self.lock_config.serial}/currentValue", status, retain=True)
        _LOGGER.info(status)

    def on_mqtt_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        try:
            _LOGGER.info(f"New MQTT message received: {message.payload.decode()}")
            self.mqtt_message = message.payload.decode("utf-8")
            self.mqtt_command_event.set()
        except Exception as e:
            _LOGGER.error(f"Error processing MQTT message: {e}")

    def on_mqtt_connect(self, client: mqtt.Client, userdata: Any, flags: Dict[str, Any], reason_code: int, properties: Any) -> None:
        if reason_code == 0:
            client.subscribe(f"yalexs/{self.lock_config.serial}/set")
        else:
            _LOGGER.fatal(f"MQTT connection error: {reason_code}")
            sys.exit(1)

    async def setup_mqtt(self) -> None:
        self.mqtt_client.username_pw_set(self.mqtt_config.user, self.mqtt_config.password)
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.connect_async(self.mqtt_config.broker_address)
        self.mqtt_client.loop_start()
        self.mqtt_client.publish("yalexs/bridge/availability", "online", retain=True)

    def _new_state_callback(self, new_state: LockState, lock_info: LockInfo, connection_info: ConnectionInfo) -> None:
        state_json = json.dumps(new_state, default=self._custom_asdict_factory)
        connection_json = json.dumps(connection_info, default=self._custom_asdict_factory)
        merged_json = json.dumps({
            "state": json.loads(state_json),
            "connection_info": json.loads(connection_json),
            "last_updated": datetime.today().isoformat()
        })
        self.on_status_update(merged_json)

    async def run(self) -> None:
        await self.setup_mqtt()

        self.push_lock = PushLock(
            local_name=self.lock_config.serial,
            address=self.lock_config.address,
            key=self.lock_config.key,
            key_index=self.lock_config.key_index
        )
        self.scanner = BleakScanner(self.push_lock.update_advertisement)
        
        cancel_callback = self.push_lock.register_callback(self._new_state_callback)
        cancel_connect = None

        try:
            await self.scanner.start()
            cancel_connect = await self.push_lock.start()
            _LOGGER.info(
                "Started, waiting for lock to be discovered with local_name: %s",
                self.push_lock.local_name,
            )
            await self.push_lock.wait_for_first_update(10000)
            _LOGGER.info(
                "Connected - Keys are good: %s",
                self.push_lock.is_connected,
            )

            while True:
                done, pending = await asyncio.wait(
                    [asyncio.create_task(self.mqtt_command_event.wait())],
                    timeout=1.0,
                    return_when=asyncio.FIRST_COMPLETED
                )
                if self.mqtt_command_event.is_set():
                    if self.mqtt_message == "LOCK":
                        await self.push_lock.lock()
                    elif self.mqtt_message == "UNLOCK":
                        await self.push_lock.unlock()
                    elif self.mqtt_message == "UPDATE":
                        await self.push_lock.update()
                    else:
                        _LOGGER.error(f"Unknown command: {self.mqtt_message}")
                    self.mqtt_message = None
                    self.mqtt_command_event.clear()
        
        except DisconnectedError as e:
            _LOGGER.critical(f"Disconnected Error: {e}. Check your handshakeKey and handshakeKeyIndex in config.json.")
            sys.exit(1)
        except Exception as e:
            _LOGGER.fatal(f"An error occurred: {e}")
            sys.exit(1)
        finally:
            cancel_callback()
            if cancel_connect:
                cancel_connect()
            if self.scanner:
                await self.scanner.stop()
            _LOGGER.info("Cleanly exited.")

if __name__ == "__main__":
    bridge = Yalexs2MqttBridge()
    asyncio.run(bridge.run())