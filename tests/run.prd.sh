#!/bin/bash
# ========================================
# Production Test Runner
# ========================================
# Runs backend tests against the production server
# via SSH + docker exec (localhost auth bypass).
#
# Usage:
#   ./tests/run.prd.sh                    # Run all tests
#   ./tests/run.prd.sh test_supabase_auth # Run specific test file
#   ./tests/run.prd.sh -k "auth_bypass"   # Run tests matching pattern
#   ./tests/run.prd.sh --coverage         # Run with coverage report
#
# Environment:
#   REMOTE_DEBUG_SERVER    SSH server (default: root@192.3.249.169)
#   REMOTE_DEBUG_CONTAINER Container name (default: whisper_server_prd)

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REMOTE_SERVER="${REMOTE_DEBUG_SERVER:-root@192.3.249.169}"
REMOTE_CONTAINER="${REMOTE_DEBUG_CONTAINER:-whisper_server_prd}"

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Check SSH connection
check_ssh_connection() {
    log_info "Checking SSH connection to $REMOTE_SERVER..."
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$REMOTE_SERVER" "echo 'SSH OK'" >/dev/null 2>&1; then
        log_success "SSH connection verified"
        return 0
    else
        log_error "Cannot connect to $REMOTE_SERVER"
        log_info "Please ensure:"
        log_info "  1. SSH key is configured"
        log_info "  2. Server is accessible"
        log_info "  3. Run: ssh-copy-id $REMOTE_SERVER"
        return 1
    fi
}

# Check production container
check_container() {
    log_info "Checking production container: $REMOTE_CONTAINER"
    if ssh "$REMOTE_SERVER" "docker ps --filter 'name=$REMOTE_CONTAINER' --format '{{.Names}}'" | grep -q "$REMOTE_CONTAINER"; then
        log_success "Container is running"
        return 0
    else
        log_error "Container not found or not running"
        return 1
    fi
}

# Build test image
build_test_image() {
    log_info "Building test Docker image..."
    cd "$SCRIPT_DIR"
    docker compose -f docker-compose.test.prd.yml build test-runner
}

# Start test container
start_test_container() {
    log_info "Starting test container..."
    cd "$SCRIPT_DIR"
    docker compose -f docker-compose.test.prd.yml up -d test-runner
    log_success "Test container started"
}

# Stop test container
stop_test_container() {
    log_info "Stopping test container..."
    cd "$SCRIPT_DIR"
    docker compose -f docker-compose.test.prd.yml down
    log_success "Test container stopped"
}

# Run tests
run_tests() {
    local pytest_args=("$@")

    log_info "Running tests against production server..."
    log_info "Server: $REMOTE_SERVER"
    log_info "Container: $REMOTE_CONTAINER"
    echo ""

    cd "$SCRIPT_DIR"

    # Run pytest in the test container (only integration tests)
    docker compose -f docker-compose.test.prd.yml --env-file ../.env run --rm \
        -e REMOTE_DEBUG_SERVER="$REMOTE_SERVER" \
        -e REMOTE_DEBUG_CONTAINER="$REMOTE_CONTAINER" \
        test-runner \
        pytest /app/tests/integration "${pytest_args[@]}" -v --tb=short
}

# Main flow
main() {
    echo ""
    echo "========================================"
    echo "  Production Test Runner"
    echo "========================================"
    echo ""

    # Pre-flight checks
    check_ssh_connection || exit 1
    check_container || exit 1

    # Build test image
    build_test_image

    # Start test container
    start_test_container

    # Trap to ensure cleanup
    trap stop_test_container EXIT INT TERM

    # Run tests
    run_tests "$@"

    # Cleanup happens via trap
}

# Show help if requested
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat << EOF
Production Test Runner - Run backend tests against production server

Usage:
  $0 [pytest_args...]

Examples:
  $0                          # Run all tests
  $0 test_supabase_auth       # Run specific test file
  $0 -k "auth_bypass"         # Run tests matching pattern
  $0 --coverage               # Run with coverage report
  $0 -v --tb=long             # Verbose with long tracebacks

Environment:
  REMOTE_DEBUG_SERVER    SSH server (default: root@192.3.249.169)
  REMOTE_DEBUG_CONTAINER Container name (default: whisper_server_prd)

Requirements:
  1. SSH access to production server
  2. Docker running locally
  3. SSH key configured (run: ssh-copy-id root@192.3.249.169)
EOF
    exit 0
fi

main "$@"
