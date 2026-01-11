#!/bin/bash
set -euo pipefail

# ========================================
# start_runner.prd.sh - Start Production Runner
# ========================================
# This script starts the GPU runner for processing audio
# Connects to the remote production server at w.198066.xyz
#
# Usage:
#   ./start_runner.prd.sh [command]
#
# Commands:
#   up       - Start the runner (default)
#   down     - Stop the runner
#   restart  - Restart the runner
#   logs     - Show runner logs
#   build    - Build and start the runner
#   push     - Build, push to registry, and start the runner
#   status   - Show runner status

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.runner.yml"
ENV_FILE=".env"

# Get command (default: up)
COMMAND="${1:-up}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Whisper Summarizer - Production Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: $ENV_FILE not found${NC}"
    echo ""
    echo "Please create $ENV_FILE with your configuration:"
    echo "  cp .env.sample .env"
    echo "  nano .env  # Edit with your values"
    echo ""
    exit 1
fi

# Load environment variables to check required values
if grep -q "^RUNNER_API_KEY=.*change-this" "$ENV_FILE" 2>/dev/null || ! grep -q "^RUNNER_API_KEY=" "$ENV_FILE" 2>/dev/null; then
    echo -e "${RED}Error: RUNNER_API_KEY not configured in .env${NC}"
    echo ""
    echo "The RUNNER_API_KEY must match the production server's API key."
    exit 1
fi

if ! grep -q "^GLM_API_KEY=" "$ENV_FILE" 2>/dev/null; then
    echo -e "${YELLOW}Warning: GLM_API_KEY may not be configured${NC}"
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

# Show production server configuration
if [ "$COMMAND" = "up" ] || [ "$COMMAND" = "status" ]; then
    SERVER_URL="${RUNNER_SERVER_URL:-https://w.198066.xyz}"
    echo -e "${BLUE}Production Server:${NC} $SERVER_URL"
    echo -e "${BLUE}Runner ID:${NC} ${RUNNER_ID:-runner-gpu-01}"
    echo ""
fi

# Execute command based on argument
case "$COMMAND" in
    up)
        echo -e "${YELLOW}Starting production runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d
        echo ""

        echo -e "${GREEN}✓ Production runner started${NC}"
        echo ""
        echo "View logs: $0 logs"
        echo "Stop runner: $0 down"
        echo "Build runner: $0 build"
        echo "Build & push: $0 push"
        echo ""
        echo "Runner connects to: $SERVER_URL/api/runner"
        ;;

    down)
        echo -e "${YELLOW}Stopping production runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" down
        echo -e "${GREEN}✓ Production runner stopped${NC}"
        ;;

    restart)
        echo -e "${YELLOW}Restarting production runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" restart
        echo -e "${GREEN}✓ Production runner restarted${NC}"
        echo ""
        echo "View logs: $0 logs"
        ;;

    logs)
        echo -e "${YELLOW}Showing production runner logs (Ctrl+C to exit)...${NC}"
        echo ""
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" logs -f
        ;;

    build)
        echo -e "${YELLOW}Building production runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d --build
        echo ""
        echo -e "${GREEN}✓ Production runner built and started${NC}"
        echo ""
        echo "View logs: $0 logs"
        ;;

    push)
        echo -e "${YELLOW}Building and pushing production runner to registry...${NC}"

        # Build the image
        echo -e "${BLUE}Step 1: Building image...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" build

        # Get the image name
        IMAGE_NAME="xyshyniaphy/whisper_summarizer-runner:latest"

        # Tag and push to registry
        echo -e "${BLUE}Step 2: Tagging image as $IMAGE_NAME${NC}"
        docker tag whisper-summarizer-runner:latest "$IMAGE_NAME" 2>/dev/null || true

        echo -e "${BLUE}Step 3: Pushing to Docker Hub...${NC}"
        docker push "$IMAGE_NAME"

        # Start the runner
        echo -e "${BLUE}Step 4: Starting runner...${NC}"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d

        echo ""
        echo -e "${GREEN}✓ Production runner built, pushed, and started${NC}"
        echo ""
        echo "Image: $IMAGE_NAME"
        echo "View logs: $0 logs"
        ;;

    status)
        echo -e "${YELLOW}Production runner status:${NC}"
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
        echo "  push     - Build, push to registry, and start the runner"
        echo "  status   - Show runner status"
        echo ""
        exit 1
        ;;
esac
