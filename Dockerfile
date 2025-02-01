# Use an official Python runtime as a parent image
FROM python:3-slim AS base-image
RUN apt-get update
RUN apt-get install -y --no-install-recommends bluez bluetooth  
RUN python3 -m venv /venv
RUN useradd -m bluezuser \
 && adduser bluezuser sudo \
 && passwd -d bluezuser


FROM base-image AS build-image
# keep the build dependencies in a build specific image
RUN apt-get install -y --no-install-recommends build-essential libbluetooth-dev 
WORKDIR /app
RUN /venv/bin/pip install yalexs-ble paho-mqtt


FROM base-image AS runtime-image
# setup bluetooth permissions
COPY ./bluezuser.conf /etc/dbus-1/system.d/
RUN apt-get install -y --no-install-recommends dbus sudo


USER bluezuser

WORKDIR /app
COPY --from=build-image /venv /venv
COPY ./config/ /app/config/
COPY ./entrypoint.sh .
COPY ./yalexs2mqtt.py /app/
RUN chmod +x ./entrypoint.sh

CMD ["./entrypoint.sh"]
