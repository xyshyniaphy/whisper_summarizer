#!/bin/bash
# Production Shutdown Script for Whisper Summarizer
#
# This script stops all production services gracefully
#
# Usage: ./stop_prd.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Banner
echo "========================================"
echo " Whisper Summarizer - Production Stop"
echo "========================================"
echo

# Use docker compose or docker-compose
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

# Check if services are running
if ! $DOCKER_COMPOSE -f docker-compose.prod.yml ps | grep -q "Up"; then
    log_warning "No production services are currently running"
    exit 0
fi

# Show current status
log_info "Current service status:"
echo
$DOCKER_COMPOSE -f docker-compose.prod.yml ps
echo

# Stop services
log_info "Stopping production services..."
echo

$DOCKER_COMPOSE -f docker-compose.prod.yml down

echo
log_success "All production services stopped"
echo

# Verify cleanup
log_info "Verifying cleanup..."
# Docker filter uses simple string matching, not regex
remaining_containers=$(docker ps -q --filter "name=whisper_" || true)

if [ -n "$remaining_containers" ]; then
    log_warning "Some containers are still running:"
    docker ps --filter "name=whisper_" --format "table {{.Names}}\t{{.Status}}"
    echo
    log_info "You can force remove them with:"
    echo "  docker stop \$(docker ps -q --filter \"name=whisper_\")"
    echo "  docker rm \$(docker ps -aq --filter \"name=whisper_\")"
else
    log_success "All containers cleaned up successfully"
fi

echo
log_success "Production shutdown complete!"
