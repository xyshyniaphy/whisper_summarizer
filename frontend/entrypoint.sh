#!/bin/sh
# Frontend container entrypoint
# Generates config.js from environment variables at runtime
# This allows the same Docker image to work across different environments

set -e

echo "[entrypoint] Generating runtime configuration..."

# Generate config.js from environment variables (write to /tmp as non-root user)
cat > /tmp/config.js << EOF
// Runtime configuration generated at container startup
// These values are injected from environment variables

window.config = {
  VITE_SUPABASE_URL: '${VITE_SUPABASE_URL:-}',
  VITE_SUPABASE_ANON_KEY: '${VITE_SUPABASE_ANON_KEY:-}',
  VITE_BACKEND_URL: '${VITE_BACKEND_URL:-/api}'
};

console.log('[config] Runtime configuration loaded');
EOF

echo "[entrypoint] Configuration generated:"
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
