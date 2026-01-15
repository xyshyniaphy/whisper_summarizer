#!/bin/sh
# Start SSH tunnel for E2E testing
# Creates SOCKS5 proxy on localhost:3480

set -e

PRODUCTION_SERVER="${PRODUCTION_SERVER:-root@192.3.249.169}"
PROXY_PORT="${PROXY_PORT:-3480}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"

echo "Starting SSH tunnel to ${PRODUCTION_SERVER}..."
echo "SOCKS5 proxy will be available at localhost:${PROXY_PORT}"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "Error: SSH key not found at ${SSH_KEY}"
    exit 1
fi

# Create SSH tunnel with SOCKS5 proxy
# -D: Dynamic port forwarding (SOCKS5)
# -N: No remote command (just forwarding)
# -f: Fork to background
# -M: Control master for later termination
# -o: Control socket location
ssh -i "$SSH_KEY" \
    -D "$PROXY_PORT" \
    -N \
    -f \
    -M \
    -S /tmp/ssh-tunnel-e2e.sock \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    "$PRODUCTION_SERVER"

echo "SSH tunnel started successfully"
echo "Control socket: /tmp/ssh-tunnel-e2e.sock"
