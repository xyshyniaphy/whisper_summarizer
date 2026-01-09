#!/bin/bash
# Production Status Script for Whisper Summarizer
#
# Shows the status of all production services
#
# Usage: ./status_prd.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Use docker compose or docker-compose
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

echo "========================================"
echo " Production Service Status"
echo "========================================"
echo

# Container status
echo "📦 Containers:"
echo "----------------------------------------"
$DOCKER_COMPOSE -f docker-compose.prod.yml ps
echo

# Resource usage
echo "💻 Resource Usage:"
echo "----------------------------------------"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
    $(docker ps -q --filter "name=whisper_.*_prd") 2>/dev/null || echo "No containers running"
echo

# Health checks
echo "🏥 Health Checks:"
echo "----------------------------------------"

# Check PostgreSQL
if docker exec whisper_postgres_prd pg_isready -U postgres -d whisper_summarizer &> /dev/null; then
    echo -e "  ✅ PostgreSQL: Healthy"
else
    echo -e "  ${RED}❌ PostgreSQL: Unhealthy${NC}"
fi

# Check API server
if curl -sf http://localhost:3080/health &> /dev/null; then
    echo -e "  ✅ API Server: Healthy"
else
    echo -e "  ${RED}❌ API Server: Unhealthy${NC}"
fi

# Check nginx
if docker exec whisper_nginx_prd wget --quiet --tries=1 --spider http://localhost/health &> /dev/null; then
    echo -e "  ✅ Nginx: Healthy"
else
    echo -e "  ${RED}❌ Nginx: Unhealthy${NC}"
fi

echo

# Recent logs (last 10 lines)
echo "📋 Recent Logs (Last 10 lines):"
echo "----------------------------------------"
$DOCKER_COMPOSE -f docker-compose.prod.yml logs --tail=10
echo

# Disk usage
echo "💾 Disk Usage:"
echo "----------------------------------------"
du -sh data/ 2>/dev/null || echo "No data directory found"
docker exec whisper_postgres_prd du -sh /var/lib/postgresql/data 2>/dev/null || echo "PostgreSQL data not accessible"
echo
