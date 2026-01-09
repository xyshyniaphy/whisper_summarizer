#!/bin/bash
# Build and Push Docker images to Docker Hub
# Usage: ./push.sh [username]
# Default username: xyshyniaphy

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get username from argument or use default
DOCKER_USERNAME="${1:-xyshyniaphy}"

echo "========================================="
echo "Build and Push Docker images to Docker Hub"
echo "Username: $DOCKER_USERNAME"
echo "========================================="
echo

# Build production images first
echo -e "${BLUE}[INFO]${NC} Building production images..."
echo
echo "Building: frontend and server"
echo "Note: runner and fastwhisper-base should be built separately"
echo
docker compose -f docker-compose.prod.yml build --no-cache frontend server

echo
echo -e "${GREEN}[SUCCESS]${NC} Build complete!"
echo

# Images to push (Server/Runner architecture)
IMAGES=(
    "whisper_summarizer-frontend"
    "whisper_summarizer-server"
    "whisper_summarizer-runner"
    "whisper-summarizer-fastwhisper-base"
)


function tag_and_push() {
    local image_name=$1
    local username=$2

    # Check if image exists
    if ! docker images "${image_name}:latest" --format "{{.Repository}}" | grep -q "${image_name}"; then
        echo -e "${YELLOW}⚠️  Image ${image_name}:latest not found, skipping...${NC}"
        echo
        return
    fi

    # Target image name
    local target="${username}/${image_name}"

    echo "🏷️  Tagging ${image_name}:latest -> ${target}:latest"
    docker tag "${image_name}:latest" "${target}:latest"

    echo "📤 Pushing ${target}:latest"
    docker push "${target}:latest"

    echo -e "${GREEN}✅ Pushed ${target}:latest${NC}"
    echo
}

# Push main images
echo "========================================="
echo "Pushing Server/Runner architecture images"
echo "========================================="
echo

for image in "${IMAGES[@]}"; do
    tag_and_push "$image" "$DOCKER_USERNAME"
done

echo "========================================="
echo -e "${GREEN}✅ All images pushed successfully!${NC}"
echo "========================================="
echo
echo "Images available at:"
echo "  https://hub.docker.com/u/${DOCKER_USERNAME}"
echo
echo "To pull these images on another machine:"
echo "  docker pull ${DOCKER_USERNAME}/whisper_summarizer-frontend:latest"
echo "  docker pull ${DOCKER_USERNAME}/whisper_summarizer-server:latest"
echo "  docker pull ${DOCKER_USERNAME}/whisper_summarizer-runner:latest"
echo "  docker pull ${DOCKER_USERNAME}/whisper-summarizer-fastwhisper-base:latest"
echo
