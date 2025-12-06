#!/bin/sh
set -e

# Start dbus
mkdir -p /var/run/dbus
dbus-daemon --system --fork
echo "Started dbus"

# Start bluetoothd
# Try to find bluetoothd path
if [ -x /usr/libexec/bluetooth/bluetoothd ]; then
    /usr/libexec/bluetooth/bluetoothd &
elif [ -x /usr/lib/bluetooth/bluetoothd ]; then
    /usr/lib/bluetooth/bluetoothd &
else
    echo "Could not find bluetoothd executable"
    exit 1
fi
echo "Started bluetoothd"

# Wait for services to settle
sleep 2

# Reset bluetooth adapter if hciconfig is available
if command -v hciconfig >/dev/null; then
    echo "Resetting hci0..."
    hciconfig hci0 down
    hciconfig hci0 up
    hciconfig
else
    echo "hciconfig not found, skipping adapter reset"
fi

# Start application
echo "Starting yalexs2mqtt..."
exec /venv/bin/python3 /app/yalexs2mqtt.py
