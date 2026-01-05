# CLAUDE.md

Developer guidance for Whisper Summarizer project.

## Project Overview

GPU-accelerated audio transcription with AI summarization using faster-whisper + cuDNN and GLM-4.5-Air API.

**Performance**: GPU (RTX 3080) achieves **40-60x speedup** vs CPU (20-min file: ~1-1.5 min vs ~60 min).

### Architecture (Server/Runner Split)

```
Frontend (Vite:3000) → Server (FastAPI, ~150MB) ←→ Runner (GPU, ~8GB)
                           ↓                              ↓
                      PostgreSQL                faster-whisper + GLM
```

**Key Benefits:**
- **Server runs on cheap VPS** (no GPU needed)
- **Horizontal scaling** (multiple runners)
- **Independent deployment** (update server without affecting processing)
- **Cost optimization** (only runner needs GPU)

**Key Points:**
- **Server**: Lightweight API server (auth, database, job queue, admin endpoints)
- **Runner**: GPU worker (faster-whisper, GLM summarization, job polling)
- **Communication**: HTTP-based job queue with API key authentication
- **Audio cleanup**: Files deleted after processing to save space
- **Local PostgreSQL 18 Alpine** for dev (internal, no port export)
- **Local filesystem** for transcriptions (`/app/data/transcribes/`, gzip-compressed)
- **Supabase Auth** only (no Storage)
- **Vite proxy** forwards `/api/*` to server, disables buffering for SSE

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

Access: http://localhost:3000

### Testing

```bash
./run_test.sh frontend    # Frontend tests (bun)
./run_test.sh backend     # Backend tests
./run_test.sh e2e         # E2E tests (requires dev env running)
./run_test.sh all         # All tests
./run_test.sh build       # Build test images
```

**Coverage**:
- Backend: **~240 comprehensive tests** ✅
  - test_runner_api.py: ~55 tests (Runner API, edge cases, race conditions, data consistency)
  - test_audio_upload.py: ~90 tests (Upload, formats, validation, error handling)
  - test_transcriptions_api.py: ~45 tests (CRUD, downloads, chat, share, channels)
  - test_admin_api.py: ~30 tests (User/channel/audio management)
  - test_integration.py: ~20 tests (E2E workflows, performance, security)
- Frontend: **73.6%** (319/433 tests passing, 114 failing)

**Note**: Frontend uses **bun** as the package manager (not npm).

### Building

```bash
# Step 1: Build base image (first time only, ~10-15 min)
./build_fastwhisper_base.sh

# Step 2: Build backend (uses base image)
docker-compose -f docker-compose.dev.yml build backend

# Step 3: Start services
docker-compose -f docker-compose.dev.yml up -d --force-recreate
```

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
│   ├── whisper_service.py    # faster-whisper (from backend)
│   ├── glm_service.py        # GLM summarization (from backend)
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

# Audio Chunking (long audio optimization)
ENABLE_CHUNKING=true
CHUNK_SIZE_MINUTES=10
CHUNK_OVERLAP_SECONDS=15
MAX_CONCURRENT_CHUNKS=4           # GPU: 4-8 recommended
USE_VAD_SPLIT=true
MERGE_STRATEGY=lcs

# GLM API (OpenAI-compatible - Moved from Server)
GLM_API_KEY=your-glm-api-key
GLM_MODEL=GLM-4.5-Air
GLM_BASE_URL=https://api.z.ai/api/paas/v4/
REVIEW_LANGUAGE=zh
```

**Runner Docker Image**: `whisper-summarizer-fastwhisper-base:latest` (~8GB)

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
docker-compose -f docker-compose.dev.yml up -d --build --force-recreate backend
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

## Audio Chunking

For faster transcription of long files (10+ min):

1. Split audio at VAD-detected silence points
2. Extract chunks with FFmpeg
3. Transcribe in parallel (ThreadPoolExecutor)
4. Merge results with LCS (deduplicates overlaps)

**Recommended Settings:**
- CPU: `MAX_CONCURRENT_CHUNKS=2`, `CHUNK_SIZE_MINUTES=10`
- GPU (RTX 3080): `MAX_CONCURRENT_CHUNKS=4-6`, `CHUNK_SIZE_MINUTES=10-15`

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
2. **Server**: Runs on any VPS without GPU, handles auth, database, job queue
3. **Runner**: Runs on GPU server, polls for jobs, processes audio with faster-whisper + GLM
4. **Communication**: HTTP-based job queue with API key authentication
5. **Audio cleanup**: Files deleted after processing to save space
6. **faster-whisper with cuDNN** runs in runner container (not server)
7. **Base image**: Run `./build_fastwhisper_base.sh` first for runner (~10-15 min, includes model download)
8. **Hot reload**: Volume mounts for instant code updates (server and runner)
9. **Test coverage**: Backend ~240 tests ✅, Frontend 73.6% (319/433)
10. **uv** for Python deps (not pip)
11. **Jotai** for state (not React Context)
12. **Data persistence**: `data/` directory volume-mounted with separation (`data/server`, `data/runner`, `data/uploads`)
13. **SSE Streaming**: Vite proxy disables buffering for real-time AI chat
14. **Integration test**: Successfully verified end-to-end workflow with real audio processing

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
