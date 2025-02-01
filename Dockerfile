# Use an official Python runtime as a parent image
FROM python:3-slim AS base-image
RUN apt-get update && \
    apt-get install -y --no-install-recommends bluez bluetooth sudo && \
    python3 -m venv /venv && \
    #     adduser --disabled-password --gecos "" bluezuser && \
    useradd -m bluezuser && \
    adduser bluezuser sudo && \
    passwd -d bluezuser  && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Build stage with build dependencies
FROM base-image AS build-image
WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libbluetooth-dev && \
    /venv/bin/pip install --no-cache-dir yalexs-ble paho-mqtt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


FROM base-image AS runtime-image
WORKDIR /app
# setup bluetooth permissions
COPY ./bluezuser.conf /etc/dbus-1/system.d/
 
COPY ./entrypoint.sh . 
RUN apt-get install -y --no-install-recommends dbus && \
    chmod +x ./entrypoint.sh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


USER bluezuser

COPY --from=build-image /venv /venv
COPY ./config/ /app/config/

COPY ./yalexs2mqtt.py /app/

CMD ["./entrypoint.sh"]
