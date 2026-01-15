#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    echo -e "${BLUE}Development E2E Test Runner${NC}"
    echo ""
    echo "Usage: ./run_e2e_dev.sh [test_pattern]"
    echo ""
    echo "Note: Dev environment must be running (./run_dev.sh)"
    echo ""
}

TEST_PATTERN="${1:-}"

if [ ! -f "tests/docker-compose.test.yml" ]; then
    echo -e "${RED}Error: tests/docker-compose.test.yml not found${NC}"
    exit 1
fi

echo -e "${BLUE}=== Development E2E Test Runner ===${NC}"
echo "Test Pattern: ${TEST_PATTERN:-all tests}"
echo ""

TEST_CMD="bun run test"
[ -n "$TEST_PATTERN" ] && TEST_CMD="$TEST_CMD -- --grep \"$TEST_PATTERN\""

docker compose -f tests/docker-compose.test.yml run --rm e2e-test sh -c "$TEST_CMD"

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Development E2E tests passed!${NC}"
else
    echo -e "${RED}✗ Development E2E tests failed${NC}"
fi
exit $TEST_EXIT_CODE
