#!/bin/sh
# Frontend container entrypoint
# Injects runtime configuration into index.html from environment variables
# This allows the same Docker image to work across different environments

set -e

echo "[entrypoint] Injecting runtime configuration into index.html..."

# Replace placeholders in index.html with actual env vars
sed -i "s|\${VITE_SUPABASE_URL}|${VITE_SUPABASE_URL:-}|g" /usr/share/nginx/html/index.html
sed -i "s|\${VITE_SUPABASE_ANON_KEY}|${VITE_SUPABASE_ANON_KEY:-}|g" /usr/share/nginx/html/index.html
sed -i "s|\${VITE_BACKEND_URL:-/api}|${VITE_BACKEND_URL:-/api}|g" /usr/share/nginx/html/index.html

echo "[entrypoint] Configuration injected:"
echo "  VITE_SUPABASE_URL=${VITE_SUPABASE_URL:-<not set>}"
echo "  VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY:+<set>}"
echo "  VITE_BACKEND_URL=${VITE_BACKEND_URL:-/api}"

# Validate required variables
if [ -z "${VITE_SUPABASE_URL:-}" ] || [ -z "${VITE_SUPABASE_ANON_KEY:-}" ]; then
    echo "[entrypoint] WARNING: Missing Supabase configuration!"
    echo "[entrypoint] Supabase authentication may not work."
fi

echo "[entrypoint] Starting nginx..."
exec nginx -g 'daemon off;'
