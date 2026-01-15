# CLAUDE.md

Developer guidance for Whisper Summarizer project.

## Project Overview

GPU-accelerated audio transcription with AI summarization using faster-whisper + cuDNN and GLM-4.5-Air API.

**Performance**: GPU (RTX 3080) achieves **11.7x real-time speed** (RTF 0.08) - processes 210-min audio in ~18 minutes.

**Performance Reports**: See `reports/2025-01-13-performance-optimization-report.md` for comprehensive performance analysis.

### Architecture (Nginx + Server/Runner Split)

```
                    Nginx (80/443)
                        ↓
        ┌───────────────┴───────────────┐
        ↓                               ↓
Frontend (/) → Server (/api/*, ~150MB) ←→ Runner (GPU, ~8GB)
                    ↓                              ↓
               PostgreSQL                faster-whisper + GLM
```

**Key Benefits:**
- **Single entry point** - One URL for frontend and API
- **Simplified CORS** - Same origin, no cross-origin issues
- **SSL termination** - Nginx handles HTTPS, server/runner stay HTTP
- **Server runs on cheap VPS** (no GPU needed)
- **Horizontal scaling** (multiple runners)
- **Independent deployment** (update server without affecting processing)
- **Cost optimization** (only runner needs GPU)

**Key Points:**
- **Nginx**: Reverse proxy (routes `/api/*` to server, `/` to frontend, handles SSL)
- **Server**: Lightweight API server (auth, database, job queue, admin endpoints)
- **Runner**: GPU worker (faster-whisper, GLM summarization, job polling)
- **Communication**: HTTP-based job queue with API key authentication
- **Audio cleanup**: Files deleted after processing to save space
- **Local PostgreSQL 18 Alpine** for dev (internal, no port export)
- **Local filesystem** for transcriptions (`/app/data/transcribes/`, gzip-compressed)
- **Supabase Auth** only (no Storage)
- **Nginx** disables buffering for SSE (AI chat streaming)

## Development Commands

```bash
# Start dev environment (background)
./run_dev.sh up-d

# Start with logs (foreground)
./run_dev.sh

# View logs
./run_dev.sh logs

# Stop services
./run_dev.sh down
```

Access: http://localhost:8130 (single entry point via nginx)

**URL Routing:**
- `http://localhost:8130/` → Frontend (React app)
- `http://localhost:8130/api/*` → Server (FastAPI backend)

### Testing

```bash
./run_test.sh frontend    # Frontend tests (bun)
./run_test.sh server      # Server tests
./run_test.sh e2e         # E2E tests (requires dev env running)
./run_test.sh all         # All tests
./run_test.sh build       # Build test images
```

**Coverage**:
- Server: **~240 comprehensive tests** ✅
  - test_runner_api.py: ~55 tests (Runner API, edge cases, race conditions, data consistency)
  - test_audio_upload.py: ~90 tests (Upload, formats, validation, error handling)
  - test_transcriptions_api.py: ~45 tests (CRUD, downloads, chat, share, channels)
  - test_admin_api.py: ~30 tests (User/channel/audio management)
  - test_integration.py: ~20 tests (E2E workflows, performance, security)
- Frontend: **73.6%** (319/433 tests passing, 114 failing)

**Note**: Frontend uses **bun** as the package manager (not npm).

### Building

```bash
# Development builds (hot reload enabled)
docker-compose -f docker-compose.dev.yml build

# Production builds (optimized images)
docker-compose -f docker-compose.prod.yml build

# Build individual services
docker-compose -f docker-compose.dev.yml build frontend  # Development
docker-compose -f docker-compose.prod.yml build frontend  # Production
```

**Frontend Dockerfiles:**
- `Dockerfile.dev` - Development with hot reload (Vite dev server)
- `Dockerfile.prod` - Production with static files (nginx multi-stage build)

## Project Structure

```
whisper_summarizer/
├── server/                    # FastAPI server (lightweight, no GPU) ⭐ ACTIVE
├── runner/                    # GPU worker (faster-whisper + GLM)
├── frontend/                  # React + TypeScript + Vite
├── nginx/                     # Reverse proxy configuration
├── data/                      # Shared data directories
│   ├── server/                # Server-specific data
│   ├── runner/                # Runner-specific data
│   └── uploads/               # Temporary audio uploads
├── scripts/                   # Utility scripts
├── tests/                     # E2E tests
├── backup_legacy/             # Legacy monolithic setup ⭐ BACKUP
│   ├── docker-compose.yml     # Old compose file (monolithic)
│   └── run_prd.sh             # Old production script
└── backend.backup.20250108/   # Legacy monolithic backend ⭐ BACKUP
```

**Active Docker Compose Files:**
- `docker-compose.dev.yml` - Development environment (server + runner + frontend + nginx)
- `docker-compose.prod.yml` - Production environment (optimized)
- `docker-compose.runner.prod.yml` - Runner-only production deployment
- `docker-compose.runner.yml` - Runner development configuration

**Note:** Legacy files have been moved to `backup_legacy/` and `backend.backup.20250108/`. All active development uses the new `server/` + `runner/` split architecture with nginx reverse proxy.

## Code Architecture

### Server (`server/app/`)

**Lightweight API server** - No GPU, no whisper, no ffmpeg required.

```
app/
├── api/              # FastAPI routers
│   ├── auth.py       # Supabase OAuth
│   ├── audio.py      # Audio upload
│   ├── transcriptions.py  # Transcription CRUD
│   ├── admin.py      # Admin endpoints (users, channels, audio)
│   └── runner.py     # Runner API (job queue) ⭐ NEW
├── core/             # Config, Supabase integration
├── services/         # Lightweight services only
│   └── storage_service.py  # File storage (database + paths)
├── models/           # SQLAlchemy ORM
│   └── transcription.py     # + status, runner_id, started_at, etc.
├── schemas/          # Pydantic validation
│   └── runner.py     # Runner API schemas ⭐ NEW
└── db/session.py     # Database session management
```

**Removed from Server** (moved to runner):
- `whisper_service.py` - faster-whisper transcription
- `transcription_processor.py` - Audio processing orchestration
- `glm_service.py` - GLM API summarization
- All ffmpeg/whisper/CUDA dependencies

### Runner (`runner/app/`)

**GPU worker** - Polls server for jobs, processes audio, uploads results.

```
app/
├── worker/
│   └── poller.py     # Main polling loop (async)
├── services/
│   ├── job_client.py     # Server communication (HTTP) ⭐ NEW
│   ├── whisper_service.py    # faster-whisper transcription
│   ├── glm_service.py        # GLM summarization
│   └── audio_processor.py    # Orchestration ⭐ NEW
├── models/
│   └── job_schemas.py    # Job DTOs ⭐ NEW
└── config.py          # Runner configuration (server URL, API key) ⭐ NEW
```

### Frontend (`frontend/src/`)

```
src/
├── pages/            # Route components (Login, Dashboard, TranscriptionList, TranscriptionDetail)
├── components/
│   ├── ui/           # Tailwind UI components (Button, Modal, Badge, ConfirmDialog)
│   ├── channel/      # Channel management (Badge, Filter, AssignModal)
│   └── dashboard/    # Dashboard tabs (Users, Channels, Audio)
├── hooks/useAuth.ts  # Supabase auth (Jotai-based)
├── atoms/            # Jotai state (auth, theme, transcriptions, channels, dashboard)
├── services/api.ts    # Axios + API functions
└── App.tsx           # React Router + ProtectedLayout with NavBar
```

**Key Patterns:**
- **Jotai** for state (not React Context)
- **Tailwind CSS** for styling
- **lucide-react** for icons
- **Google OAuth only** (email/password removed)
- **ConfirmDialog** component (NEVER use `window.confirm`)

## Environment Variables

### Server (.env)

**Server environment variables** - Lightweight, no GPU requirements.

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/whisper_summarizer
POSTGRES_DB=whisper_summarizer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Supabase Auth (Google OAuth only)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Runner Authentication (NEW - Required)
RUNNER_API_KEY=your-super-secret-runner-api-key-here

# Server Configuration
CORS_ORIGINS=http://localhost:3000
```

**Server Docker Image**: `python:3.12-slim` (~150MB)

### Runner (.env)

**Runner environment variables** - GPU required, whisper + GLM.

```bash
# Server Connection (NEW - Required)
SERVER_URL=http://localhost:8000  # Or https://your-server.com
RUNNER_API_KEY=your-super-secret-runner-api-key-here
RUNNER_ID=runner-gpu-01

# Polling Configuration (NEW)
POLL_INTERVAL_SECONDS=10           # How often to poll for jobs
MAX_CONCURRENT_JOBS=2              # Concurrent jobs per runner
JOB_TIMEOUT_SECONDS=3600           # Max time per job

# faster-whisper (GPU enabled by default)
FASTER_WHISPER_DEVICE=cuda              # cuda (GPU) or cpu
FASTER_WHISPER_COMPUTE_TYPE=int8_float16 # int8_float16 (GPU), int8 (CPU)
FASTER_WHISPER_MODEL_SIZE=large-v3-turbo
WHISPER_LANGUAGE=zh
WHISPER_THREADS=4

# Audio Chunking (segments-first approach)
ENABLE_CHUNKING=true
CHUNK_SIZE_MINUTES=5                         # 10-minute chunks for parallel processing
CHUNK_OVERLAP_SECONDS=15                     # Overlap for deduplication
MAX_CONCURRENT_CHUNKS=4                      # GPU: 4-8 recommended
USE_VAD_SPLIT=true                           # Use VAD for smart chunking
MERGE_STRATEGY=lcs                           # Timestamp-based merge for >=10 chunks

# Text Formatting (LLM-based) - 5000 byte chunks to avoid timeouts
MAX_FORMAT_CHUNK=5000

# GLM API (OpenAI-compatible - Moved from Server)
GLM_API_KEY=your-glm-api-key
GLM_MODEL=GLM-4.5-Air
GLM_BASE_URL=https://api.z.ai/api/paas/v4/
REVIEW_LANGUAGE=zh
```

**Runner Docker Image**: `whisper-summarizer-fastwhisper-base:latest` (~8GB)

## Nginx Reverse Proxy

For Nginx configuration, URL routing, SSL, and Cloudflare Tunnel integration, use the **`/whisper-nginx`** skill:

```bash
/whisper-nginx
```

**Quick Reference**:
- **URL Routing**: `/` → Frontend, `/api/*` → Server
- **Port**: `http://localhost:8130` (dev), `https://w.198066.xyz` (prod)
- **SSL**: Handled by Cloudflare Tunnel (no certificates in nginx)
- **Key Features**: SSE streaming, 500MB uploads, WebSocket support, rate limiting

## User & Channel Management

For user roles, permissions, channels, and admin dashboard, use the **`/whisper-users`** skill:

```bash
/whisper-users
```

**Quick Reference**:
- **Roles**: Admin (all content), Regular User (own + assigned channels only)
- **New users**: Inactive by default, require admin approval
- **Admin Dashboard**: `/dashboard` - Manage users, channels, audio
- **Setup**: `./scripts/set_first_admin.sh user@example.com`

## Database Schema

```sql
-- users (extended)
is_active BOOLEAN DEFAULT FALSE
is_admin BOOLEAN DEFAULT FALSE
activated_at TIMESTAMP
deleted_at TIMESTAMP

-- channels
id UUID PRIMARY KEY
name VARCHAR(255) UNIQUE
description TEXT
created_by UUID REFERENCES users(id)

-- channel_memberships (junction)
channel_id UUID REFERENCES channels(id) ON DELETE CASCADE
user_id UUID REFERENCES users(id) ON DELETE CASCADE
PRIMARY KEY (channel_id, user_id)

-- transcription_channels (junction)
transcription_id UUID REFERENCES transcriptions(id) ON DELETE CASCADE
channel_id UUID REFERENCES channels(id) ON DELETE CASCADE
PRIMARY KEY (transcription_id, channel_id)

-- transcriptions (with server/runner split fields)
id UUID PRIMARY KEY
-- ... existing fields ...

status VARCHAR(20) DEFAULT 'pending'      -- NEW: pending, processing, completed, failed
runner_id VARCHAR(100)                      -- NEW: Which runner is processing
started_at TIMESTAMP                        -- NEW: When processing started
completed_at TIMESTAMP                      -- NEW: When processing finished
error_message TEXT                          -- NEW: Error details if failed
processing_time_seconds INTEGER             -- NEW: Processing duration

-- Indexes for runner queries
CREATE INDEX idx_transcriptions_status ON transcriptions(status);
CREATE INDEX idx_transcriptions_status_created ON transcriptions(status, created_at);
```

### Transcription Status Flow

```
pending → processing → completed
                ↘ failed
```

**Status meanings**:
- `pending`: Audio uploaded, waiting for runner to claim
- `processing`: Runner has claimed the job and is processing
- `completed`: Transcription and summary complete
- `failed`: Processing failed (check `error_message`)

## Cascade Deletes

Use `ON DELETE CASCADE` at database level:

```python
# Child model
transcription_id = Column(UUID, ForeignKey("transcriptions.id", ondelete="CASCADE"))
transcription = relationship("Transcription", back_populates="...", passive_deletes=True)
```

**Rebuild required** after model changes:
```bash
docker-compose -f docker-compose.dev.yml up -d --build --force-recreate server
```

## Local File Storage

Transcription text stored as gzip-compressed files (`/app/data/transcribes/{uuid}.txt.gz`).

```python
from app.services.storage_service import get_storage_service

storage = get_storage_service()
storage.save_transcription_text(transcription_id, text)  # Auto-compresses
text = storage.get_transcription_text(transcription_id)  # Auto-decompresses
```

Transcription model provides `.text` property that reads/decompresses automatically.

## Audio Chunking (Segments-First Architecture)

For chunking architecture, VAD split, parallel processing, and SRT generation, use the **`/whisper-chunking`** skill:

```bash
/whisper-chunking
```

**Quick Reference**:
- **Segments-first**: Preserves Whisper timestamps for accurate SRT export
- **VAD Split**: Smart chunking at silence points
- **Parallel Processing**: ThreadPoolExecutor for GPU utilization
- **Config**: `CHUNK_SIZE_MINUTES=5-10`, `MAX_CONCURRENT_CHUNKS=4-6` (GPU)

## Performance Optimization

**CRITICAL**: RTX 3080 achieves **11.7x real-time speed** (RTF 0.08). For performance guidelines, restrictions, benchmarks, and troubleshooting, use the **`/whisper-performance`** skill:

```bash
/whisper-performance
```

**Quick Reference**:
- **RTF target**: <0.1 (excellent), 0.1-0.3 (good), >0.5 (investigate)
- **NEVER**: Fixed-duration chunking (3.3x slower), large GLM payloads (>5000 bytes), sequential processing
- **ALWAYS**: 5-10 min chunks, parallel processing, preserve segments
- **Config (RTX 3080)**: `CHUNK_SIZE_MINUTES=5-10`, `MAX_CONCURRENT_CHUNKS=4-6`

**Performance Report**: See `reports/2025-01-13-performance-optimization-report.md` for comprehensive analysis.

## Debugging & Logging

**Log limits**: Restrict by **bytes**, NOT lines:
```python
logger.debug(f"Result: {result[:5000]}")  # GOOD - First 5000 bytes
logger.debug(f"Result: {result}")        # BAD - Could be 100KB+
```

**Reading logs**: NEVER read full output at once:
```python
TaskOutput(task_id="xxx", block=True, timeout=5000)  # GOOD - 5s limit
mcp__chrome-devtools__list_console_messages(pageSize=20)  # GOOD - 20 items
```

## Authentication Bypass System

### Overview

The system includes a **hardcoded localhost authentication bypass** for automated testing and remote debugging. This replaces the old `DISABLE_AUTH` environment variable approach.

**Key Features**:
- **Zero configuration** - No environment variables needed
- **Secure by default** - Only bypasses for actual localhost requests (`127.0.0.1`, `::1`)
- **Multi-source detection** - Checks `X-Forwarded-For`, `X-Real-IP`, `CF-Connecting-IP`, `client.host`
- **Session persistence** - `session.json` stores test user state
- **Audit logging** - All bypassed requests logged with metadata

### How It Works

```
Localhost Request (127.0.0.1)
    ↓
is_localhost_request() → True
    ↓
get_test_user() from session.json
    ↓
Endpoint called with fake user (test@example.com)

External Request (w.198066.xyz)
    ↓
is_localhost_request() → False
    ↓
Supabase OAuth required
```

### Session Management

**Session file location**: `server/session.json` (auto-created, gitignored)

**Structure**:
```json
{
  "version": "1.0",
  "created_at": "2026-01-10T00:00:00Z",
  "updated_at": "2026-01-10T01:30:00Z",
  "test_user": {
    "id": "fc47855d-6973-4931-b6fd-bd28515bec0d",
    "email": "test@example.com",
    "is_admin": true,
    "is_active": true
  },
  "test_channels": [],
  "test_transcriptions": []
}
```

### Local Development Testing

```bash
# Direct localhost curl (bypasses auth)
curl http://localhost:8130/api/transcriptions

# Via nginx proxy (still localhost)
curl http://localhost:8130/api/transcriptions
```

## Remote Production Debugging

For comprehensive remote debugging and testing capabilities, use the **`/prd_debug`** skill:

```bash
# View all transcriptions
/prd_debug transcriptions

# Check server status
/prd_debug status

# View logs
/prd_debug logs

# Test API endpoint (localhost bypass)
/prd_debug api /health

# Upload audio file for testing
/prd_debug upload /path/to/audio.m4a

# Test chat streaming
/prd_debug chat <transcription_id> "your question"

# Open shell in container
/prd_debug shell

# Query database
/prd_debug db "SELECT * FROM transcriptions LIMIT 5"

# Monitor job processing
/prd_debug watch
```

### Quick Reference

**Production Server**: `ssh -i ~/.ssh/id_ed25519 root@192.3.249.169`
**Project Path**: `/root/whisper_summarizer`
**URL**: https://w.198066.xyz

### Key Features

- **Auth Bypass**: Uses localhost auth bypass inside container
- **No Authentication**: All API calls work without Supabase OAuth
- **Bypasses Cloudflare**: Direct container access
- **Quick Diagnostics**: Check status, logs, APIs from terminal

### Manual SSH Access

**IMPORTANT**: Server container uses `python:3.12-slim` (lightweight, no curl, no requests package). Use Python standard library for HTTP requests.

```bash
# Connect to server
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169

# Quick health check (using Python urllib - always available)
docker exec whisper_server_prd python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').status)"

# Get API response as JSON
docker exec whisper_server_prd python -c "import urllib.request, json; data=json.loads(urllib.request.urlopen('http://localhost:8000/api/transcriptions').read().decode()); print(json.dumps(data, indent=2))"

# Check response headers
docker exec whisper_server_prd python -c "import urllib.request; response=urllib.request.urlopen('http://localhost:8000/api/shared/xxx/download?format=txt'); print(dict(response.headers))"

# Test status code only
docker exec whisper_server_prd python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/transcriptions').status)"

# View logs
docker logs whisper_server_prd --tail=50

# Database access
docker exec -it whisper_postgres_prd psql -U postgres -d whisper_summarizer
```

**See**: [`/prd_debug`](.claude/skills/prd_debug) skill for full documentation

## Frontend UI Patterns

For React component patterns, Jotai state, Tailwind CSS, and coding standards, use the **`/whisper-frontend`** skill:

```bash
/whisper-frontend
```

**Quick Reference**:
- **State**: Jotai (not React Context)
- **Styling**: Tailwind CSS utilities
- **Icons**: lucide-react
- **ConfirmDialog**: NEVER use `window.confirm()`
- **React Hooks**: Use conditional returns, NOT early returns

## Audio Player with SRT Navigation

For sticky audio player, SRT navigation, auto-highlighting, and responsive design, use the **`/whisper-player`** skill:

```bash
/whisper-player
```

**Quick Reference**:
- **Features**: Sticky player, click-to-seek subtitles, auto-highlight, auto-scroll
- **API**: `/api/shared/{token}/segments`, `/api/shared/{token}/audio`
- **Mobile**: Collapsible list, touch-friendly controls
- **Requirements**: `segments.json.gz`, valid audio file, active share token

## E2E Testing

**Development E2E:**
```bash
./run_test.sh e2e-dev              # Run all E2E tests against dev
./run_test.sh e2e-dev auth         # Run specific test pattern
```

**Production E2E:**
```bash
./run_test.sh e2e-prd              # Run all E2E tests against production
./run_test.sh e2e-prd -k auth      # Run specific test pattern
```

**How Production E2E Works:**
- SSH tunnel creates SOCKS5 proxy (`ssh -D 3480`)
- Playwright routes traffic through proxy
- Requests appear from `127.0.0.1` on production server
- Triggers localhost auth bypass → returns `lmr@lmr.com` test user

**Prerequisites for Production E2E:**
- SSH key: `~/.ssh/id_ed25519`
- Production access: `root@192.3.249.169`
- URL: `https://w.198066.xyz`

**See:** `docs/e2e-testing-guide.md` for comprehensive E2E testing documentation

**Testing Patterns:**
For Playwright testing patterns, file upload testing, auth token handling, and common patterns, use the **`/whisper-e2e`** skill:

```bash
/whisper-e2e
```

**Quick Reference:**
- **File Upload**: NEVER click buttons - use direct API calls with auth tokens
- **Auth**: `getAuthToken()` helper from localStorage
- **Helpers**: `uploadFileViaAPI()`, `waitForTranscription()`

## Important Notes

1. **Server/Runner Architecture**: Server is lightweight (~150MB), runner has GPU (~8GB)
2. **Performance**: RTX 3080 achieves 11.7x real-time speed (RTF 0.08) - see `/whisper-performance`
3. **Performance Report**: See `reports/2025-01-13-performance-optimization-report.md` for comprehensive analysis
4. **NEVER use fixed-duration chunking**: Causes 3.3x performance degradation - see `/whisper-performance`
5. **Segments-first architecture**: Preserves Whisper timestamps for accurate SRT export - see `/whisper-chunking`
6. **Server**: Runs on any VPS without GPU, handles auth, database, job queue
7. **Runner**: Runs on GPU server, polls for jobs, processes audio with faster-whisper + GLM
8. **Communication**: HTTP-based job queue with API key authentication
9. **Audio cleanup**: Files deleted after processing to save space
10. **faster-whisper with cuDNN** runs in runner container (not server)
11. **Base image**: Run `./build_fastwhisper_base.sh` first for runner (~10-15 min, includes model download)
12. **Hot reload**: Volume mounts for instant code updates (server and runner)
13. **Test coverage**: Backend ~240 tests ✅, Frontend 73.6% (319/433)
14. **uv** for Python deps (not pip)
15. **Jotai** for state (not React Context) - see `/whisper-frontend`
16. **Data persistence**: `data/` directory volume-mounted with separation (`data/server`, `data/runner`, `data/uploads`)
17. **SSE Streaming**: Vite proxy disables buffering for real-time AI chat - see `/whisper-nginx`
18. **Integration test**: Successfully verified end-to-end workflow with real audio processing
19. **MAX_FORMAT_CHUNK=5000**: Prevents GLM API timeouts - enforced in configuration

## Server/Runner API

### Runner API Endpoints (Server → Runner)

These endpoints are called by the runner to poll for jobs and submit results:

**Authentication**: `Authorization: Bearer RUNNER_API_KEY` header required

- `GET /api/runner/jobs?status=pending&limit=10` - Get pending jobs
- `POST /api/runner/jobs/{id}/start` - Claim a job (status: pending → processing)
- `GET /api/runner/audio/{id}` - Get audio file path for processing
- `POST /api/runner/jobs/{id}/complete` - Submit transcription result
- `POST /api/runner/jobs/{id}/fail` - Report job failure
- `POST /api/runner/heartbeat` - Update runner status (monitoring)

### Job Lifecycle

1. **Upload**: User uploads audio → Server stores → `status=pending`
2. **Claim**: Runner polls → Claims job → `status=processing`, `runner_id=xxx`
3. **Process**: Runner downloads audio, transcribes, summarizes
4. **Complete**: Runner uploads result → `status=completed`, audio deleted
5. **Failure**: Runner reports error → `status=failed`, error saved

### Deployment Models

**Development**: Single machine
```
[Frontend] + [Server] + [Runner] + [Postgres]
All in docker-compose.dev.yml
```

**Production**: Separate servers
```
VPS (cheap):
  [Frontend] + [Server] + [Postgres]

GPU Server (RunPod, Lambda Labs, etc.):
  [Runner] → connects to remote SERVER_URL
```

**Horizontal Scaling**:
```
1 Server → N Runners (each with unique RUNNER_ID)
```

## Production Deployment

For deployment instructions, server configuration, and troubleshooting, use the **`/whisper-deploy`** skill:

```bash
/whisper-deploy
```

**Quick Deploy** (one-line):
```bash
docker build -t xyshyniaphy/whisper_summarizer-server:latest -f server/Dockerfile server && \
docker push xyshyniaphy/whisper_summarizer-server:latest && \
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169 "cd /root/whisper_summarizer && git pull && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d"
```

**Production Server**: `ssh -i ~/.ssh/id_ed25519 root@192.3.249.169`
**URL**: https://w.198066.xyz
**Note**: Build images locally (production server is low-spec), runner runs on separate GPU machine.

## Available Skills

Quick reference for all available skills:

| Skill | Purpose | Command |
|-------|---------|---------|
| **whisper-deploy** | Production deployment | `/whisper-deploy` |
| **whisper-nginx** | Nginx reverse proxy config | `/whisper-nginx` |
| **whisper-performance** | Performance optimization guide | `/whisper-performance` |
| **whisper-chunking** | Audio chunking architecture | `/whisper-chunking` |
| **whisper-frontend** | Frontend UI patterns & coding standards | `/whisper-frontend` |
| **whisper-player** | Audio player with SRT navigation | `/whisper-player` |
| **whisper-e2e** | E2E testing patterns | `/whisper-e2e` |
| **whisper-users** | User & channel management | `/whisper-users` |
| **prd_debug** | Production server remote debugging | `/prd_debug` |
| **test_prd** | Automated production testing | `/test_prd` |
| **check_backup** | Backup and restore verification | `/check_backup` |
| **git_push** | Git workflow with commit and push | `/git_push` |

All skills are located in `.claude/skills/{skill-name}/SKILL.md`.
