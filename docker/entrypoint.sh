#!/bin/bash

# Start supervisor (which manages Xvfb, fluxbox, x11vnc, noVNC)
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf &

# Wait for display to be ready
sleep 3

echo ""
echo "============================================"
echo "  noVNC is available at: http://localhost:6080"
echo "============================================"
echo ""
echo "Open the URL above in your browser to view"
echo "the Chrome window for CAS authentication."
echo ""

# Run drudl with any passed arguments
exec python /app/drudl "$@"
