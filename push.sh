#!/bin/bash
# Push Docker images to Docker Hub
# Usage: ./push.sh [username]
# Default username: xyshyniaphy

set -e

# Get username from argument or use default
DOCKER_USERNAME="${1:-xyshyniaphy}"

echo "========================================="
echo "Pushing Docker images to Docker Hub"
echo "Username: $DOCKER_USERNAME"
echo "========================================="
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
        echo "⚠️  Image ${image_name}:latest not found, skipping..."
        return
    fi

    # Target image name
    local target="${username}/${image_name}"

    echo "🏷️  Tagging ${image_name}:latest -> ${target}:latest"
    docker tag "${image_name}:latest" "${target}:latest"

    echo "📤 Pushing ${target}:latest"
    docker push "${target}:latest"

    echo "✅ Pushed ${target}:latest"
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
echo "✅ All images pushed successfully!"
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
