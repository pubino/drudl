FROM python:3.14-slim-bookworm

WORKDIR /app

# Install dependencies for Chromium, VNC, and noVNC
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    supervisor \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Copy supervisor and startup configs
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose noVNC port
EXPOSE 6080

# Set display for Chrome and unbuffered Python output
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]
