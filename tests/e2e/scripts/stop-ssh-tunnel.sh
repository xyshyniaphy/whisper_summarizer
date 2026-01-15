#!/bin/sh
# Stop SSH tunnel for E2E testing

CONTROL_SOCKET="/tmp/ssh-tunnel-e2e.sock"

if [ -S "$CONTROL_SOCKET" ]; then
    echo "Stopping SSH tunnel..."
    ssh -S "$CONTROL_SOCKET" -O exit dummy 2>/dev/null || true
    rm -f "$CONTROL_SOCKET"
    echo "SSH tunnel stopped"
else
    echo "No SSH tunnel control socket found"
fi
