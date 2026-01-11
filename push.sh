#!/bin/bash
# Build and Push Docker images to Docker Hub
#
# This script builds production Docker images locally and pushes them to Docker Hub.
# The frontend uses RUNTIME configuration (via entrypoint.sh), so credentials are
# NOT baked into the JavaScript bundle at build time.
#
# Runtime configuration workflow:
#   1. entrypoint.sh generates config.js at container startup from ENV vars
#   2. Supabase credentials are injected via docker-compose.prod.yml environment
#   3. Same image works across different environments (dev, staging, prod)
#
# Usage: ./push.sh [username]
# Default username: xyshyniaphy
#
# Workflow:
#   1. Run this script locally to build and push images
#   2. SSH to production server
#   3. Run ./pull.sh to download the new images
#   4. Restart services

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get username from argument or use default
DOCKER_USERNAME="${1:-xyshyniaphy}"

# Banner
echo "========================================="
echo "Build and Push to Docker Hub"
echo "Username: $DOCKER_USERNAME"
echo "========================================="
echo

# Check .env file
if [ ! -f .env ]; then
    echo -e "${RED}[ERROR]${NC} .env file not found"
    echo "Please create .env file from template:"
    echo "  cp .env.prod .env"
    echo "  nano .env  # Edit with your values"
    exit 1
fi

# Source .env with security (disable debug tracing)
set +x  # Disable debug tracing to prevent secret leakage
source .env
set -e  # Re-enable exit on error

# Validate required environment variables
echo -e "${BLUE}[INFO]${NC} Validating environment configuration..."
echo

required_vars=(
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo -e "${RED}[ERROR]${NC} The following required environment variables are missing:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo
    echo "Please edit .env file and set these values."
    exit 1
fi

echo -e "${GREEN}[SUCCESS]${NC} Environment validation passed"
echo

# ========================================
# Build Frontend (Production)
# ========================================
echo "========================================="
echo "Building Frontend"
echo "========================================="
echo -e "${BLUE}[INFO]${NC} Building production static build with nginx..."
echo -e "${BLUE}[INFO]${NC} Runtime configuration: credentials injected via ENV vars"
echo -e "${BLUE}[INFO]${NC} Supabase URL: ${SUPABASE_URL}"
echo -e "${BLUE}[INFO]${NC} Same image works across all environments (no credentials baked)"
echo

docker build -f frontend/Dockerfile.prod \
  -t ${DOCKER_USERNAME}/whisper_summarizer-frontend:latest \
  -t whisper_summarizer-frontend:latest \
  ./frontend

echo
echo -e "${GREEN}[SUCCESS]${NC} Frontend built successfully!"
echo

# Verify the build contains assets
echo -e "${BLUE}[INFO]${NC} Verifying build output..."
CONTAINER_ID=$(docker create ${DOCKER_USERNAME}/whisper_summarizer-frontend:latest)

echo "Static files in nginx root:"
docker exec $CONTAINER_ID ls -lh /usr/share/nginx/html/ 2>/dev/null | head -10

echo
echo "JavaScript bundle:"
docker exec $CONTAINER_ID ls -lh /usr/share/nginx/html/assets/*.js 2>/dev/null || echo "No JS files found!"

echo
echo "Entrypoint script (for runtime config):"
docker exec $CONTAINER_ID ls -lh /docker-entrypoint.sh 2>/dev/null || echo "Entrypoint not found!"

# Clean up temporary container
docker rm $CONTAINER_ID > /dev/null 2>&1

echo
echo -e "${GREEN}[VERIFIED]${NC} Frontend build output looks good!"
echo -e "${BLUE}[INFO]${NC} Runtime config will be injected at container startup"
echo

# ========================================
# Build Server
# ========================================
echo "========================================="
echo "Building Server"
echo "========================================="
echo -e "${BLUE}[INFO]${NC} Building FastAPI backend server..."
echo

docker build -f server/Dockerfile \
  -t ${DOCKER_USERNAME}/whisper_summarizer-server:latest \
  -t whisper_summarizer-server:latest \
  ./server

echo
echo -e "${GREEN}[SUCCESS]${NC} Server built successfully!"
echo

# ========================================
# Push Images
# ========================================
echo "========================================="
echo "Pushing Images to Docker Hub"
echo "========================================="
echo

IMAGES=(
    "whisper_summarizer-frontend"
    "whisper_summarizer-server"
)

for image in "${IMAGES[@]}"; do
    target="${DOCKER_USERNAME}/${image}:latest"
    echo -e "${BLUE}[INFO]${NC} Pushing ${target}"

    if docker push "${target}"; then
        echo -e "${GREEN}[SUCCESS]${NC} Pushed ${target}"
    else
        echo -e "${RED}[ERROR]${NC} Failed to push ${target}"
        exit 1
    fi
    echo
done

echo "========================================="
echo -e "${GREEN}Build and Push Complete!${NC}"
echo "========================================="
echo
echo "Images pushed to Docker Hub:"
echo "  ✅ ${DOCKER_USERNAME}/whisper_summarizer-frontend:latest"
echo "  ✅ ${DOCKER_USERNAME}/whisper_summarizer-server:latest"
echo
echo "To deploy to production server:"
echo "  1. SSH to production: ssh root@192.3.249.169"
echo "  2. Pull latest images: ./pull.sh"
echo "  3. Restart services: ./stop_prd.sh && ./start_prd.sh"
echo
echo "Or restart specific service:"
echo "  docker compose -f docker-compose.prod.yml pull web"
echo "  docker compose -f docker-compose.prod.yml up -d web"
echo
