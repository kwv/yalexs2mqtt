# Use an official Python runtime as a parent image
FROM python:3-slim AS base-image
RUN apt-get update && \
    apt-get install -y --no-install-recommends bluez bluetooth sudo && \
    python3 -m venv /venv && \
    useradd -m bluezuser && \
    adduser bluezuser sudo && \
    passwd -d bluezuser && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Build stage with build dependencies
FROM base-image AS build-image
WORKDIR /app

# Install system build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libbluetooth-dev && \
    /venv/bin/pip install --no-cache-dir --upgrade pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY ./requirements.txt /app/requirements.txt
RUN /venv/bin/pip install --no-cache-dir -r /app/requirements.txt


# Runtime stage
FROM base-image AS runtime-image
WORKDIR /app

# Setup Bluetooth permissions
COPY ./bluezuser.conf /etc/dbus-1/system.d/

# Copy entrypoint script and set permissions
COPY ./entrypoint.sh .
RUN apt-get install -y --no-install-recommends dbus && \
    chmod +x ./entrypoint.sh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER bluezuser

# Copy virtual environment from build stage
COPY --from=build-image /venv /venv

# Copy application files
COPY ./config/ /app/config/
COPY ./yalexs2mqtt.py /app/

CMD ["./entrypoint.sh"]