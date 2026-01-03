# CLAUDE.md

Developer guidance for Whisper Summarizer project.

## Project Overview

GPU-accelerated audio transcription with AI summarization using faster-whisper + cuDNN and GLM-4.5-Air API.

**Performance**: GPU (RTX 3080) achieves **40-60x speedup** vs CPU (20-min file: ~1-1.5 min vs ~60 min).

### Architecture

```
Frontend (Vite:3000) → Backend (FastAPI:8000) → PostgreSQL + Supabase Auth
                                    ↓
                            faster-whisper (cuDNN)
```

**Key Points:**
- **Local PostgreSQL 18 Alpine** for dev (internal, no port export)
- **Local filesystem** for transcriptions (`/app/data/transcribes/`, gzip-compressed)
- **Supabase Auth** only (no Storage)
- **Vite proxy** forwards `/api/*` to backend, disables buffering for SSE

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

**Coverage**: Backend 73.37% (32 tests passing) ✅

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

### Backend (`backend/app/`)

```
app/
├── api/              # FastAPI routers (auth, audio, transcriptions, admin)
├── core/             # Config, Supabase, GLM API integration
├── services/         # Business logic (whisper, storage, transcription processor)
├── models/           # SQLAlchemy ORM (UUID primary keys)
├── schemas/          # Pydantic validation
└── db/session.py     # Database session management
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

## Environment Variables (.env)

```bash
# Supabase (Auth only)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Database (Dev: PostgreSQL 18 Alpine)
POSTGRES_DB=whisper_summarizer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# GLM API (OpenAI-compatible)
GLM_API_KEY=your-key
GLM_MODEL=GLM-4.5-Air
GLM_BASE_URL=https://api.z.ai/api/paas/v4/
REVIEW_LANGUAGE=zh

# faster-whisper (GPU enabled by default)
FASTER_WHISPER_DEVICE=cuda              # cuda or cpu
FASTER_WHISPER_COMPUTE_TYPE=int8_float16  # Mixed precision (recommended)
FASTER_WHISPER_MODEL_SIZE=large-v3-turbo
WHISPER_LANGUAGE=zh
WHISPER_THREADS=4

# Audio Chunking
ENABLE_CHUNKING=true
CHUNK_SIZE_MINUTES=10
CHUNK_OVERLAP_SECONDS=15
MAX_CONCURRENT_CHUNKS=2           # GPU: 4-8 recommended
USE_VAD_SPLIT=true
MERGE_STRATEGY=lcs
```

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
```

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

1. **faster-whisper with cuDNN** runs in-process within backend container
2. **Base image**: Run `./build_fastwhisper_base.sh` first (~10-15 min, includes model download)
3. **Hot reload**: Volume mounts for instant code updates
4. **Test coverage**: 70%+ target (currently 73.37%, 32 tests)
5. **uv** for Python deps (not pip)
6. **Jotai** for state (not React Context)
7. **Data persistence**: `data/` directory volume-mounted
8. **SSE Streaming**: Vite proxy disables buffering for real-time AI chat
