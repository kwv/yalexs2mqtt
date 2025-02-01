# yalexs2mqtt
BLE to MQTT Bridge for yale (August) locks.

Inspired by [aeozyalcin/August2MQTT](https://github.com/aeozyalcin/August2MQTT),  [yalexs-ble](https://github.com/bdraco/yalexs-ble) and [bluetooth in docker](https://medium.com/omi-uulm/how-to-run-containerized-bluetooth-applications-with-bluez-dced9ab767f6)


## Getting Started
1. Clone the repo, and start by modifying `config.example.json` file with the info for your lock as `config.json`. Follow the instructions [here](https://github.com/Friendly0Fire/augustpy#putting-it-all-together) to find the `handshakeKey` and `handshakeKeyIndex`. 

```
	"lock": [
		{
            "serial": "ASDFGH1234",
			"bluetoothAddress": "0A:1B:2C:3D:4E:5F",
			"handshakeKey": "1798AF9EA2E0B3E86D94809A3483E716",
			"handshakeKeyIndex": 1
		}
	]
```
2. enter your MQTT server details in the same `config.json` file. 

```
    "mqtt": {
        "broker_address": "192.168.0.192",
        "mqtt_user": "august",
        "mqtt_password": "lock"
    },
```

## Running in docker
`docker run -it  --net=host --cap-add=NET_ADMIN -v ${PWD}/config:/config  kwv4/yalexs2mqtt:latest`


## Building it locally

Building locally the docker image `docker build -t yalexs2mqtt .` and run it `docker run -it  --net=host --cap-add=NET_ADMIN -v ${PWD}/config:/config  yalexs2mqtt`.  If building cross platform (i.e. building on amd64, running on arm64 like a Raspberry Pi) follow 
 [multi-platform](https://docs.docker.com/build/building/multi-platform/#install-qemu-manually)


Things to know:
- The bridge will listen for MQTT topic `yalexs/{SERIAL}/set` to wait for `LOCK`, `UNLOCK`, `UPDATE` commands.  
- The bridge will publish to MQTT topic `yalexs/{SERIAL}/state`, when the lock reports a state change.


```json
{"state": {"lock": "LOCKED", "door": "CLOSED", "battery": {"voltage": 5.298, "percentage": 30}, "auth": {"successful": true}}, "connection_info": {"rssi": -72}, "last_updated": "2025-01-19T22:24:03.835916"}
```
https://github.com/bdraco/yalexs-ble/blob/main/src/yalexs_ble/const.py


### Troubleshooting

config.json `handshakeKey` or `handshakeKeyIndex` are wrong
```
yalexs2mqtt-1  |   File "/venv/lib/python3.13/site-packages/yalexs_ble/lock.py", line 246, in _setup_session
yalexs2mqtt-1  |     response = await self.secure_session.execute(
yalexs2mqtt-1  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
yalexs2mqtt-1  |         cmd, "SEC_LOCK_TO_MOBILE_KEY_EXCHANGE"
yalexs2mqtt-1  |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
yalexs2mqtt-1  |     )
yalexs2mqtt-1  |     ^
yalexs2mqtt-1  |   File "/venv/lib/python3.13/site-packages/yalexs_ble/session.py", line 268, in execute
yalexs2mqtt-1  |     async with interrupt(
yalexs2mqtt-1  |                ~~~~~~~~~^
yalexs2mqtt-1  |         disconnected_future, DisconnectedError, f"{self.name}: Disconnected"
yalexs2mqtt-1  |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
yalexs2mqtt-1  |     ):
yalexs2mqtt-1  |     ^
yalexs2mqtt-1  |   File "/venv/lib/python3.13/site-packages/async_interrupt/__init__.py", line 89, in __aexit__
yalexs2mqtt-1  |     raise self._exception(self._message) from exc_val
yalexs2mqtt-1  | yalexs_ble.session.DisconnectedError: 0A:1B:2C:3D:4E:5F: Disconnected
yalexs2mqtt-1  | 2025-01-19 21:34:52 CRITICAL An error occurred: 0A:1B:2C:3D:4E:5F: Disconnected
```