#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PRODUCTION_SERVER="${PRODUCTION_SERVER:-root@192.3.249.169}"
LOCAL_PORT="${LOCAL_PORT:-8130}"
NGINX_PORT="${NGINX_PORT:-3080}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:${LOCAL_PORT}}"

show_help() {
    echo -e "${BLUE}Production E2E Test Runner (Direct SSH - Cloudflare Bypass)${NC}"
    echo ""
    echo "Usage: ./run_e2e_prd.sh [options] [test_pattern]"
    echo ""
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -k, --grep PATTERN   Run tests matching pattern"
    echo "  -l, --local-port PORT Local port for SSH forward (default: 8130)"
    echo "  -n, --nginx-port PORT Nginx port on server (default: 3080)"
    echo "  -s, --server SERVER  SSH server (default: root@192.3.249.169)"
    echo "  -u, --url URL        Frontend URL (default: http://localhost:\${LOCAL_PORT})"
    echo ""
    echo "This script uses SSH local port forwarding to bypass Cloudflare:"
    echo "  - Creates tunnel: localhost:${LOCAL_PORT} → server:localhost:${NGINX_PORT}"
    echo "  - Tests access http://localhost:${LOCAL_PORT} directly"
    echo "  - Server sees requests from 127.0.0.1 → auth bypass triggered"
    echo ""
}

TEST_PATTERN=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) show_help; exit 0 ;;
        -k|--grep) TEST_PATTERN="$2"; shift 2 ;;
        -l|--local-port) LOCAL_PORT="$2"; shift 2 ;;
        -n|--nginx-port) NGINX_PORT="$2"; shift 2 ;;
        -s|--server) PRODUCTION_SERVER="$2"; shift 2 ;;
        -u|--url) FRONTEND_URL="$2"; shift 2 ;;
        *) TEST_PATTERN="$1"; shift ;;
    esac
done

if [ ! -f "tests/docker-compose.e2e.prd.yml" ]; then
    echo -e "${RED}Error: tests/docker-compose.e2e.prd.yml not found${NC}"
    exit 1
fi

if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}Error: SSH key not found at ${SSH_KEY}${NC}"
    exit 1
fi

echo -e "${BLUE}=== Production E2E Test Runner ===${NC}"
echo "Frontend URL: ${FRONTEND_URL}"
echo "Production Server: ${PRODUCTION_SERVER}"
echo "SSH Port Forward: localhost:${LOCAL_PORT} → server:localhost:${NGINX_PORT}"
echo "Test Pattern: ${TEST_PATTERN:-all tests}"
echo ""

echo -e "${YELLOW}Starting SSH tunnel (local port forward)...${NC}"
ssh -i "$SSH_KEY" -L "${LOCAL_PORT}:localhost:${NGINX_PORT}" -N -f -M -S /tmp/ssh-tunnel-e2e.sock \
    -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
    "$PRODUCTION_SERVER"
echo -e "${GREEN}✓ SSH tunnel started (localhost:${LOCAL_PORT} → server:localhost:${NGINX_PORT})${NC}"

cleanup() {
    echo -e "${YELLOW}Cleaning up...${NC}"

    # Stop SSH tunnel
    ssh -S /tmp/ssh-tunnel-e2e.sock -O exit dummy 2>/dev/null || true
    rm -f /tmp/ssh-tunnel-e2e.sock
    echo -e "${GREEN}✓ SSH tunnel stopped${NC}"

    # Cleanup test transcription state file
    if [ -f "/tmp/e2e-test-transcription.json" ]; then
        echo -e "${YELLOW}Cleaning up test transcription state...${NC}"
        rm -f /tmp/e2e-test-transcription.json
        echo -e "${GREEN}✓ Test transcription state removed${NC}"
    fi
}
trap cleanup EXIT INT TERM

echo -e "${BLUE}Running E2E tests...${NC}"
export FRONTEND_URL="$FRONTEND_URL"
export PRODUCTION_SERVER="$PRODUCTION_SERVER"

TEST_CMD="bun run test"
[ -n "$TEST_PATTERN" ] && TEST_CMD="$TEST_CMD -- --grep \"$TEST_PATTERN\""

docker compose -f tests/docker-compose.e2e.prd.yml run --rm \
    -e FRONTEND_URL="$FRONTEND_URL" \
    -e PRODUCTION_SERVER="$PRODUCTION_SERVER" \
    e2e-test sh -c "$TEST_CMD"

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Production E2E tests passed!${NC}"
else
    echo -e "${RED}✗ Production E2E tests failed${NC}"
fi
exit $TEST_EXIT_CODE
