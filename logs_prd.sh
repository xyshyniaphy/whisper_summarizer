#!/bin/bash
# Production Logs Script for Whisper Summarizer
#
# Shows logs from production services
#
# Usage: ./logs_prd.sh [service]
#   service: postgres|server|nginx|all (default: all)

# Colors for output
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Use docker compose or docker-compose
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

SERVICE=${1:-all}

case $SERVICE in
    postgres)
        echo -e "${BLUE}Showing PostgreSQL logs...${NC}"
        $DOCKER_COMPOSE -f docker-compose.prod.yml logs -f postgres
        ;;
    server)
        echo -e "${BLUE}Showing API server logs...${NC}"
        $DOCKER_COMPOSE -f docker-compose.prod.yml logs -f server
        ;;
    nginx)
        echo -e "${BLUE}Showing Nginx logs...${NC}"
        $DOCKER_COMPOSE -f docker-compose.prod.yml logs -f nginx
        ;;
    all|"")
        echo -e "${BLUE}Showing all service logs...${NC}"
        $DOCKER_COMPOSE -f docker-compose.prod.yml logs -f
        ;;
    *)
        echo -e "${YELLOW}Unknown service: $SERVICE${NC}"
        echo "Usage: $0 [postgres|server|nginx|all]"
        exit 1
        ;;
esac
