#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PRODUCTION_SERVER="${PRODUCTION_SERVER:-root@192.3.249.169}"
FRONTEND_URL="${FRONTEND_URL:-https://w.198066.xyz}"
PROXY_PORT="${PROXY_PORT:-3480}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"

show_help() {
    echo -e "${BLUE}Production E2E Test Runner${NC}"
    echo ""
    echo "Usage: ./run_e2e_prd.sh [options] [test_pattern]"
    echo ""
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -k, --grep PATTERN   Run tests matching pattern"
    echo "  -p, --proxy PORT     SOCKS5 proxy port (default: 3480)"
    echo "  -s, --server SERVER  SSH server (default: root@192.3.249.169)"
    echo "  -u, --url URL        Frontend URL (default: https://w.198066.xyz)"
    echo ""
}

TEST_PATTERN=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) show_help; exit 0 ;;
        -k|--grep) TEST_PATTERN="$2"; shift 2 ;;
        -p|--proxy) PROXY_PORT="$2"; shift 2 ;;
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
echo "Proxy Port: ${PROXY_PORT}"
echo "Test Pattern: ${TEST_PATTERN:-all tests}"
echo ""

echo -e "${YELLOW}Starting SSH tunnel...${NC}"
ssh -i "$SSH_KEY" -D "$PROXY_PORT" -N -f -M -S /tmp/ssh-tunnel-e2e.sock \
    -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
    "$PRODUCTION_SERVER"
echo -e "${GREEN}✓ SSH tunnel started (localhost:${PROXY_PORT})${NC}"

cleanup() {
    echo -e "${YELLOW}Stopping SSH tunnel...${NC}"
    ssh -S /tmp/ssh-tunnel-e2e.sock -O exit dummy 2>/dev/null || true
    rm -f /tmp/ssh-tunnel-e2e.sock
    echo -e "${GREEN}✓ SSH tunnel stopped${NC}"
}
trap cleanup EXIT

echo -e "${BLUE}Running E2E tests...${NC}"
export FRONTEND_URL="$FRONTEND_URL"
export PROXY_SERVER="socks5://localhost:${PROXY_PORT}"
export PRODUCTION_SERVER="$PRODUCTION_SERVER"

TEST_CMD="bun run test"
[ -n "$TEST_PATTERN" ] && TEST_CMD="$TEST_CMD -- --grep \"$TEST_PATTERN\""

docker compose -f tests/docker-compose.e2e.prd.yml run --rm --network host \
    -e FRONTEND_URL="$FRONTEND_URL" \
    -e PROXY_SERVER="socks5://localhost:${PROXY_PORT}" \
    -e PRODUCTION_SERVER="$PRODUCTION_SERVER" \
    e2e-test sh -c "$TEST_CMD"

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Production E2E tests passed!${NC}"
else
    echo -e "${RED}✗ Production E2E tests failed${NC}"
fi
exit $TEST_EXIT_CODE
