# Use a minimal base image
FROM python:3.9-alpine AS base-image

# Combine RUN instructions to reduce layers
RUN apk update && \
    apk add --no-cache bluez bluetooth sudo && \
    python3 -m venv /venv && \
    adduser -D bluezuser && \
    adduser bluezuser wheel && \
    passwd -u bluezuser && \
    rm -rf /var/cache/apk/*

# Build stage with build dependencies
FROM base-image AS build-image
RUN apk update && \
    apk add --no-cache build-base libbluetooth-dev && \
    /venv/bin/pip install --no-cache-dir yalexs-ble paho-mqtt && \
    rm -rf /var/cache/apk/*

# Runtime stage with runtime dependencies only
FROM base-image AS runtime-image
RUN apk update && \
    apk add --no-cache dbus && \
    rm -rf /var/cache/apk/* && \
    mkdir /app && \
    chown -R bluezuser:bluezuser /app

# Switch to the non-root user
USER bluezuser

# Set the working directory
WORKDIR /app

# Copy the virtual environment and application files
COPY --from=build-image /venv /venv
COPY ./config/ /app/config/
COPY ./entrypoint.sh .
COPY ./yalexs2mqtt.py /app/

# Set the execute permission for entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Use entrypoint to run the script
ENTRYPOINT ["/app/entrypoint.sh"]