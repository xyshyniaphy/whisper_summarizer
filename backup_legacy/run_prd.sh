#!/bin/bash
# Production build and deployment script
# Builds images with lint checks included in Docker multi-stage builds

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Whisper Summarizer - Production Build${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${BLUE}Note: Lint checks run during Docker build${NC}"
echo -e "${BLUE}      Build will fail if linting fails${NC}"
echo ""

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}>>> $1${NC}"
    echo "----------------------------------------"
}

# Function to print success/error
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ========================================
# Step 1: Check Environment
# ========================================
print_section "Step 1: Checking Environment"

if [ ! -f .env ]; then
    print_warning ".env file not found!"
    print_warning "Please create .env with required variables:"
    echo "  SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY"
    echo "  DATABASE_URL, GLM_API_KEY"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Deployment cancelled."
    fi
else
    print_success ".env file found"
fi

# Validate required environment variables
source .env

missing_vars=()

if [ -z "$SUPABASE_URL" ]; then
    missing_vars+=("SUPABASE_URL")
fi

if [ -z "$SUPABASE_ANON_KEY" ]; then
    missing_vars+=("SUPABASE_ANON_KEY")
fi

if [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    missing_vars+=("SUPABASE_SERVICE_ROLE_KEY")
fi

if [ -z "$GLM_API_KEY" ]; then
    missing_vars+=("GLM_API_KEY")
fi

if [ ${#missing_vars[@]} -gt 0 ]; then
    print_error "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please set these variables in .env file"
    exit 1
fi

print_success "Environment variables validated"

# ========================================
# Step 2: Build Production Images (with lint stages)
# ========================================
print_section "Step 2: Building Production Images"

echo "Building backend with lint check (this may take several minutes)..."
if docker compose -f docker-compose.yml build backend; then
    print_success "Backend image built (lint passed)"
else
    print_error "Backend build failed. Check logs above for lint errors."
fi

echo "Building frontend with lint check (this may take several minutes)..."
if docker compose -f docker-compose.yml build frontend; then
    print_success "Frontend image built (lint passed)"
else
    print_error "Frontend build failed. Check logs above for lint errors."
fi

# ========================================
# Step 3: Start Production Services
# ========================================
print_section "Step 3: Starting Production Services"

echo "Stopping existing containers..."
docker compose -f docker-compose.yml down 2>/dev/null || true

echo "Starting production containers..."
if docker compose -f docker-compose.yml up -d; then
    print_success "Production services started"
else
    print_error "Failed to start services"
fi

# ========================================
# Step 4: Health Check
# ========================================
print_section "Step 4: Health Check"

echo "Waiting for services to be ready..."
sleep 5

# Check backend health (internal container - no port exposed)
FRONTEND_URL="http://localhost:${FRONTEND_PORT:-80}"

# Try up to 30 times (1 minute total)
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "Checking backend health ($ATTEMPT/$MAX_ATTEMPTS)... "

    if docker exec whisper_backend curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend is healthy!"
        break
    fi

    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        print_error "Backend health check failed. Check logs: docker compose logs backend"
    fi

    sleep 2
done

# Check frontend
echo "Checking frontend..."
if curl -sf "$FRONTEND_URL" > /dev/null 2>&1; then
    print_success "Frontend is accessible!"
else
    print_warning "Frontend check failed (may still be starting)"
fi

# ========================================
# Summary
# ========================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Production Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Services running:"
echo "  - Frontend & API: http://localhost:${FRONTEND_PORT:-80}"
echo "  - Backend:       internal only (accessed via nginx proxy)"
echo ""
echo "API endpoints are routed through nginx:"
echo "  http://localhost:${FRONTEND_PORT:-80}/api/*"
echo ""
echo "Useful commands:"
echo "  docker compose logs -f          # View all logs"
echo "  docker compose logs -f frontend  # View frontend logs"
echo "  docker compose logs -f backend   # View backend logs"
echo "  docker compose down             # Stop all services"
echo ""
