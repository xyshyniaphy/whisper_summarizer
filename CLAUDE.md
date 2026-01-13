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

**File Structure:**
```
nginx/
├── nginx.conf          # Main nginx configuration
└── conf.d/
    └── default.conf    # Server blocks and routing rules
```

**Note:** SSL/TLS handled by Cloudflare Tunnel - no certificates needed in nginx.

### Nginx Configuration

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

**Environment Variables:**
```bash
# Nginx Configuration ⭐ NEW
NGINX_HOST=localhost          # Server hostname
NGINX_PORT=8130               # HTTP port (default: 8130, for Cloudflare Tunnel)
```

### URL Routing

```
Request                        → Target
--------------------------------------------------------------
/                              → Frontend (Vite dev server)
/health                        → Nginx health check
/api/*                         → Server (FastAPI backend)
  /api/auth/*                  → Supabase OAuth
  /api/audio/*                 → Audio upload
  /api/transcriptions/*        → Transcription CRUD
  /api/admin/*                 → Admin endpoints
  /api/runner/*                → Runner API (job queue)
```

### Key Features

1. **SSE Support** (AI Chat Streaming):
   - `proxy_buffering off`
   - `proxy_cache off`
   - `X-Accel-Buffering: no` header
   - 1-hour timeout for streaming responses

2. **Large File Uploads**:
   - `client_max_body_size 500M`
   - `proxy_request_buffering off` (stream uploads)
   - Extended timeouts

3. **WebSocket Support** (Vite HMR):
   - `proxy_http_version 1.1`
   - `Connection: "upgrade"` header

4. **Security Headers**:
   - `X-Frame-Options: SAMEORIGIN`
   - `X-Content-Type-Options: nosniff`
   - `X-XSS-Protection: 1; mode=block`

5. **Rate Limiting**:
   - API: 10 req/s with burst of 20
   - Uploads: 2 req/s with burst of 5
   - Connection limit: 10 per IP

6. **Cloudflare Headers**:
   - `CF-Connecting-IP` - Real client IP (preserved through tunnel)
   - `CF-Ray` - Request identifier for debugging
   - `CF-Visitor` - Visitor scheme (http/https)

### Cloudflare Tunnel

**Cloudflare Tunnel** provides SSL/TLS termination for the application.

- **No SSL certificates needed** in nginx configuration
- Cloudflare manages HTTPS at the edge
- Application runs on HTTP internally
- Secure outbound connection only (no open ports)

**Note**: Cloudflare Tunnel configuration is handled separately through the Cloudflare dashboard.

**Static File Serving** (production):
- Development: Proxies to Vite dev server (hot reload, port 3000)
- Production: Serves static files from Docker image (nginx alpine)
- SPA routing: `try_files` fallback to `index.html`
- Asset caching: 1-year cache for hashed assets (js, css, images)

### Frontend Deployment

**Development Mode:**
```bash
# Uses Dockerfile.dev with hot reload
docker-compose -f docker-compose.dev.yml up frontend
```

**Production Mode:**

The production frontend uses pre-built Docker images from Docker Hub. Vite environment variables (VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY) are **build-time only** - they must be baked into the JavaScript bundle during the Docker image build.

**Build and Push Workflow (run locally):**
```bash
# 1. Ensure .env has SUPABASE_URL and SUPABASE_ANON_KEY
# 2. Build and push to Docker Hub
./push.sh

# This builds frontend with your Supabase credentials baked in
# and pushes to: xyshyniaphy/whisper_summarizer-frontend:latest
```

**Deploy on Production Server:**
```bash
# SSH to production server
ssh root@192.3.249.169

# Pull latest images
./pull.sh

# Restart services
./stop_prd.sh
./start_prd.sh

# Or restart specific service
docker compose -f docker-compose.prod.yml pull web
docker compose -f docker-compose.prod.yml up -d web
```

**Key Differences:**

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

## User & Channel Management

**Important**: New users are **inactive** by default. Admin approval required.

### Roles & Access

| Role | Content Visibility |
|------|-------------------|
| **Admin** | ALL content + dashboard access |
| **Regular User** | Own content + assigned channels only |

### First-Time Admin Setup

```bash
# Development
./scripts/set_first_admin.sh user@example.com

# Production
DATABASE_URL="postgresql://..." ./scripts/set_first_admin.sh user@example.com
```

### Admin Dashboard (`/dashboard`)

Three tabs:
1. **User Management**: Activate, toggle admin, soft delete
2. **Channel Management**: Create/edit/delete channels, assign users
3. **Audio Management**: Assign audio to channels

### Channel Assignment Endpoints

**User-accessible** (`/api/transcriptions/{id}/channels`):
- `GET` - Get transcription channels
- `POST` - Assign to channels (replaces existing)

**Admin-only** (`/api/admin/*`):
- `/users` - User management
- `/channels` - Channel management
- `/audio` - Audio management

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

The system uses a **segments-first approach** to preserve individual Whisper timestamps throughout the pipeline.

### Data Flow

```
Whisper Transcription (10-min chunks, parallel)
    ↓
Segments: [{start: 0.0, end: 2.5, text: "..."}, ...]
    ↓
Runner sends segments (NOT concatenated text)
    ↓
Server saves segments.json.gz
    ↓
LLM formatting: Text extracted → chunked by 5000 bytes → GLM → formatted
    ↓
SRT export: Uses original segments.json.gz with real timestamps ✅
```

### Chunking Strategy

For faster transcription of long files (10+ min):

1. Split audio at VAD-detected silence points
2. Extract chunks with FFmpeg
3. Transcribe in parallel (ThreadPoolExecutor)
4. Merge results with **timestamp-based merge** (O(n), fast)

**Key Configuration:**
- `CHUNK_SIZE_MINUTES: 5` - Parallel 5-10 minute chunks
- `MAX_CONCURRENT_CHUNKS: 4` - GPU workers
- `MAX_FORMAT_CHUNK: 5000` - Max bytes per GLM request (avoids timeouts)
- Timestamp-based merge (O(n), fast)

**Recommended Settings:**
- CPU: `MAX_CONCURRENT_CHUNKS=2`, `CHUNK_SIZE_MINUTES=10`
- GPU (RTX 3080): `MAX_CONCURRENT_CHUNKS=4-6`, `CHUNK_SIZE_MINUTES=5-10`

### SRT Generation

The SRT export uses the **original Whisper segments** with their individual timestamps, ensuring:
- Each subtitle line has precise timing from Whisper
- No fake timestamps at chunk boundaries
- Accurate alignment between audio and text

## Performance Restrictions & Best Practices

**CRITICAL**: Follow these performance guidelines to maintain optimal transcription speed.

### ⚠️ PERFORMANCE RESTRICTIONS

**1. NEVER Use Fixed-Duration Chunking**

Fixed-duration chunks (10-30s) cause **massive FFmpeg overhead**:

| Approach | Chunks (210-min) | FFmpeg Calls | RTF | Processing Time |
|----------|------------------|--------------|-----|-----------------|
| **Fixed-Duration (20s)** | 561 | 561 | 0.28 | ~58 min |
| **10-Minute Chunks** | 42 | 42 | 0.08 | ~18 min |

**Performance Impact**: Fixed-duration is **3.3x slower** due to 561 sequential FFmpeg extractions.

**NEVER do this**:
```python
# ❌ WRONG - Fixed-duration chunking (removed from codebase)
def transcribe_fixed_chunks(audio_path, chunk_duration=20):
    for i in range(0, total_duration, chunk_duration):
        extract_audio_with_ffmpeg(audio_path, i, i + chunk_duration)  # 561 calls!
```

**ALWAYS do this**:
```python
# ✅ CORRECT - Use 5-10 minute chunks with parallel processing
def transcribe_with_chunks(audio_path, chunk_size_minutes=5):
    chunks = create_chunks(audio_path, chunk_size_minutes)  # Only 42 chunks
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(transcribe_chunk, chunks)  # Parallel!
```

**2. NEVER Send Large Text Payloads to GLM API**

GLM-4.5-Air has timeout issues with payloads >5000 bytes:

```python
# ❌ WRONG - Large payload causes timeout
formatted_text = glm_format(text)  # 10000+ bytes → timeout

# ✅ CORRECT - Chunk by 5000 bytes
chunks = chunk_text_by_bytes(text, max_bytes=5000)
formatted_parts = [glm_format(chunk) for chunk in chunks]
formatted_text = ''.join(formatted_parts)
```

**Configuration**: `MAX_FORMAT_CHUNK=5000` (enforced in `docker-compose.dev.yml`)

**3. NEVER Process Chunks Sequentially for Long Audio**

Sequential processing prevents GPU utilization:

| Mode | 42 Chunks | GPU Utilization | Time |
|------|-----------|-----------------|------|
| **Sequential** | 1 at a time | 25% | ~70 min |
| **Parallel (4 workers)** | 4 at a time | 95% | ~18 min |

**Configuration**: `MAX_CONCURRENT_CHUNKS=4-6` (GPU-dependent)

**4. NEVER Skip Segments Preservation**

Segments are required for accurate SRT timestamps:

```python
# ❌ WRONG - Only sends concatenated text
result = JobResult(text=concatenated_text, segments=None)

# ✅ CORRECT - Preserves Whisper segments
result = JobResult(text=concatenated_text, segments=whisper_segments)
```

### ✅ PERFORMANCE BEST PRACTICES

**1. Use 5-10 Minute Chunks**

Optimal chunk size balances FFmpeg overhead and parallelization:

| Chunk Size | 210-min File | Chunks | Pros | Cons |
|------------|--------------|--------|------|------|
| 5 min | 42 chunks | 42 | ✅ More parallelization | More merge overhead |
| 10 min | 21 chunks | 21 | ✅ Fewer FFmpeg calls | Less parallelization |
| **20s** | 630 chunks | 630 | ❌ **NEVER USE** | **3.3x slower** |

**Recommended**: `CHUNK_SIZE_MINUTES=5-10`

**2. Match Workers to GPU VRAM**

| GPU Model | VRAM | MAX_CONCURRENT_CHUNKS | CHUNK_SIZE_MINUTES |
|-----------|------|----------------------|-------------------|
| RTX 3060/3060 Ti | 12GB | 4 | 5-10 |
| RTX 3080 | 8GB | 4-6 | 5-10 |
| RTX 3090/4080 | 10GB+ | 6-8 | 10-15 |
| RTX 4090 | 24GB | 8-12 | 10-15 |

**Rule of Thumb**: 1 concurrent chunk per 2GB VRAM (minimum 4 for RTX 3080)

**3. Enable VAD Split for Smart Chunking**

VAD (Voice Activity Detection) splits at silence points:

```yaml
USE_VAD_SPLIT: true
VAD_SILENCE_THRESHOLD: -30
VAD_MIN_SILENCE_DURATION: 0.5
```

**Benefit**: Reduces transcription of silence, improves accuracy.

**4. Use Timestamp-Based Merge for >=10 Chunks**

Auto-selection logic in `whisper_service.py`:

```python
if chunk_count >= 10:
    use_timestamp_merge()  # O(n) - fast
else:
    use_lcs_merge()  # O(n²) - better deduplication
```

**Rationale**: LCS merge has O(n²) complexity - unacceptable for 42+ chunks.

**5. Monitor RTF (Real-Time Factor)**

```
RTF = Processing Time / Audio Duration
```

| RTF | Performance | Status |
|-----|-------------|--------|
| < 0.1 | >10x real-time | ✅ Excellent |
| 0.1-0.3 | 3-10x real-time | ✅ Good |
| 0.3-0.5 | 2-3x real-time | ⚠️ Acceptable |
| > 0.5 | <2x real-time | ❌ Investigate |
| > 1.0 | Slower than real-time | 🚨 Critical issue |

**Expected RTF**:
- 2-min audio: 1.0-1.5x (API overhead dominates)
- 20-min audio: 0.20-0.30x (5x faster than real-time)
- 60-min audio: 0.35-0.45x (2.2-2.8x faster than real-time)
- 210-min audio: 0.25-0.35x (3-4x faster than real-time)

### Performance Benchmarks

**Test Configuration**:
- GPU: NVIDIA RTX 3080
- Model: faster-whisper large-v3-turbo
- Compute: int8_float16 (GPU optimized)

| Audio Duration | Expected RTF | Processing Time | Chunks |
|----------------|-------------|-----------------|--------|
| 2 min | 1.0-1.5x | ~2-3 min | 1 |
| 20 min | 0.20-0.30x | ~4-6 min | 5 |
| 60 min | 0.35-0.45x | ~21-27 min | 6-12 |
| 210 min | 0.25-0.35x | ~52-73 min | 21-42 |

**Key Insight**: Longer audio = better RTF (fixed API overhead amortized).

### Performance Troubleshooting

**Issue**: RTF > 0.5 (slower than expected)

**Checklist**:
1. ✅ `CHUNK_SIZE_MINUTES` is 5-10 (not 20s)
2. ✅ `MAX_CONCURRENT_CHUNKS` matches GPU VRAM (4-6 for RTX 3080)
3. ✅ `MAX_FORMAT_CHUNK` is 5000 (not 10000)
4. ✅ `USE_VAD_SPLIT` is true
5. ✅ `MERGE_STRATEGY` is `lcs`
6. ✅ GPU is being utilized (`nvidia-smi` shows 80-95% GPU usage)

**Issue**: GLM API timeouts

**Solution**: Reduce `MAX_FORMAT_CHUNK` to 4000 or 3000 bytes.

**Issue**: Out of memory errors

**Solution**: Reduce `MAX_CONCURRENT_CHUNKS` by 1-2 workers.

### Code Review Checklist

Before committing performance-related changes:

- [ ] No fixed-duration chunking logic (20-30s chunks)
- [ ] Chunks are processed in parallel (ThreadPoolExecutor)
- [ ] GLM payloads are chunked by 5000 bytes max
- [ ] Whisper segments are preserved throughout pipeline
- [ ] FFmpeg extraction is minimized (42 chunks max for 210-min file)
- [ ] Merge strategy auto-selects based on chunk count
- [ ] GPU workers match VRAM capacity (4-6 for RTX 3080)

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

### Confirmation Dialogs

**NEVER use `window.confirm()`** - blocks JS thread, can't be customized/tested.

```tsx
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { useState } from 'react'

function MyComponent() {
  const [confirm, setConfirm] = useState({ isOpen: false, id: null })

  return (
    <>
      <button onClick={() => setConfirm({ isOpen: true, id: '123' })}>Delete</button>

      <ConfirmDialog
        isOpen={confirm.isOpen}
        onClose={() => setConfirm({ isOpen: false, id: null })}
        onConfirm={async () => {
          await deleteItem(confirm.id)
          setConfirm({ isOpen: false, id: null })
        }}
        title="确认删除"
        message="确定要删除吗？"
        confirmLabel="删除"
        cancelLabel="取消"
        variant="danger"
      />
    </>
  )
}
```

### Loading States

```tsx
import { Loader2 } from 'lucide-react'

{isLoading ? (
  <div className="flex items-center justify-center py-16">
    <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
  </div>
) : (
  // content
)}
```

### React Hooks Rules

**CRITICAL**: Always use conditional returns, NOT early returns, for components with hooks:

```tsx
// ❌ WRONG - Early return after hook causes Hooks violation
export function Modal({ isOpen, ... }) {
  useEffect(() => { ... }, [isOpen])  // Hook called
  if (!isOpen) return null            // Early return breaks hook order
  return ( ... )
}

// ✅ CORRECT - Conditional return preserves hook order
export function Modal({ isOpen, ... }) {
  useEffect(() => { ... }, [isOpen])  // Hook always called
  return isOpen ? ( ... ) : null      // Conditional return
}
```

## Audio Player with SRT Navigation

The shared transcription page includes an interactive audio player with SRT (subtitle) navigation, allowing users to listen to audio while following along with synchronized text.

### Overview

The audio player feature enables a seamless listening experience with:
- **Sticky Audio Player**: Fixed at bottom of viewport for continuous access
- **SRT Navigation**: Click any subtitle to jump to that timestamp
- **Auto-Highlighting**: Current subtitle highlighted during playback
- **Auto-Scrolling**: List automatically scrolls to keep current segment visible
- **Responsive Design**: Optimized for both desktop and smartphone

### Features

**Sticky Audio Player**
- Fixed position at bottom of screen
- Always visible regardless of scroll position
- Collapsible on mobile to save screen space

**SRT Navigation**
- Click any subtitle segment to seek audio to that timestamp
- Smooth scrolling to selected segment
- Visual feedback for active/clicked segments

**Auto-Highlighting**
- Current subtitle highlighted during playback
- Smooth transition between segments
- Clear visual distinction between played, current, and upcoming segments

**Auto-Scrolling**
- Automatic scrolling to keep current segment in view
- Smart scroll behavior (doesn't interrupt manual scrolling)
- Configurable scroll offset for better visibility

**Responsive Design**
- Desktop: Full-featured player with expandable subtitle list
- Smartphone: Compact player with collapsible subtitle list
- Touch-optimized controls for mobile devices

### API Endpoints

**Get SRT Segments**
```http
GET /api/shared/{share_token}/segments
```

**Response** (JSON):
```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "第一段字幕内容"
    },
    {
      "start": 2.5,
      "end": 5.0,
      "text": "第二段字幕内容"
    }
  ]
}
```

**Get Audio File**
```http
GET /api/shared/{share_token}/audio
```

**Features**:
- Supports HTTP Range requests for seeking
- Streams audio in chunks
- Compatible with HTML5 Audio API
- Returns appropriate Content-Type based on audio format

**Response Headers**:
```
Content-Type: audio/mpeg
Accept-Ranges: bytes
Content-Length: 12345678
Content-Range: bytes 0-1023/12345678
```

### Frontend Components

**AudioPlayer Component**

```tsx
interface AudioPlayerProps {
  audioUrl: string;          // URL to audio file
  segments: SrtSegment[];    // Array of subtitle segments
  onTimeUpdate?: (time: number) => void;
  onSegmentClick?: (segment: SrtSegment) => void;
}

interface SrtSegment {
  start: number;    // Start time in seconds
  end: number;      // End time in seconds
  text: string;     // Subtitle text
}
```

**Example Usage**:
```tsx
<AudioPlayer
  audioUrl="/api/shared/abc123/audio"}
  onSegmentClick={(segment) => {
    audioRef.current?.seekTo(segment.start);
  }}
/>
```

**SrtList Component**

```tsx
interface SrtListProps {
  segments: SrtSegment[];
  currentTime: number;
  onSegmentClick: (segment: SrtSegment) => void;
  autoScroll?: boolean;  // Default: true
}

// Segment item styling states:
// - past: Already played (dimmed)
// - current: Currently playing (highlighted)
// - future: Not yet played (normal)
```

**Example Usage**:
```tsx
<SrtList
  segments={segments}
  currentTime={currentTime}
  onSegmentClick={(segment) => handleSegmentClick(segment)}
  autoScroll={true}
/>
```

### Requirements

**Server-Side Requirements**:
1. **Segments File**: `segments.json.gz` must exist in `/app/data/segments/{transcription_id}.json.gz`
   - Generated by runner during transcription
   - Gzip-compressed JSON array of SRT segments
   - Contains accurate Whisper timestamps

2. **Original Audio**: `file_path` must be accessible and point to valid audio file
   - Stored in `/app/data/uploads/` or shared storage
   - Must be readable by server process
   - Supported formats: MP3, M4A, WAV, OGG, etc.

3. **Share Token**: Valid share token must exist in database
   - Token must not be expired
   - Transcription must have `status=completed`

**Client-Side Requirements**:
1. **Browser Support**: HTML5 Audio API
   - Chrome/Edge: Full support
   - Firefox: Full support
   - Safari: Full support (iOS 13+)
   - Mobile browsers: Full support

2. **JavaScript Features**:
   - ES6+ (async/await, arrow functions)
   - React 18+ hooks (useState, useEffect, useRef)
   - CSS Scroll Snap module for smooth scrolling

### Implementation Details

**Segment Synchronization**:
- Audio player's `timeupdate` event triggers highlight updates
- Current segment determined by `currentTime >= segment.start && currentTime < segment.end`
- Highlight updates use React state for efficient re-renders

**Auto-Scroll Logic**:
- Scrolls when current segment changes
- Uses `scrollIntoView()` with `behavior: 'smooth'`
- Respects user scroll position (doesn't interrupt manual scrolling)
- Configurable offset to prevent segment from being too close to edge

**Performance Optimizations**:
- Segments loaded once on component mount
- Audio uses native browser streaming (no full download)
- Highlight updates debounced to 100ms
- Auto-scroll uses `requestAnimationFrame` for smooth 60fps

### Mobile Optimizations

**Smartphone Layout**:
- Player minimized to bottom bar by default
- Expandable subtitle list with toggle button
- Touch-friendly controls (larger tap targets)
- Prevents page scroll when interacting with player

**Touch Gestures**:
- Tap subtitle to seek
- Swipe up/down to expand/collapse list
- Pinch to zoom text size (optional feature)

### Testing

**Manual Testing Checklist**:
- [ ] Audio plays from beginning
- [ ] Clicking subtitle seeks to correct timestamp
- [ ] Current subtitle highlights during playback
- [ ] List scrolls to keep current segment visible
- [ ] Player remains visible when scrolling page
- [ ] Responsive design works on mobile
- [ ] Audio works with Range requests (seeking)
- [ ] Expired/invalid tokens show error

**E2E Test Example**:
```typescript
test('audio player with SRT navigation', async ({ page }) => {
  // Navigate to shared transcription
  await page.goto('/shared/abc123');

  // Wait for audio to load
  await page.waitForSelector('audio');

  // Click a subtitle segment
  await page.click('[data-segment-index="5"]');

  // Verify audio seeked to correct time
  const currentTime = await page.evaluate(() => {
    return document.querySelector('audio')?.currentTime;
  });
  expect(currentTime).toBeCloseTo(expectedTime, 1);
});
```

### Troubleshooting

**Audio Not Playing**:
- Check browser console for CORS errors
- Verify audio file exists at `file_path`
- Ensure server sends correct `Content-Type` header
- Test audio file is valid format

**Segments Not Loading**:
- Verify `segments.json.gz` exists in `/app/data/segments/`
- Check gzip compression is working
- Ensure runner generated segments during transcription
- Check API response for errors

**Auto-Scroll Not Working**:
- Verify `autoScroll` prop is `true`
- Check browser supports `scrollIntoView()`
- Ensure container has `overflow-y: auto`
- Check for CSS conflicts with scroll behavior

**Mobile Issues**:
- Test on actual device (emulator may not be accurate)
- Check viewport meta tag configuration
- Verify touch events are not blocked by other elements
- Ensure player has high z-index for visibility

## E2E Testing with File Uploads

**CRITICAL**: NEVER click upload buttons - opens native file picker, blocks automation.

**Correct pattern** - Direct API calls with auth tokens:

```typescript
// Get auth token from localStorage
const getAuthToken = async (page: Page) => {
  return await page.evaluate(() => {
    const keys = Object.keys(localStorage);
    const authKey = keys.find(k => k.startsWith('sb-') && k.includes('-auth-token'));
    if (!authKey) return null;
    const tokenData = JSON.parse(localStorage.getItem(authKey)!);
    return tokenData?.currentSession?.access_token || tokenData?.access_token || null;
  });
};

// Upload via API
const uploadFileViaAPI = async (page: Page, filePath: string) => {
  const token = await getAuthToken(page);
  const formData = new FormData();
  const fileBuffer = await fs.readFile(filePath);
  formData.append('file', new Blob([fileBuffer]), path.basename(filePath));

  const response = await page.request.post('/api/audio/upload', {
    headers: { 'Authorization': `Bearer ${token}` },
    data: formData
  });
  return response.json();
};
```

## Important Notes

1. **Server/Runner Architecture**: Server is lightweight (~150MB), runner has GPU (~8GB)
2. **Performance**: RTX 3080 achieves 11.7x real-time speed (RTF 0.08) - see [Performance Restrictions & Best Practices](#performance-restrictions--best-practices)
3. **Performance Report**: See `reports/2025-01-13-performance-optimization-report.md` for comprehensive analysis
4. **NEVER use fixed-duration chunking**: Causes 3.3x performance degradation - see restrictions above
5. **Segments-first architecture**: Preserves Whisper timestamps for accurate SRT export
6. **Server**: Runs on any VPS without GPU, handles auth, database, job queue
7. **Runner**: Runs on GPU server, polls for jobs, processes audio with faster-whisper + GLM
8. **Communication**: HTTP-based job queue with API key authentication
9. **Audio cleanup**: Files deleted after processing to save space
10. **faster-whisper with cuDNN** runs in runner container (not server)
11. **Base image**: Run `./build_fastwhisper_base.sh` first for runner (~10-15 min, includes model download)
12. **Hot reload**: Volume mounts for instant code updates (server and runner)
13. **Test coverage**: Backend ~240 tests ✅, Frontend 73.6% (319/433)
14. **uv** for Python deps (not pip)
15. **Jotai** for state (not React Context)
16. **Data persistence**: `data/` directory volume-mounted with separation (`data/server`, `data/runner`, `data/uploads`)
17. **SSE Streaming**: Vite proxy disables buffering for real-time AI chat
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

### Production Server Info

**Location**: `ssh -i ~/.ssh/id_ed25519 root@192.3.249.169`
**SSH Key**: `~/.ssh/id_ed25519`
**Project Path**: `/root/whisper_summarizer`
**URL**: https://w.198066.xyz

**IMPORTANT**: Production server is **low spec** - DO NOT build images on production server.

**Production API Testing Pattern**:
Server container uses `python:3.12-slim` (lightweight, no curl). Use Python standard library `urllib.request` for HTTP testing. This bypasses Cloudflare protection and uses localhost auth bypass:

```bash
# Check health status
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169 "docker exec whisper_server_prd python -c \"import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').status)\""

# Get transcriptions (JSON)
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169 "docker exec whisper_server_prd python -c \"import urllib.request, json; data=json.loads(urllib.request.urlopen('http://localhost:8000/api/transcriptions').read().decode()); print(json.dumps(data, indent=2))\""
```

### Deployment Workflow

**Build images locally, push to registry, pull on production:**

```bash
# 1. Build and push images LOCALLY (not on production server)
docker build -t xyshyniaphy/whisper_summarizer-server:latest -f server/Dockerfile server
docker build -t xyshyniaphy/whisper_summarizer-frontend:latest -f frontend/Dockerfile.prod frontend
docker push xyshyniaphy/whisper_summarizer-server:latest
docker push xyshyniaphy/whisper_summarizer-frontend:latest

# 2. Connect to production server and pull images
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169
cd /root/whisper_summarizer

# 3. Pull latest code
git pull

# 4. Pull and restart services
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# 5. View logs
docker compose -f docker-compose.prod.yml logs -f server
```

### What to Deploy

| Service | Deploy to Production? | Notes |
|---------|----------------------|-------|
| Frontend | ✅ Yes | Static files, lightweight |
| Server | ✅ Yes | API server, lightweight |
| Runner | ❌ NO | Runner runs on separate GPU machine |

**Runner is NOT deployed to production server** - it runs on a separate GPU machine that connects to the production server via `SERVER_URL`.

### Quick Deploy Script

```bash
# One-line deploy (run from local machine)
docker build -t xyshyniaphy/whisper_summarizer-server:latest -f server/Dockerfile server && \
docker push xyshyniaphy/whisper_summarizer-server:latest && \
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169 "cd /root/whisper_summarizer && git pull && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d"
```

### Debugging on Production Server

For remote debugging and testing, use the **`/prd_debug`** skill or SSH directly:

```bash
# Use the prd_debug skill
/prd_debug status
/prd_debug logs
/prd_debug api /health

# Or connect manually
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169

# Check container status
docker ps -a

# View logs
docker logs whisper_server_prd --tail=100
docker logs whisper_web_prd --tail=100

# Restart services
cd /root/whisper_summarizer
docker compose -f docker-compose.prod.yml restart server
```

**See**: [Remote Production Debugging](#remote-production-debugging) section above for `/prd_debug` skill usage.

### Common Issues

**DELETE 500 Error**:
- Check for RecursionError in logs: `docker logs whisper_server_prd | grep -i recursion`
- Usually caused by function calling itself instead of getting user ID

**Container unhealthy**:
- Check health status: `docker ps`
- View logs: `docker logs whisper_server_prd`
- Common issue: Database not ready when server starts

**Images not updating**:
- Ensure you pushed to Docker Hub: `docker push xyshyniaphy/whisper_summarizer-server:latest`
- Pull with digest: `docker pull xyshyniaphy/whisper_summarizer-server:latest@sha256:...`
- Force recreate: `docker compose -f docker-compose.prod.yml up -d --force-recreate server`
