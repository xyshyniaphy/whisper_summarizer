#!/bin/bash
# Production Startup Script for Whisper Summarizer
#
# This script starts production services on the API server:
# - Frontend (via nginx) - serves static files on port 3080
# - Backend API server (FastAPI) - handles API requests
# - PostgreSQL database - stores data
#
# ⚠️  IMPORTANT: This does NOT start the Runner!
# The Runner is a separate GPU worker that runs on a different machine.
# It connects to this server via SERVER_URL and RUNNER_API_KEY.
#
# Architecture:
#   [Production Server - This Script]
#     ├── Frontend (nginx) → Port 3080
#     ├── API Server (FastAPI) → Internal
#     └── PostgreSQL → Internal
#
#   [GPU Runner - Separate Machine]
#     ├── faster-whisper (GPU)
#     └── GLM API
#       └── Connects to: SERVER_URL (this server)
#
# Only port 3080 is exposed (HTTP for cloudflared tunnel)
#
# Usage: ./start_prd.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo "========================================"
echo " Whisper Summarizer - Production Start"
echo "========================================"
echo

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Use docker compose or docker-compose
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

log_success "Prerequisites check passed"

# Check .env file
if [ ! -f .env ]; then
    log_warning ".env file not found"
    echo
    echo "Please create .env file from template:"
    echo "  cp .env.prod .env"
    echo "  nano .env  # Edit with your production values"
    echo
    log_error "Cannot start without .env file"
    exit 1
fi

# Source .env to validate (without exposing values)
source .env

# Validate critical environment variables
log_info "Validating environment configuration..."

required_vars=(
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY"
    "SUPABASE_SERVICE_ROLE_KEY"
    "POSTGRES_PASSWORD"
    "RUNNER_API_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ] || [[ "${!var}" == *"change-this"* ]]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    log_error "The following required environment variables are missing or using default values:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo
    echo "Please edit .env file and set proper production values."
    exit 1
fi

log_success "Environment validation passed"

# Frontend is built in Docker container - no local check needed
log_info "Frontend will be built in Docker container"

# Create necessary directories
log_info "Creating data directories..."
mkdir -p data/transcribes 2>/dev/null || true
# Skip chmod if permission denied (files may be owned by root)
chmod 755 data/transcribes 2>/dev/null || log_warning "Could not set permissions on data/transcribes (may be owned by root)"
log_success "Data directories ready"

# Check if ports are already in use
log_info "Checking port 3080..."
if lsof -Pi :3080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_error "Port 3080 is already in use"
    echo
    echo "Please stop the service using port 3080 first:"
    echo "  ./stop_prd.sh"
    echo "  # or manually kill the process"
    exit 1
fi

# Pull pre-built images from Docker registry
log_info "Pulling pre-built Docker images from registry..."
log_info "This ensures you have the latest version from Docker Hub..."
echo ""
echo "Pulling images:"
echo "  → xyshyniaphy/whisper_summarizer-server:latest"
echo "  → xyshyniaphy/whisper_summarizer-frontend:latest"
echo "  → postgres:18-alpine"
echo "  → nginx:1.25-alpine"
echo ""

if ! $DOCKER_COMPOSE -f docker-compose.prod.yml pull; then
    log_error "Failed to pull images from Docker Hub"
    echo ""
    echo "Possible reasons:"
    echo "  - Network connectivity issues"
    echo "  - Docker Hub is unavailable"
    echo "  - Image names are incorrect"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check internet connection: ping hub.docker.com"
    echo "  2. Verify Docker is running: docker ps"
    echo "  3. Try manual pull: docker pull xyshyniaphy/whisper_summarizer-server:latest"
    exit 1
fi
echo ""
log_success "All images pulled successfully"

# Start services
log_info "Starting production services..."
echo

# Start in detached mode
$DOCKER_COMPOSE -f docker-compose.prod.yml up -d

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
echo

# Wait for PostgreSQL
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker exec whisper_postgres_prd pg_isready -U postgres -d whisper_summarizer &> /dev/null; then
        log_success "PostgreSQL is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    log_error "PostgreSQL failed to start"
    $DOCKER_COMPOSE -f docker-compose.prod.yml logs postgres
    exit 1
fi

# Wait for API server
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -sf http://localhost:3080/health &> /dev/null; then
        log_success "API server is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    log_error "API server failed to start"
    $DOCKER_COMPOSE -f docker-compose.prod.yml logs server
    exit 1
fi

echo
log_success "All services started successfully!"
echo

# Show status
echo "========================================"
echo " Service Status"
echo "========================================"
$DOCKER_COMPOSE -f docker-compose.prod.yml ps
echo

echo "========================================"
echo " Access Information"
echo "========================================"
echo "🌐 Application URL: http://localhost:3080"
echo
echo "Services:"
echo "  ✅ Frontend (nginx)      → http://localhost:3080/"
echo "  ✅ API Server            → http://localhost:3080/api/"
echo "  ✅ PostgreSQL            → Internal only"
echo
echo "To view logs:"
echo "  $DOCKER_COMPOSE -f docker-compose.prod.yml logs -f"
echo
echo "To stop services:"
echo "  ./stop_prd.sh"
echo
echo "========================================"
echo "⚠️  Next Steps:"
echo "========================================"
echo "1. Configure cloudflared tunnel to point to http://localhost:3080"
echo "2. Set up your domain DNS in Cloudflare"
echo "3. Test your application through the tunnel"
echo
log_success "Production startup complete!"

# Optional: Display recent logs
echo
log_info "Recent logs (last 20 lines):"
echo "========================================"
$DOCKER_COMPOSE -f docker-compose.prod.yml logs --tail=20
