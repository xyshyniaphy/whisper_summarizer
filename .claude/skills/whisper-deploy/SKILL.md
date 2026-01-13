---
name: whisper-deploy
description: Deploy Whisper Summarizer to production. Build images locally, push to Docker Hub, and deploy to production server. Includes server info, deployment workflow, quick deploy script, and troubleshooting.
---

# whisper-deploy - Production Deployment

## Purpose

Automates deployment of Whisper Summarizer to production server:
- **Build locally** - Images built on local machine (production server is low-spec)
- **Push to registry** - Docker Hub for distribution
- **Deploy to production** - Pull and restart services on remote server

## Quick Start

```bash
# Full deployment (build, push, deploy)
/whisper-deploy

# Quick one-liner
docker build -t xyshyniaphy/whisper_summarizer-server:latest -f server/Dockerfile server && \
docker push xyshyniaphy/whisper_summarizer-server:latest && \
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169 "cd /root/whisper_summarizer && git pull && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d"
```

## Server Configuration

**Location**: `ssh -i ~/.ssh/id_ed25519 root@192.3.249.169`
**SSH Key**: `~/.ssh/id_ed25519`
**Project Path**: `/root/whisper_summarizer`
**URL**: https://w.198066.xyz

**IMPORTANT**: Production server is **low spec** - DO NOT build images on production server.

### Container Names

| Container | Name | Image |
|-----------|------|-------|
| Server | `whisper_server_prd` | xyshyniaphy/whisper_summarizer-server:latest |
| Frontend | `whisper_web_prd` | xyshyniaphy/whisper_summarizer-frontend:latest |
| PostgreSQL | `whisper_postgres_prd` | postgres:18-alpine |
| Nginx | `whisper_nginx_prd` | nginx:alpine |

**Note**: Runner is NOT deployed to production server - it runs on separate GPU machine.

## What to Deploy

| Service | Deploy to Production? | Notes |
|---------|----------------------|-------|
| Frontend | ✅ Yes | Static files, lightweight (~20MB) |
| Server | ✅ Yes | API server, lightweight (~150MB) |
| Runner | ❌ NO | Runner runs on separate GPU machine via SERVER_URL |

## Deployment Workflow

### Step 1: Build Images Locally

Build Docker images on your local machine (NOT on production server):

```bash
# Build server image
docker build -t xyshyniaphy/whisper_summarizer-server:latest -f server/Dockerfile server

# Build frontend image
docker build -t xyshyniaphy/whisper_summarizer-frontend:latest -f frontend/Dockerfile.prod frontend
```

### Step 2: Push to Docker Hub

```bash
# Push both images
docker push xyshyniaphy/whisper_summarizer-server:latest
docker push xyshyniaphy/whisper_summarizer-frontend:latest
```

### Step 3: Deploy to Production

Connect to production server and pull latest images:

```bash
# SSH to production server
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169

# Change to project directory
cd /root/whisper_summarizer

# Pull latest code
git pull

# Pull and restart services
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# View logs to verify
docker compose -f docker-compose.prod.yml logs -f server
```

## Deploy Individual Services

### Server Only

```bash
# Local
docker build -t xyshyniaphy/whisper_summarizer-server:latest -f server/Dockerfile server
docker push xyshyniaphy/whisper_summarizer-server:latest

# Production
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169 "cd /root/whisper_summarizer && docker compose -f docker-compose.prod.yml pull server && docker compose -f docker-compose.prod.yml up -d server"
```

### Frontend Only

```bash
# Local
docker build -t xyshyniaphy/whisper_summarizer-frontend:latest -f frontend/Dockerfile.prod frontend
docker push xyshyniaphy/whisper_summarizer-frontend:latest

# Production
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169 "cd /root/whisper_summarizer && docker compose -f docker-compose.prod.yml pull web && docker compose -f docker-compose.prod.yml up -d web"
```

## Production API Testing

Server container uses `python:3.12-slim` (lightweight, no curl). Use Python standard library `urllib.request` for HTTP testing.

### From Local Machine

```bash
# Check health status
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169 "docker exec whisper_server_prd python -c \"import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').status)\""

# Get transcriptions (formatted JSON)
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169 "docker exec whisper_server_prd python -c \"import urllib.request, json; data=json.loads(urllib.request.urlopen('http://localhost:8000/api/transcriptions').read().decode()); print(json.dumps(data, indent=2))\""
```

### From Production Server

```bash
# SSH to server
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169

# Quick health check
docker exec whisper_server_prd python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').status)"

# Check response headers
docker exec whisper_server_prd python -c "import urllib.request; response=urllib.request.urlopen('http://localhost:8000/api/shared/xxx/download?format=txt'); print(dict(response.headers))"

# Test status code only
docker exec whisper_server_prd python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/transcriptions').status)"
```

## Debugging on Production

### Check Container Status

```bash
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169
docker ps -a
```

### View Logs

```bash
# Server logs
docker logs whisper_server_prd --tail=100

# Follow logs in real-time
docker logs -f whisper_server_prd

# Frontend logs
docker logs whisper_web_prd --tail=100

# Nginx logs
docker logs whisper_nginx_prd --tail=100
```

### Restart Services

```bash
# Restart all services
cd /root/whisper_summarizer
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart server
docker compose -f docker-compose.prod.yml restart web
```

### Database Access

```bash
# Interactive psql shell
docker exec -it whisper_postgres_prd psql -U postgres -d whisper_summarizer

# Run single query
docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c "SELECT * FROM transcriptions LIMIT 5;"
```

## Troubleshooting

### DELETE 500 Error

**Symptoms**: DELETE requests return 500 error

**Diagnosis**:
```bash
docker logs whisper_server_prd | grep -i recursion
```

**Cause**: Usually caused by function calling itself instead of getting user ID (recursive bug)

**Solution**: Fix the recursive function call in code

### Container Unhealthy

**Symptoms**: Docker shows container as "unhealthy" or constantly restarting

**Diagnosis**:
```bash
docker ps
docker logs whisper_server_prd --tail=100
```

**Common causes**:
- Database not ready when server starts
- Environment variable misconfiguration
- Port conflicts

**Solution**:
```bash
# Check database is ready
docker logs whisper_postgres_prd

# Restart server after database is up
docker compose -f docker-compose.prod.yml restart server
```

### Images Not Updating

**Symptoms**: Deployed code doesn't match expected changes

**Diagnosis**:
```bash
# Check current image digest
docker images | grep whisper_summarizer
```

**Solutions**:
```bash
# 1. Ensure you pushed to Docker Hub
docker push xyshyniaphy/whisper_summarizer-server:latest

# 2. Pull with specific digest
docker pull xyshyniaphy/whisper_summarizer-server:latest@sha256:...

# 3. Force recreate container
docker compose -f docker-compose.prod.yml up -d --force-recreate server
```

### Out of Disk Space

**Symptoms**: Docker pull fails or containers crash

**Diagnosis**:
```bash
df -h
docker system df
```

**Solutions**:
```bash
# Clean up unused images
docker system prune -a

# Clean up build cache
docker builder prune

# Remove old images
docker rmi $(docker images -f "dangling=true" -q)
```

### Port Already in Use

**Symptoms**: Service fails to start with "port already allocated" error

**Diagnosis**:
```bash
netstat -tulpn | grep :8130
```

**Solution**:
```bash
# Find and kill process using port
lsof -ti:8130 | xargs kill -9

# Or restart all services
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

## Production Deployment Models

### Development (Single Machine)

```
[Frontend] + [Server] + [Runner] + [Postgres]
All in docker-compose.dev.yml
```

### Production (Separate Servers)

```
VPS (cheap):
  [Frontend] + [Server] + [Postgres]
  URL: https://w.198066.xyz

GPU Server (RunPod, Lambda Labs, etc.):
  [Runner] → connects to remote SERVER_URL
```

### Horizontal Scaling

```
1 Server → N Runners (each with unique RUNNER_ID)
```

## Related Skills

```bash
# Production server debugging
/prd_debug

# Run production tests
/test_prd

# Verify backup/restore functionality
/check_backup

# Git workflow with commit and push
/git_push
```

## See Also

- [CLAUDE.md - Architecture](../../CLAUDE.md#architecture-nginx---serverrunner-split)
- [CLAUDE.md - Server/Runner API](../../CLAUDE.md#serverrunner-api)
- [docker-compose.prod.yml](../../docker-compose.prod.yml)
