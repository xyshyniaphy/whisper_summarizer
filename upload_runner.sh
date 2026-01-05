#!/bin/bash
set -euo pipefail

# ========================================
# upload_runner.sh - Build and Push Runner Image to Docker Hub
# ========================================
# This script builds the runner Docker image and pushes it to Docker Hub
#
# Usage:
#   ./upload_runner.sh [tag]
#
# Examples:
#   ./upload_runner.sh              # Push as :latest
#   ./upload_runner.sh v1.0.0       # Push as :v1.0.0 and :latest
#   ./upload_runner.sh test-123     # Push as :test-123 and :latest

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Docker Hub configuration
DOCKER_USERNAME="xyshyniaphy"
IMAGE_NAME="whisper-summarizer-runner"
IMAGE_FULL="${DOCKER_USERNAME}/${IMAGE_NAME}"

# Get tag from argument or use "latest"
TAG="${1:-latest}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Docker Runner Image Upload Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check if user is logged in to Docker Hub
echo -e "${YELLOW}Checking Docker Hub login status...${NC}"
if ! docker info | grep -q "Username: ${DOCKER_USERNAME}"; then
    echo -e "${YELLOW}You need to log in to Docker Hub${NC}"
    docker login
fi

echo -e "${GREEN}✓ Docker Hub authenticated${NC}"
echo ""

# Show build info
echo -e "${BLUE}Build Configuration:${NC}"
echo "  Image: ${IMAGE_FULL}"
echo "  Tag: ${TAG}"
echo "  Context: ./runner"
echo ""

# Confirm build
read -p "Continue with build and push? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Cancelled${NC}"
    exit 0
fi

# Build the image
echo -e "${YELLOW}Building Docker image...${NC}"
echo ""

docker build -t "${IMAGE_FULL}:${TAG}" \
    -f ./runner/Dockerfile \
    ./runner

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

echo ""

# Also tag as latest if the tag is not "latest"
if [ "$TAG" != "latest" ]; then
    echo -e "${YELLOW}Tagging as :latest...${NC}"
    docker tag "${IMAGE_FULL}:${TAG}" "${IMAGE_FULL}:latest"
fi

# Push the image
echo -e "${YELLOW}Pushing to Docker Hub...${NC}"
echo ""

docker push "${IMAGE_FULL}:${TAG}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Push successful${NC}"
else
    echo -e "${RED}✗ Push failed${NC}"
    exit 1
fi

# Also push latest if we tagged it
if [ "$TAG" != "latest" ]; then
    echo ""
    echo -e "${YELLOW}Pushing :latest tag...${NC}"
    docker push "${IMAGE_FULL}:latest"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Upload Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Image: ${IMAGE_FULL}:${TAG}"
echo ""
echo "To deploy on GPU server:"
echo "  1. Copy .env.runner to the server"
echo "  2. Fill in the required values"
echo "  3. Run: ./start_runner.sh"
echo ""
