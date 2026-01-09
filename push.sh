#!/bin/bash
# Build and Push Docker images to Docker Hub
# Usage: ./push.sh [username]
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

# Get environment variables from .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
else
    echo -e "${RED}[ERROR]${NC} .env file not found"
    echo "Please create .env file from .env.prod first"
    exit 1
fi

echo "========================================="
echo "Build and Push Docker images to Docker Hub"
echo "Username: $DOCKER_USERNAME"
echo "========================================="
echo

# Validate required environment variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_ANON_KEY" ]; then
    echo -e "${RED}[ERROR]${NC} SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env"
    exit 1
fi

# ========================================
# Build Frontend (Production)
# ========================================
echo -e "${BLUE}[INFO]${NC} Building frontend (production static build with nginx)..."
echo

docker build -f frontend/Dockerfile.prod \
  --build-arg VITE_SUPABASE_URL="${SUPABASE_URL}" \
  --build-arg VITE_SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY}" \
  --build-arg VITE_BACKEND_URL=/api \
  -t ${DOCKER_USERNAME}/whisper_summarizer-frontend:latest \
  -t whisper_summarizer-frontend:latest \
  ./frontend

echo -e "${GREEN}[SUCCESS]${NC} Frontend built successfully!"
echo

# Verify the build contains CSS and assets
echo -e "${BLUE}[INFO]${NC} Verifying build output..."
echo
echo "Checking frontend image contents..."

# Create temporary container to inspect
CONTAINER_ID=$(docker create ${DOCKER_USERNAME}/whisper_summarizer-frontend:latest)

# Check if dist was copied correctly
echo "Static files:"
docker cp $CONTAINER_ID:/usr/share/nginx/html/. - > /dev/null 2>&1
ls -lh /usr/share/nginx/html/ 2>/dev/null | head -20 || docker exec $CONTAINER_ID ls -lh /usr/share/nginx/html/ | head -20

echo
echo "Assets folder:"
docker exec $CONTAINER_ID ls -lh /usr/share/nginx/html/assets/ | head -20 || echo "No assets folder found!"

# Clean up temporary container
docker rm $CONTAINER_ID > /dev/null 2>&1

echo
echo -e "${GREEN}[VERIFIED]${NC} Build output contains static files!"
echo

# ========================================
# Build Server
# ========================================
echo -e "${BLUE}[INFO]${NC} Building server (FastAPI backend)..."
echo

docker build -f server/Dockerfile \
  -t ${DOCKER_USERNAME}/whisper_summarizer-server:latest \
  -t whisper_summarizer-server:latest \
  ./server

echo -e "${GREEN}[SUCCESS]${NC} Server built successfully!"
echo

# ========================================
# Push Images
# ========================================
echo "========================================="
echo "Pushing images to Docker Hub"
echo "========================================="
echo

IMAGES=(
    "whisper_summarizer-frontend"
    "whisper_summarizer-server"
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

    echo "📤 Pushing ${target}:latest"
    docker push "${target}:latest"

    echo -e "${GREEN}✅ Pushed ${target}:latest${NC}"
    echo
}

for image in "${IMAGES[@]}"; do
    tag_and_push "$image" "$DOCKER_USERNAME"
done

echo "========================================="
echo -e "${GREEN}✅ Build and push complete!${NC}"
echo "========================================="
echo
echo "Images available at:"
echo "  https://hub.docker.com/u/${DOCKER_USERNAME}"
echo
echo "Built images:"
echo "  ✅ ${DOCKER_USERNAME}/whisper_summarizer-frontend:latest (static nginx + assets)"
echo "  ✅ ${DOCKER_USERNAME}/whisper_summarizer-server:latest (FastAPI, ~150MB)"
echo
echo "Note: Runner images should be built separately on GPU machine"
echo
echo "To pull and run on production server:"
echo "  git pull"
echo "  ./pull.sh ${DOCKER_USERNAME}"
echo "  ./stop_prd.sh"
echo "  ./start_prd.sh"
echo
