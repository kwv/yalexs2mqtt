import sys
import paho.mqtt.client as mqtt
import asyncio
import logging

from bleak import BleakScanner

from yalexs_ble import LockState, PushLock
from yalexs_ble.const import ConnectionInfo, LockInfo
import json
from enum import Enum
from datetime import datetime

# Load configuration from JSON file
config = None
with open("config/config.json", "r") as config_file:
    config = json.load(config_file)

# Extract lock configuration
LOCK_SERIAL = config["lock"]["serial"]
LOCK_ADDRESS = config["lock"]["bluetoothAddress"]
LOCK_KEY = config["lock"]["handshakeKey"]
LOCK_KEY_INDEX = config["lock"]["handshakeKeyIndex"]

assert isinstance(LOCK_SERIAL, str)  # nosec
assert isinstance(LOCK_ADDRESS, str)  # nosec
assert isinstance(LOCK_KEY, str)  # type: ignore[unreachable] # nosec
assert isinstance(LOCK_KEY_INDEX, int)  # nosec

# Set up logging
_LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger("yalexs_ble").setLevel(logging.INFO)
logging.getLogger("bleak_retry_connector").setLevel(logging.INFO)

# Custom asdict factory to convert Enum values to their string representation
def custom_asdict_factory(data):
    def convert_value(obj):
        if isinstance(obj, Enum):
            return obj.name
        return obj   
    return {k: convert_value(v) for k, v in data.__dict__.items()}

# Initialize event for new MQTT commands
mqtt_command_event = asyncio.Event()
mqtt_message = None  # Initialize mqtt_message to None

def onStatusUpdate(status: json):
        client.publish(f"yalexs/{LOCK_SERIAL}/currentValue", status, retain=True)
        _LOGGER.info(status)
def on_message(client, userdata, message):
    global mqtt_message
    try:
        _LOGGER.info(f"New MQTT message received: {message.payload.decode()}")
        mqtt_message = message.payload.decode("utf-8")
        mqtt_command_event.set()
    except Exception as e:
        _LOGGER.error(f"Error processing MQTT message: {e}")
def on_mqtt_client_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe(f"yalexs/{LOCK_SERIAL}/set")
    else:
        _LOGGER.fatal(f"MQTT connection error: {reason_code}")
        sys.exit(1)

# Set up MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2) 
client.username_pw_set(config["mqtt"]["mqtt_user"],config["mqtt"]["mqtt_password"])
client.connect_async(config["mqtt"]["broker_address"])

client.publish("yalexs/bridge/availability", "online", retain=True)

client.on_message = on_message
client.on_connect = on_mqtt_client_connect
client.loop_start()


async def run():

    push_lock = PushLock(
        local_name=LOCK_SERIAL, address=LOCK_ADDRESS, key=LOCK_KEY, key_index=LOCK_KEY_INDEX
    )
    scanner = BleakScanner(push_lock.update_advertisement)

    def new_state(
        new_state: LockState, lock_info: LockInfo, connection_info: ConnectionInfo
    ) -> None:
        state_json = json.dumps(new_state, default=custom_asdict_factory)
       # lock_json = json.dumps(lock_info, default=custom_asdict_factory)
        connection_json = json.dumps(connection_info, default=custom_asdict_factory)
        merged_json = json.dumps({
            "state": json.loads(state_json),
            # "lock_info": json.loads(lock_json),
            "connection_info": json.loads(connection_json),
            "last_updated": datetime.today().isoformat()
        })
        onStatusUpdate(merged_json)

    cancel_callback = push_lock.register_callback(new_state)
    cancel = None  # Initialize cancel to None

    try:
        await scanner.start()
        cancel = await push_lock.start()
        _LOGGER.info(
            "Started, waiting for lock to be discovered with local_name: %s",
            push_lock.local_name,
        )
        await push_lock.wait_for_first_update(10000)
        _LOGGER.info(
            "Connected - Keys are good: %s",
            push_lock.is_connected,
        )

        while True:
            done, pending = await asyncio.wait(
                [asyncio.create_task(mqtt_command_event.wait())],
                timeout=1.0,  # Adjust the timeout as needed
                return_when=asyncio.FIRST_COMPLETED
            )
            if mqtt_command_event.is_set():
                global mqtt_message
                if mqtt_message == "LOCK":
                    await push_lock.lock()
                elif mqtt_message == "UNLOCK":
                    await push_lock.unlock()
                elif mqtt_message == "UPDATE":
                    await push_lock.update()
                else:
                    _LOGGER.error(f"Unknown command: {mqtt_message}")
                mqtt_message = None
                mqtt_command_event.clear()
    except Exception as e:
        _LOGGER.fatal(f"An error occurred: {e}")
    finally:
        cancel_callback()
        if cancel:
            cancel()
        await scanner.stop()
        _LOGGER.info("Cleanly exited.")
        sys.exit(1)



# Run the main function
asyncio.run(run())