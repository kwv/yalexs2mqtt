# Use a minimal base image
FROM python:3.9-slim AS base-image

# Combine RUN instructions to reduce layers
RUN apt-get update && \
    apt-get install -y --no-install-recommends bluez sudo python3-venv && \
    python3 -m venv /venv && \
    adduser --disabled-password --gecos "" bluezuser && \
    adduser bluezuser sudo && \
    passwd -d bluezuser && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Build stage with build dependencies
FROM base-image AS build-image
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libbluetooth-dev && \
    /venv/bin/pip install --no-cache-dir yalexs-ble paho-mqtt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Runtime stage with runtime dependencies only
FROM base-image AS runtime-image
RUN apt-get update && \
    apt-get install -y --no-install-recommends dbus && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir /app && \
    chown -R bluezuser:bluezuser /app


# Set the working directory
WORKDIR /app

# Set the execute permission for entrypoint.sh
COPY ./entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

# Switch to the non-root user
USER bluezuser
# Copy the virtual environment and application files
COPY --from=build-image /venv /venv
COPY ./config/ /app/config/

COPY ./yalexs2mqtt.py /app/


# Use entrypoint to run the script
ENTRYPOINT ["/app/entrypoint.sh"]