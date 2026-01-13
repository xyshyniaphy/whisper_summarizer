---
name: whisper-nginx
description: Nginx reverse proxy configuration for Whisper Summarizer. URL routing, SSE support, file uploads, WebSocket, rate limiting, Cloudflare Tunnel integration, and static file serving.
---

# whisper-nginx - Nginx Reverse Proxy

## Purpose

Configures Nginx as a reverse proxy for Whisper Summarizer:
- **Single entry point** - One URL for frontend and API
- **URL routing** - Routes `/api/*` to server, `/` to frontend
- **SSE support** - Disabled buffering for AI chat streaming
- **Large file uploads** - 500MB limit with streaming
- **WebSocket support** - Vite HMR in development
- **Cloudflare Tunnel** - SSL/TLS termination at edge

## Quick Start

```bash
# Development (with hot reload)
docker-compose -f docker-compose.dev.yml up nginx

# Production
docker-compose -f docker-compose.prod.yml up nginx
```

**Access**: http://localhost:8130 (or https://w.198066.xyz in production)

## File Structure

```
nginx/
├── nginx.conf          # Main nginx configuration
└── conf.d/
    └── default.conf    # Server blocks and routing rules
```

## Environment Variables

```bash
# Nginx Configuration
NGINX_HOST=localhost          # Server hostname
NGINX_PORT=8130               # HTTP port (default: 8130, for Cloudflare Tunnel)
```

## URL Routing

```
Request                        → Target
--------------------------------------------------------------
/                              → Frontend (Vite dev server / nginx static)
/health                        → Nginx health check
/api/*                         → Server (FastAPI backend)
  /api/auth/*                  → Supabase OAuth
  /api/audio/*                 → Audio upload
  /api/transcriptions/*        → Transcription CRUD
  /api/admin/*                 → Admin endpoints
  /api/runner/*                → Runner API (job queue)
```

## Configuration (docker-compose)

**Development** (docker-compose.dev.yml):
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "${NGINX_PORT:-8130}:80"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/conf.d:/etc/nginx/conf.d:ro
```

**Production** (docker-compose.prod.yml):
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/conf.d:/etc/nginx/conf.d:ro
```

## Key Features

### 1. SSE Support (AI Chat Streaming)

Enables real-time streaming responses from AI chat:

```nginx
location /api {
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    add_header X-Accel-Buffering no;
}
```

**Why**: Server-Sent Events require disabled buffering to stream responses in real-time.

### 2. Large File Uploads

Supports audio files up to 500MB:

```nginx
client_max_body_size 500M;
proxy_request_buffering off;
proxy_read_timeout 600s;
proxy_send_timeout 600s;
```

**Why**: Streaming uploads prevents memory issues with large files.

### 3. WebSocket Support (Vite HMR)

Enables hot module replacement in development:

```nginx
location / {
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

**Why**: Vite dev server uses WebSocket for live reloading.

### 4. Security Headers

```nginx
add_header X-Frame-Options SAMEORIGIN;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
```

**Why**: Prevents clickjacking, MIME sniffing, and XSS attacks.

### 5. Rate Limiting

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload:10m rate=2r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
}

location /api/audio/ {
    limit_req zone=upload burst=5 nodelay;
}
```

**Why**: Prevents API abuse and DoS attacks.

### 6. Cloudflare Headers

Preserves client information through Cloudflare Tunnel:

```nginx
# Cloudflare preserves these headers:
# CF-Connecting-IP - Real client IP
# CF-Ray - Request identifier
# CF-Visitor - Visitor scheme (http/https)
```

**Why**: Tunnel forwarding preserves original request metadata for logging and authentication.

## Cloudflare Tunnel Integration

**Cloudflare Tunnel** provides SSL/TLS termination for the application.

### Benefits

- **No SSL certificates needed** in nginx configuration
- Cloudflare manages HTTPS at the edge
- Application runs on HTTP internally
- Secure outbound connection only (no open ports)
- Automatic DDoS protection
- Global CDN caching

### Configuration

Cloudflare Tunnel is configured separately through the Cloudflare dashboard (`cloudflared` service).

**Tunnel Routes**:
```
w.198066.xyz → localhost:8130
```

## Static File Serving

### Development Mode

Proxies to Vite dev server with hot reload:

```nginx
location / {
    proxy_pass http://frontend:3000;
}
```

### Production Mode

Serves static files from Docker image:

```nginx
location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}
```

**SPA Routing**: `try_files` fallback ensures React Router works on refresh.

**Asset Caching**:
```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

**Why**: Hashed assets (js, css) never change content, cache for 1 year.

## Frontend Deployment Differences

| Feature | Development | Production |
|---------|-----------|------------|
| Dockerfile | `Dockerfile.dev` | `Dockerfile.prod` |
| Server | Vite dev server (HMR) | Nginx (static files) |
| Source code | Volume mounted | Baked into image |
| Hot reload | ✅ Yes | ❌ No |
| Dev dependencies | ✅ Included | ❌ Excluded |
| Image size | ~500MB | ~20MB (nginx alpine) |
| Build time | Fast | Slower (Vite build) |
| Runtime | Heavy (Node.js) | Light (nginx only) |

## Production Deployment

### Frontend Build (run locally)

```bash
# Ensure .env has SUPABASE_URL and SUPABASE_ANON_KEY
# Build and push to Docker Hub
./push.sh

# This builds frontend with credentials baked in
# Pushes to: xyshyniaphy/whisper_summarizer-frontend:latest
```

### Deploy on Production Server

```bash
# SSH to production server
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169

# Pull latest images
./pull.sh

# Restart services
./stop_prd.sh
./start_prd.sh

# Or restart specific service
docker compose -f docker-compose.prod.yml pull web
docker compose -f docker-compose.prod.yml up -d web
```

**Note**: Vite environment variables are **build-time only** - must be baked into the JavaScript bundle during Docker image build.

## Troubleshooting

### SSE Not Streaming

**Symptoms**: AI chat responses arrive all at once instead of streaming

**Diagnosis**:
```bash
curl -H "Accept: text/event-stream" http://localhost:8130/api/chat
```

**Solution**:
```nginx
# Ensure these are set:
proxy_buffering off;
proxy_cache off;
add_header X-Accel-Buffering no;
```

### File Upload Fails

**Symptoms**: 413 Request Entity Too Large

**Solution**:
```nginx
client_max_body_size 500M;
```

### WebSocket Connection Fails

**Symptoms**: Vite HMR not working in development

**Diagnosis**:
```bash
# Check WebSocket upgrade headers
nginx -T | grep -A 10 "location /"
```

**Solution**:
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### Rate Limiting Too Aggressive

**Symptoms**: Legitimate requests getting 503 errors

**Solution**:
```nginx
# Adjust burst and rate
limit_req zone=api burst=30 nodelay;
```

### SPA Routes Return 404

**Symptoms**: Refreshing /transcription/abc123 returns 404

**Solution**:
```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

## Related Skills

```bash
# Deploy to production
/whisper-deploy

# Debug production issues
/prd_debug

# Frontend UI patterns
/whisper-frontend
```

## See Also

- [CLAUDE.md - Nginx Reverse Proxy](../../CLAUDE.md#nginx-reverse-proxy)
- [nginx/nginx.conf](../../nginx/nginx.conf)
- [nginx/conf.d/default.conf](../../nginx/conf.d/default.conf)
