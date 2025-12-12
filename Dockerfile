# Build stage
FROM python:3-alpine AS build-image

WORKDIR /app

# Install build dependencies
# build-base: for compiling C extensions (gcc, musl-dev, etc.)
# bluez-dev: for bluetooth headers (if needed by bleak/dependencies)
# linux-headers: for kernel headers
RUN apk add --no-cache build-base bluez-dev linux-headers

# Create venv
RUN python3 -m venv /venv

# Install dependencies
COPY requirements.txt .
RUN /venv/bin/pip install --no-cache-dir --upgrade pip && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3-alpine AS runtime-image

LABEL maintainer="kwv4"
ARG VERSION=local
LABEL version="$VERSION"
LABEL description="A bluetooth bridge to MQTT for yale locks."
LABEL repository="https://github.com/kwv/yalexs2mqtt"

WORKDIR /app

# Install runtime dependencies
# bluez: for bluetooth stack
# bluez-deprecated: for hciconfig
# dbus: for inter-process communication
# sudo: for privilege escalation (if needed)
RUN apk add --no-cache bluez bluez-deprecated dbus sudo

# Setup Bluetooth permissions (copy config)
COPY ./bluezuser.conf /etc/dbus-1/system.d/

# Copy entrypoint
COPY ./entrypoint.sh .
RUN chmod +x ./entrypoint.sh

# Create user
RUN adduser -D bluezuser && \
    echo "bluezuser ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/bluezuser

# Copy venv from builder
COPY --from=build-image /venv /venv

# Copy application files
COPY ./config/ /app/config/
COPY ./yalexs2mqtt.py /app/

# Switch to user
USER bluezuser
EXPOSE 8080
CMD ["./entrypoint.sh"]
