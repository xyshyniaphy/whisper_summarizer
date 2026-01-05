#!/bin/bash
set -euo pipefail

# ========================================
# start_runner.sh - Start Runner from Docker Hub
# ========================================
# This script pulls the latest runner image from Docker Hub and starts it
#
# Usage:
#   ./start_runner.sh [command]
#
# Commands:
#   up       - Start the runner (default)
#   down     - Stop the runner
#   restart  - Restart the runner
#   logs     - Show runner logs
#   update   - Pull latest image and restart
#   status   - Show runner status

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Docker Hub configuration
DOCKER_USERNAME="xyshyniaphy"
IMAGE_NAME="whisper-summarizer-runner"
IMAGE_FULL="${DOCKER_USERNAME}/${IMAGE_NAME}:latest"

# Compose file
COMPOSE_FILE="docker-compose.runner.prod.yml"
ENV_FILE=".env.runner"

# Get command (default: up)
COMMAND="${1:-up}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Whisper Summarizer Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if .env.runner exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: $ENV_FILE not found${NC}"
    echo ""
    echo "Please create $ENV_FILE with your configuration:"
    echo "  cp .env.runner $ENV_FILE"
    echo "  nano $ENV_FILE  # Edit with your values"
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
        echo -e "${YELLOW}Pulling latest image from Docker Hub...${NC}"
        docker pull "$IMAGE_FULL"
        echo ""

        echo -e "${YELLOW}Starting runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
        echo ""

        echo -e "${GREEN}✓ Runner started${NC}"
        echo ""
        echo "View logs: $0 logs"
        echo "Stop runner: $0 down"
        ;;

    down)
        echo -e "${YELLOW}Stopping runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
        echo -e "${GREEN}✓ Runner stopped${NC}"
        ;;

    restart)
        echo -e "${YELLOW}Restarting runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart
        echo -e "${GREEN}✓ Runner restarted${NC}"
        echo ""
        echo "View logs: $0 logs"
        ;;

    logs)
        echo -e "${YELLOW}Showing runner logs (Ctrl+C to exit)...${NC}"
        echo ""
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f
        ;;

    update)
        echo -e "${YELLOW}Pulling latest image...${NC}"
        docker pull "$IMAGE_FULL"
        echo ""

        echo -e "${YELLOW}Recreating runner with new image...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --force-recreate
        echo ""

        echo -e "${GREEN}✓ Runner updated and restarted${NC}"
        echo ""
        echo "View logs: $0 logs"
        ;;

    status)
        echo -e "${YELLOW}Runner status:${NC}"
        echo ""
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
        ;;

    *)
        echo -e "${RED}Error: Unknown command '$COMMAND'${NC}"
        echo ""
        echo "Available commands:"
        echo "  up       - Start the runner (default)"
        echo "  down     - Stop the runner"
        echo "  restart  - Restart the runner"
        echo "  logs     - Show runner logs"
        echo "  update   - Pull latest image and restart"
        echo "  status   - Show runner status"
        echo ""
        exit 1
        ;;
esac
