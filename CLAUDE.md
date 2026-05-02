# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**yalexs2mqtt** is a BLE-to-MQTT bridge for Yale/August smart locks. It uses [yalexs-ble](https://github.com/bdraco/yalexs-ble) to connect to locks via Bluetooth and bridges commands/state to MQTT, making locks controllable from home automation systems like Home Assistant.

## Development Setup

```sh
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio flake8
```

## Commands

```sh
# Run tests
pytest

# Run a single test
pytest tests/unit/test_foo.py::test_specific_function

# Lint (only these error classes are enforced in CI)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Build Docker image locally
docker build -t yalexs2mqtt .
docker run -it --net=host --cap-add=NET_ADMIN -v ${PWD}/config:/app/config yalexs2mqtt
```

## Architecture

The entire application lives in a single file: `yalexs2mqtt.py` (~254 lines).

**Main flow:**
1. `Yalexs2MqttBridge` loads `config/config.json` into `LockConfig` and `MqttConfig` dataclasses
2. Connects to MQTT broker, subscribes to `yalexs/{SERIAL}/set` for commands (`LOCK`, `UNLOCK`, `UPDATE`)
3. Creates a `PushLock` (yalexs-ble) and `BleakScanner`, then starts BLE scanning
4. Registers `_new_state_callback` — fires on any lock state change, publishes JSON to `yalexs/{SERIAL}/currentValue` (retained)
5. Main loop polls for MQTT commands using `asyncio.Event` with 1s timeout
6. Health check HTTP server runs on `:8080/health` in a daemon thread

**MQTT topics:**
- Subscribe: `yalexs/{SERIAL}/set`
- Publish state: `yalexs/{SERIAL}/currentValue` (retained)
- Bridge availability: `yalexs/bridge/availability` (`online`/`offline`, retained)

**State JSON shape** (published on every lock state change):
```json
{
  "state": { "lock": "LOCKED", "door": "CLOSED", "battery": {...}, "auth": {...} },
  "connection_info": { "rssi": -72 },
  "last_updated": "2025-01-19T22:24:03.835916"
}
```
Enum values from yalexs-ble are serialized to their `.name` string via `_custom_asdict_factory`.

## Releasing

Push a semver tag to trigger CI build and Docker Hub publish:
```sh
git tag v1.2.3
git push origin v1.2.3
```

CI publishes `kwv4/yalexs2mqtt:v1.2.3` and `kwv4/yalexs2mqtt:latest` (multi-arch: `linux/amd64`, `linux/arm64`).

Required GitHub secrets: `DOCKERHUB_USER`, `DOCKERHUB_TOKEN`.
