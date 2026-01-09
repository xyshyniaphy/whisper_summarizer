# Production Deployment Guide

This guide covers deploying Whisper Summarizer to a production server using Docker Compose.

## Architecture Overview

```
Internet → Cloudflare Tunnel → Port 3080 → Nginx (Reverse Proxy)
                                                  ↓
                                    ┌─────────────────┴───────────┐
                                    ↓                           ↓
                              Frontend (Static)           API Server (FastAPI)
                                                             ↓
                                                        PostgreSQL (Internal)
```

**Key Features:**
- ✅ Only port 3080 exposed (HTTP for cloudflared)
- ✅ SSL/TLS handled by Cloudflare tunnel
- ✅ PostgreSQL internal only (no external access)
- ✅ Nginx reverse proxy with rate limiting
- ✅ Health checks for all services
- ✅ Automatic restart on failure

## Prerequisites

1. **Server Requirements:**
   - Docker 20.10+
   - Docker Compose 2.0+
   - Minimum 2GB RAM (4GB recommended)
   - 20GB disk space

2. **Cloudflare Account:**
   - Domain configured in Cloudflare
   - Cloudflare Tunnel installed

3. **Supabase Account:**
   - Project created with Google OAuth enabled

## Quick Start

### 1. Initial Setup

```bash
# Clone repository
git clone <your-repo-url>
cd whisper_summarizer

# Create environment file
cp .env.prod .env

# Edit .env with production values
nano .env
```

### 2. Configure Environment Variables

Edit `.env` and set the following **required** values:

```bash
# Supabase (get from Supabase dashboard)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Strong passwords (generate with: openssl rand -hex 32)
POSTGRES_PASSWORD=<generate-strong-password>
RUNNER_API_KEY=<generate-strong-api-key>

# CORS (include your cloudflare tunnel domain)
CORS_ORIGINS=https://your-domain.example.com,https://your-tunnel.trycloudflare.com

# Authentication (DO NOT CHANGE)
DISABLE_AUTH=false
```

### 3. Build Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Start Services

```bash
./start_prd.sh
```

This will:
- Check prerequisites
- Validate environment configuration
- Build/pull Docker images
- Start all services (postgres, server, nginx)
- Wait for services to be healthy
- Display access information

### 5. Configure Cloudflare Tunnel

Install and configure cloudflared to tunnel to your application:

```bash
# Install cloudflared (Ubuntu/Debian)
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared-linux-amd64.deb

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create whisper-prod

# Configure tunnel (create config.yml)
cat > ~/.cloudflared/config.yml << EOF
tunnel: <your-tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: your-domain.example.com
    service: http://localhost:3080
  - service: http_status:404
