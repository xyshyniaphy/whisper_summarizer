#!/bin/bash
# Pull Docker images from Docker Hub
#
# This script pulls pre-built production images from Docker Hub.
# Use this after running ./push.sh locally to deploy updated images to production.
#
# Usage: ./pull.sh [username]
# Default username: xyshyniaphy

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get username from argument or use default
DOCKER_USERNAME="${1:-xyshyniaphy}"

echo "========================================="
echo "Pulling Docker images from Docker Hub"
echo "Username: $DOCKER_USERNAME"
echo "========================================="
echo

# Images to pull (production deployment)
# Note: Runner is deployed separately on GPU machine
IMAGES=(
    "whisper_summarizer-frontend"
    "whisper_summarizer-server"
)

for image in "${IMAGES[@]}"; do
    target="${DOCKER_USERNAME}/${image}:latest"
    echo -e "${BLUE}[INFO]${NC} Pulling ${target}"
    if docker pull "${target}"; then
        echo -e "${GREEN}[SUCCESS]${NC} Pulled ${target}"
    else
        echo -e "${YELLOW}[WARNING]${NC} Failed to pull ${target}"
    fi
    echo
done

echo "========================================="
echo -e "${GREEN}Pull complete!${NC}"
echo "========================================="
echo
echo "To start services with the new images:"
echo "  ./stop_prd.sh"
echo "  ./start_prd.sh"
echo
echo "Or to restart a specific service:"
echo "  docker compose -f docker-compose.prod.yml up -d web"
echo "  docker compose -f docker-compose.prod.yml up -d server"
echo
