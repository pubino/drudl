FROM python:3.12-slim-bookworm

WORKDIR /app

# Install dependencies for Chrome, VNC, and noVNC
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    supervisor \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
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

# Set display for Chrome
ENV DISPLAY=:99

ENTRYPOINT ["/entrypoint.sh"]
