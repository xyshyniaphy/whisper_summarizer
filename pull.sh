#!/bin/bash
# Pull Docker images from Docker Hub
# Usage: ./pull.sh [username]
# Default username: xyshyniaphy

set -e

# Get username from argument or use default
DOCKER_USERNAME="${1:-xyshyniaphy}"

echo "========================================="
echo "Pulling Docker images from Docker Hub"
echo "Username: $DOCKER_USERNAME"
echo "========================================="
echo

# Images to pull (Server/Runner architecture)
IMAGES=(
    "whisper_summarizer-frontend"
    "whisper_summarizer-server"
    "whisper_summarizer-runner"
    "whisper-summarizer-fastwhisper-base"
)

for image in "${IMAGES[@]}"; do
    target="${DOCKER_USERNAME}/${image}:latest"
    echo "📥 Pulling ${target}"
    docker pull "${target}" || echo "⚠️  Failed to pull ${target}, skipping..."
    echo
done

echo "========================================="
echo "✅ All images pulled!"
echo "========================================="
echo
echo "To retag images for local use:"
echo "  docker tag ${DOCKER_USERNAME}/whisper_summarizer-frontend:latest whisper_summarizer-frontend:latest"
echo "  docker tag ${DOCKER_USERNAME}/whisper_summarizer-server:latest whisper_summarizer-server:latest"
echo "  docker tag ${DOCKER_USERNAME}/whisper_summarizer-runner:latest whisper_summarizer-runner:latest"
echo "  docker tag ${DOCKER_USERNAME}/whisper-summarizer-fastwhisper-base:latest whisper-summarizer-fastwhisper-base:latest"
