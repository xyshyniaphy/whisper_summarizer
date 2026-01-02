#!/bin/bash
# Build script for fastwhisper base image
# This builds the base image containing CUDA cuDNN and faster-whisper model
# Build once, then backend builds will be much faster

set -e

IMAGE_NAME="whisper-summarizer-fastwhisper-base"
IMAGE_TAG="${1:-latest}"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

echo "======================================"
echo "Building fastwhisper base image"
echo "======================================"
echo "Image: ${FULL_IMAGE}"
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: docker not found. Please install Docker first."
    exit 1
fi

# Build the image
echo "Building ${FULL_IMAGE}..."
echo ""
docker build \
    -t "${FULL_IMAGE}" \
    -f fastwhisper/Dockerfile \
    .

echo ""
echo "======================================"
echo "Build complete!"
echo "======================================"
echo "Image: ${FULL_IMAGE}"
echo ""
echo "Image size:"
docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
echo ""
echo "To use this base image, backend/Dockerfile should start with:"
echo "  FROM ${FULL_IMAGE}"
echo ""
echo "To rebuild without cache:"
echo "  $0 --no-cache"
echo ""

# Tag as latest if not already
if [ "${IMAGE_TAG}" != "latest" ]; then
    docker tag "${FULL_IMAGE}" "${IMAGE_NAME}:latest"
    echo "Also tagged as ${IMAGE_NAME}:latest"
fi
