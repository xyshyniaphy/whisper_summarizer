#!/bin/bash
set -euo pipefail

# ========================================
# start_runner.sh - Start Runner
# ========================================
# This script starts the GPU runner for processing audio
#
# Usage:
#   ./start_runner.sh [command]
#
# Commands:
#   up       - Start the runner (default)
#   down     - Stop the runner
#   restart  - Restart the runner
#   logs     - Show runner logs
#   build    - Build and start the runner
#   status   - Show runner status

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.runner.yml"
ENV_FILE="runner/.env"

# Get command (default: up)
COMMAND="${1:-up}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Whisper Summarizer Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if runner/.env exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: $ENV_FILE not found${NC}"
    echo ""
    echo "Please create $ENV_FILE with your configuration:"
    echo "  cp runner/.env.sample runner/.env"
    echo "  nano runner/.env  # Edit with your values"
    echo ""
    echo "Required values:"
    echo "  - SERVER_URL (your main server URL)"
    echo "  - RUNNER_API_KEY (must match server)"
    echo "  - GLM_API_KEY (your GLM API key)"
    echo ""
    exit 1
fi

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p data/runner logs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Check if docker compose is available
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    if ! docker-compose version &> /dev/null; then
        echo -e "${RED}Error: docker compose is not installed${NC}"
        exit 1
    fi
fi

# Execute command based on argument
case "$COMMAND" in
    up)
        echo -e "${YELLOW}Starting runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d
        echo ""

        echo -e "${GREEN}✓ Runner started${NC}"
        echo ""
        echo "View logs: $0 logs"
        echo "Stop runner: $0 down"
        echo "Build runner: $0 build"
        ;;

    down)
        echo -e "${YELLOW}Stopping runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" down
        echo -e "${GREEN}✓ Runner stopped${NC}"
        ;;

    restart)
        echo -e "${YELLOW}Restarting runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" restart
        echo -e "${GREEN}✓ Runner restarted${NC}"
        echo ""
        echo "View logs: $0 logs"
        ;;

    logs)
        echo -e "${YELLOW}Showing runner logs (Ctrl+C to exit)...${NC}"
        echo ""
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" logs -f
        ;;

    build)
        echo -e "${YELLOW}Building runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d --build
        echo ""
        echo -e "${GREEN}✓ Runner built and started${NC}"
        echo ""
        echo "View logs: $0 logs"
        ;;

    status)
        echo -e "${YELLOW}Runner status:${NC}"
        echo ""
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps
        ;;

    *)
        echo -e "${RED}Error: Unknown command '$COMMAND'${NC}"
        echo ""
        echo "Available commands:"
        echo "  up       - Start the runner (default)"
        echo "  down     - Stop the runner"
        echo "  restart  - Restart the runner"
        echo "  logs     - Show runner logs"
        echo "  build    - Build and start the runner"
        echo "  status   - Show runner status"
        echo ""
        exit 1
        ;;
esac
