# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Whisper Summarizer is a web application for audio transcription and AI-powered summarization. It uses:
- **faster-whisper** (CTranslate2 + cuDNN) for GPU-accelerated audio transcription
- **GLM-4.5-Air API** (OpenAI-compatible) for summarization
- **PostgreSQL 18 Alpine** for local development database
- **Supabase** for authentication and cloud database (production)
- **Docker Compose** for orchestration

### Transcription Performance Comparison

| Configuration | 5-min Chunk Time | 20-min File Time | Speedup |
|---------------|------------------|-----------------|---------|
| **CPU (Intel/AMD)** | ~15 min | ~60 min | 1x (baseline) |
| **GPU (RTX 3080 with cuDNN)** | ~15-20 sec | ~1-1.5 min | **40-60x** |

*Note: faster-whisper with cuDNN optimized kernels provides significantly better GPU performance than whisper.cpp. Performance varies by GPU model, VRAM, and audio complexity.*

### Services Architecture

**Development Mode:**
```
┌───────────────────────────────────────┐
│         Frontend (Vite Dev)           │
│         React + Tailwind               │
│         :3000 (host)                   │
│  ┌────────────────────────────────┐   │
│  │  Vite Proxy: /api → backend:8000 │   │
│  └────────────────────────────────┘   │
└───────────────────────────────────────┘
                  │
                  │ Docker Network
                  ▼
┌───────────────────────────────────────┐
│         Backend (FastAPI)              │
│         faster-whisper + cuDNN         │
│         :8000 (internal)               │
│         :5678 (debug - host)           │
└───────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌──────────────┐    ┌─────────────────┐
│  PostgreSQL  │    │  Supabase       │
│  18 Alpine   │    │  (Auth only)    │
│  (Dev only)  │    │  - No Storage   │
└──────────────┘    └─────────────────┘

         Local File Storage
         /app/data/transcribes/
         (gzip-compressed .txt.gz)
```

**Key changes:**
- **Local PostgreSQL 18 Alpine** for development database (no port export - internal only)
- **Local filesystem** for transcription text files (`/app/data/transcribes/`, gzip-compressed)
- **Supabase Auth** for authentication only (no Storage used)
- **Vite proxy** pattern - Frontend on :3000 proxies `/api/*` to backend:8000
- **SSE Streaming** - Vite proxy configured to disable buffering for Server-Sent Events

## SSE Streaming Configuration

The application uses Server-Sent Events (SSE) for real-time AI chat responses. Proper configuration is required to prevent buffering in development mode.

### Vite Proxy Configuration

**File:** `frontend/vite.config.ts`

```typescript
proxy: {
  '/api': {
    target: 'http://backend:8000',
    changeOrigin: true,
    // Enable WebSocket support (also helps with SSE streaming)
    ws: true,
    // Configure proxy to NOT buffer SSE responses
    configure: (proxy, options) => {
      proxy.on('proxyRes', (proxyRes: any, req: any, res: any) => {
        // Disable buffering for SSE endpoints
        if (req.url?.includes('/chat/stream') ||
            proxyRes.headers['content-type']?.includes('text/event-stream')) {
          // Ensure no buffering
          delete proxyRes.headers['content-length'];
          // Flush immediately
          proxyRes.headers['x-accel-buffering'] = 'no';
          proxyRes.headers['Cache-Control'] = 'no-cache';
        }
      });
    }
  }
}
```

**Why this is needed:**
- By default, Vite's development proxy buffers responses before forwarding them
- SSE requires immediate forwarding of chunks for real-time streaming
- The configuration above disables buffering for `/chat/stream` endpoints
- Production (static files) doesn't need this - only affects `npm run dev`

### Backend Implementation

**File:** `backend/app/core/glm.py`

The backend uses **httpx** (not OpenAI SDK) for true progressive streaming:

```python
def chat_stream(self, question: str, transcription_context: str, chat_history: list[dict] = None):
    """Uses raw HTTP (httpx) for true progressive streaming."""
    import httpx

    with httpx.Client(timeout=60.0) as client:
        with client.stream(
            'POST',
            f'{self.base_url.rstrip('/')}/chat/completions',
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': self.model,
                'messages': messages,
                'stream': True,
            }
        ) as response:
            for line in response.iter_lines():
                # Process SSE chunks immediately
                if line_str.startswith('data: '):
                    yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
```

**Key implementation details:**
- Uses `httpx.Client.stream()` with `iter_lines()` for true progressive streaming
- Yields SSE-formatted chunks: `data: {"content": "...", "done": false}\n\n`
- Response includes `Content-Type: text/event-stream; charset=utf-8`
- Backend adds `x-accel-buffering: no` header to prevent nginx buffering

### Testing SSE Streaming

To verify streaming is working correctly:

```bash
# Test from host (via Vite proxy - may show buffering in dev mode)
python3 /tmp/test_streaming_speed.py

# Test from inside backend container (true streaming)
docker exec whisper_backend_dev python3 -c "
import httpx, json, time
start = time.time()
with httpx.Client() as client:
    with client.stream('POST', 'https://api.z.ai/api/paas/v4/chat/completions',
        headers={'Authorization': f'Bearer {GLM_API_KEY}'},
        json={'model': 'GLM-4.5-Air', 'messages': [...], 'stream': True}) as r:
        for line in r.iter_lines():
            if line: print(f'{(time.time()-start)*1000:.0f}ms: {line[:50]}...')
"
```

**Expected results:**
- Direct backend test: Chunks spread over 500-2000ms (true streaming)
- Via Vite proxy: Same spread (with proper SSE configuration)
- Without config: All chunks arrive within <10ms (buffered)

### Streaming Behavior by Response Length

| Response Type | Chunks | Spread | Behavior |
|---------------|--------|--------|----------|
| Short (<100 chars) | ~10-50 | 100-500ms | Minimal visible streaming |
| Medium (100-500 chars) | ~50-150 | 500-1500ms | Noticeable word-by-word streaming |
| Long (>500 chars) | ~150+ | 1500-5000ms | Clear progressive streaming |

**Note:** The GLM API (api.z.ai) provides true streaming, but short responses complete quickly enough that the spread may not be noticeable. This is expected behavior.

## Development Commands

### Starting Development Environment

```bash
# Quick start (background)
./run_dev.sh up-d

# With logs (foreground)
./run_dev.sh

# View logs
./run_dev.sh logs

# Stop services
./run_dev.sh down
```

Access URLs:
- Frontend: http://localhost:3000
- API (via Vite proxy): http://localhost:3000/api/*
- Backend Debug: http://localhost:5678 (Python debugger)

### Testing

Use `run_test.sh` for all testing - this is the only supported way to run tests:

```bash
./run_test.sh frontend    # Frontend tests only
./run_test.sh backend     # Backend tests only
./run_test.sh e2e         # E2E tests only (requires dev environment running)
./run_test.sh all         # All tests
./run_test.sh build       # Build test images
./run_test.sh clean       # Cleanup test containers
```

### Building

```bash
# Step 1: Build the fastwhisper base image (first time only, or when model needs update)
./build_fastwhisper_base.sh

# Step 2: Build backend (uses base image, much faster)
docker-compose -f docker-compose.dev.yml build backend

# Step 3: Build frontend (when package.json changes)
docker-compose -f docker-compose.dev.yml build --no-cache frontend

# Step 4: Start services
docker-compose -f docker-compose.dev.yml up -d --force-recreate

# Production
docker-compose up -d --build
```

**Base Image Notes:**
- The `whisper-summarizer-fastwhisper-base` image contains: CUDA cuDNN, faster-whisper model (~3GB)
- Build takes ~10-15 minutes on first run (model download)
- Subsequent backend builds are much faster since model is pre-downloaded
- Rebuild base image with `./build_fastwhisper_base.sh` when updating model or dependencies

### GPU Support

**Requirements:**
- NVIDIA GPU with Compute Capability 7.0+ (RTX 3080, 3090, 4080, 4090, A5000, A6000, etc.)
- NVIDIA Driver 470+ (CUDA 11.4+)
- nvidia-container-toolkit installed on host

**GPU is enabled by default** with faster-whisper. The backend uses `nvidia/cuda:12.9.1-cudnn-runtime-ubuntu24.04` as the base image.

**Configure GPU in .env:**
```bash
# GPU configuration (default settings)
FASTER_WHISPER_DEVICE=cuda                  # Use GPU (set to 'cpu' for CPU-only)
FASTER_WHISPER_COMPUTE_TYPE=int8_float16     # Mixed precision: int8 weights, float16 activations
FASTER_WHISPER_MODEL_SIZE=large-v3-turbo
WHISPER_THREADS=4
```

**Compute Type Options:**
- `int8_float16` - **Default (recommended)**: Mixed precision for optimal memory efficiency (~40% VRAM savings)
- `float16` - Pure 16-bit floating point (fastest, highest accuracy, more VRAM)
- `float32` - Pure 32-bit floating point (most accurate, slowest, most VRAM)
- `int8` - 8-bit integer quantization (CPU/low-VRAM mode, lowest accuracy)

**Switch to CPU-only:**
```bash
# In .env, set:
FASTER_WHISPER_DEVICE=cpu
FASTER_WHISPER_COMPUTE_TYPE=int8
```

**Note**: When `package.json` changes, use `--no-cache` to rebuild the frontend image. The `deps` stage caches `node_modules` and won't pick up new dependencies otherwise.

## Code Architecture

### Backend Structure (`backend/app/`)

```
app/
├── api/              # API route handlers (FastAPI routers)
│   ├── auth.py       # Supabase auth endpoints
│   ├── audio.py      # Audio upload/management
│   └── transcriptions.py
├── core/
│   ├── config.py     # Settings (Pydantic BaseSettings)
│   ├── supabase.py   # Supabase client initialization
│   └── glm.py        # GLM API integration (OpenAI-compatible)
├── services/         # Business logic services
│   ├── storage_service.py      # Local filesystem storage (gzip)
│   ├── whisper_service.py      # faster-whisper wrapper
│   ├── transcription_processor.py  # Async transcription workflow
│   └── pptx_service.py          # PowerPoint generation
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic request/response schemas
├── db/
│   └── session.py    # Database session management
└── main.py           # FastAPI app initialization
```

**Key patterns:**
- FastAPI with dependency injection for auth
- SQLAlchemy ORM with UUID primary keys
- Pydantic schemas for validation
- Service layer pattern for external API calls (GLM, Storage)
- Background tasks for async transcription processing

### Frontend Structure (`frontend/src/`)

```
src/
├── pages/            # Route-level components
│   ├── Login.tsx     # Public auth page
│   ├── Dashboard.tsx # Protected dashboard
│   ├── TranscriptionList.tsx # Transcription list page
│   └── TranscriptionDetail.tsx # Detail page with summary
├── components/       # Reusable UI components
│   ├── ui/           # Tailwind UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Modal.tsx
│   │   ├── Accordion.tsx
│   │   └── index.ts
│   ├── AudioUploader.tsx # File upload with drag & drop
│   ├── NavBar.tsx    # Top navigation bar with mobile menu
│   ├── ThemeToggle.tsx # Sun/moon theme toggle button
│   ├── UserMenu.tsx  # User dropdown with sign out
│   └── GoogleButton.tsx # Google OAuth button
├── hooks/            # Custom React hooks
│   └── useAuth.ts    # Supabase auth state management (Jotai-based)
├── atoms/            # Jotai state atoms
│   ├── auth.ts       # Authentication atoms (user, session, role)
│   ├── theme.ts      # Theme atom (light/dark mode)
│   └── transcriptions.ts # Transcription state atoms
├── services/
│   └── api.ts        # Axios instance + API functions
├── types/            # TypeScript type definitions
├── utils/
│   └── cn.ts         # Tailwind className utility (clsx + tailwind-merge)
├── App.tsx           # React Router setup with ProtectedLayout
└── main.tsx          # Entry point with Jotai Provider
```

**Key patterns:**
- **Jotai** for atomic state management (replaces React Context)
- **Tailwind CSS** for styling (replaces Mantine UI)
- **lucide-react** for icons (replaces @tabler/icons-react)
- React Router v7 for navigation
- `useAuth` hook returns tuple: `[{ user, session, role, loading }, { signInWithGoogle, signOut }]`
- **Google OAuth only**: Email/password signup and login have been removed. Users must sign in with Google OAuth.
- Role-based access control: `role` extracted from `user.user_metadata.role` ('user' | 'admin')
- Dark mode via selector pattern (`.dark` class on documentElement)
- Protected routes check `user` state from `useAuth`
- **Navigation bar** included on all protected routes via `ProtectedLayout` component

### Navigation Components

The app includes a fixed top navigation bar with:
- **Logo/Brand**: Links to `/transcriptions`
- **Navigation Links**: 转录列表, 仪表板
- **Theme Toggle**: Sun/moon button to switch light/dark mode
- **User Menu**: Avatar with dropdown showing user info and sign out (退出登录)
- **Mobile Menu**: Hamburger menu for responsive design

**Component locations:**
- `NavBar.tsx` - Main navigation container
- `ThemeToggle.tsx` - Theme switcher (uses `themeWithPersistenceAtom`)
- `UserMenu.tsx` - User dropdown with sign out

**Integration:** Protected routes use `ProtectedLayout` which wraps content with `NavBar` and adds `pt-16` padding for fixed header.

### Authentication Flow (Google OAuth Only)

**Important:** Email/password signup and login have been removed. Only Google OAuth is supported.

1. Frontend: User clicks "Sign in with Google" button
2. Frontend: Supabase client redirects to Google OAuth
3. Google: User authorizes the app
4. Frontend: Supabase client receives session token
5. Backend: Validates JWT via `SUPABASE_ANON_KEY` on protected routes
6. Tokens stored in `localStorage` (access token) and Supabase client (refresh)

**Supabase keys usage:**
- `SUPABASE_ANON_KEY` - Frontend client, bypasses RLS for public policies
- `SUPABASE_SERVICE_ROLE_KEY` - Backend admin operations, bypasses all RLS

### User & Channel Management

The system includes comprehensive user management and channel-based content organization.

#### User Activation Flow

**Important**: New user registrations create **inactive** accounts by default. Admin approval is required.

1. **User Registration** (Google OAuth)
   - User signs up with Google OAuth
   - Account created with `is_active=FALSE`, `is_admin=FALSE`
   - User redirected to `/pending-activation` page

2. **Admin Activation**
   - Admin accesses `/dashboard` → "用户管理" tab
   - Admin clicks "激活" button to activate user
   - User can now log in and use the system

3. **Access Control**
   - **Inactive users**: Cannot access app features, see pending activation page
   - **Active regular users**: See own content + content from channels they're assigned to
   - **Admin users**: See ALL content + access to dashboard for management

#### Admin Dashboard (`/dashboard`)

**Admin-only access** - Non-admins are redirected to `/transcriptions`.

The dashboard has three main tabs:

**User Management Tab** (`frontend/src/components/dashboard/UserManagementTab.tsx`):
- List all users with status badges (待机中/已激活) and admin badges
- Actions:
  - **激活**: Activate inactive users (sets `is_active=TRUE`, `activated_at=NOW()`)
  - **设为管理员/取消管理员**: Toggle admin status
    - Cannot modify own admin status
    - Cannot remove admin status from the last admin
  - **删除**: Soft delete user (sets `deleted_at`, transfers ownership to admin)
    - Cannot delete self
    - Cannot delete the last admin

**Channel Management Tab** (`frontend/src/components/dashboard/ChannelManagementTab.tsx`):
- List all channels with member counts
- Create/edit/delete channels
- **Admin-only member control**: Only admins can assign users to channels
  - Users cannot self-join or self-leave channels
  - Use member dropdown to add users to a channel

**Audio Management Tab** (`frontend/src/components/dashboard/AudioManagementTab.tsx`):
- List all transcriptions in the system (admin sees all)
- Assign audio to multiple channels
- View current channel assignments per audio file

#### Channel-Based Content Filtering

**Access Rules**:
| Role | Content Visibility |
|------|-------------------|
| **Admin** | ALL content (bypasses channel filters) |
| **Regular User** | Own content + content from assigned channels |

**Backend Implementation** (`backend/app/api/transcriptions.py:45-65`):
```python
if current_db_user.is_admin:
    # Admin sees everything
    query = db.query(Transcription)
else:
    # Regular users: own OR in assigned channels
    user_channel_ids = db.query(ChannelMembership.channel_id).filter(
        ChannelMembership.user_id == current_db_user.id
    ).all()
    channel_transcription_ids = db.query(TranscriptionChannel.transcription_id).filter(
        TranscriptionChannel.channel_id.in_(user_channel_ids)
    ).all()
    query = db.query(Transcription).filter(
        or_(
            Transcription.user_id == current_db_user.id,
            Transcription.id.in_(channel_transcription_ids)
        )
    )
```

#### First-Time Admin Setup

**Script**: `scripts/set_first_admin.sh`

After the first user signs up with Google OAuth, promote them to admin:

```bash
# Development (Docker)
chmod +x scripts/set_first_admin.sh
./scripts/set_first_admin.sh user@example.com

# Production (with DATABASE_URL)
DATABASE_URL="postgresql://..." ./scripts/set_first_admin.sh user@example.com
```

This script:
- Sets `is_admin=TRUE` and `is_active=TRUE` for the specified user
- Supports both dev (Docker exec) and production (DATABASE_URL)

#### Admin API Endpoints

All admin endpoints require `require_admin` decorator.

**User Management** (`/api/admin/users`):
- `GET /api/admin/users` - List all users
- `PUT /api/admin/users/{user_id}/activate` - Activate user account
- `PUT /api/admin/users/{user_id}/admin` - Toggle admin status
- `DELETE /api/admin/users/{user_id}` - Delete user (soft delete + transfer ownership)

**Channel Management** (`/api/admin/channels`):
- `GET /api/admin/channels` - List all channels
- `POST /api/admin/channels` - Create channel
- `PUT /api/admin/channels/{channel_id}` - Update channel
- `DELETE /api/admin/channels/{channel_id}` - Delete channel (cascades to memberships/assignments)
- `GET /api/admin/channels/{channel_id}` - Get channel detail with members
- `POST /api/admin/channels/{channel_id}/members` - Assign user to channel
- `DELETE /api/admin/channels/{channel_id}/members/{user_id}` - Remove user from channel

**Audio Management** (`/api/admin/audio`):
- `GET /api/admin/audio` - List all audio (admin sees all)
- `POST /api/admin/audio/{audio_id}/channels` - Assign audio to channels
- `GET /api/admin/audio/{audio_id}/channels` - Get audio's channel assignments

#### Database Schema

**users table** (extended fields):
```sql
is_active BOOLEAN NOT NULL DEFAULT FALSE  -- Account activation status
is_admin BOOLEAN NOT NULL DEFAULT FALSE   -- Admin privilege
activated_at TIMESTAMP                     -- When account was activated
deleted_at TIMESTAMP                       -- Soft delete timestamp
```

**channels table** (new):
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
name VARCHAR(255) NOT NULL UNIQUE          -- Channel name (unique)
description TEXT                           -- Optional description
created_by UUID REFERENCES users(id)      -- Creator user ID
created_at TIMESTAMP DEFAULT NOW()
updated_at TIMESTAMP DEFAULT NOW()
```

**channel_memberships** (junction table - users ↔ channels):
```sql
channel_id UUID REFERENCES channels(id) ON DELETE CASCADE
user_id UUID REFERENCES users(id) ON DELETE CASCADE
assigned_at TIMESTAMP DEFAULT NOW()
assigned_by UUID REFERENCES users(id)      -- Admin who assigned
PRIMARY KEY (channel_id, user_id)
```

**transcription_channels** (junction table - transcriptions ↔ channels):
```sql
transcription_id UUID REFERENCES transcriptions(id) ON DELETE CASCADE
channel_id UUID REFERENCES channels(id) ON DELETE CASCADE
assigned_at TIMESTAMP DEFAULT NOW()
assigned_by UUID REFERENCES users(id)      -- Admin who assigned
PRIMARY KEY (transcription_id, channel_id)
```

#### Frontend State Management

**Jotai Atoms**:
- `frontend/src/atoms/auth.ts`: Extended user state with `is_active`, `is_admin`
- `frontend/src/atoms/channels.ts`: Channel list, filters, selected channels
- `frontend/src/atoms/dashboard.ts`: Dashboard active tab, sidebar collapse state

**API Service** (`frontend/src/services/api.ts`):
- `adminApi`: All admin endpoints (user management, channel management, audio management)
- `api.getTranscriptionChannels()`: Get channels for a transcription
- `api.assignTranscriptionToChannels()`: Assign transcription to channels

**Pages**:
- `frontend/src/pages/Dashboard.tsx`: Admin dashboard with sidebar and tabs
- `frontend/src/pages/PendingActivation.tsx`: Pending activation page for inactive users

#### Channel UI Components

The frontend includes reusable channel components for displaying and managing channel assignments.

**ChannelBadge Component** (`frontend/src/components/channel/ChannelBadge.tsx`):
- Displays channel assignments as clickable badges
- **Single channel**: Shows channel name with blue styling
- **Multiple channels**: Shows first N channels with "+N more" indicator
- **Personal content**: Shows gray "个人" badge for unassigned content
- **Clickable**: Badges can be clicked to filter the transcription list

```typescript
interface ChannelBadgeProps {
  channels: Channel[]          // Array of channel objects
  isPersonal?: boolean         // True if unassigned content
  maxDisplay?: number          // Max channels to show (default: 2)
  onClick?: (id: string) => void  // Click handler
  className?: string           // Additional CSS classes
}
```

**ChannelFilter Component** (`frontend/src/components/channel/ChannelFilter.tsx`):
- Dropdown filter for selecting channels on transcription list page
- **Filter options**:
  - "全部内容" (All Content) - shows all accessible content
  - "个人内容" (Personal) - shows only own uploads
  - Channel list - shows content assigned to specific channel
- Integrates with `channelFilterAtom` for state persistence

**ChannelAssignModal Component** (`frontend/src/components/channel/ChannelAssignModal.tsx`):
- Modal for assigning transcriptions to multiple channels
- **Features**:
  - Multi-select checkboxes for all channels
  - Search/filter channels by name
  - "Select All" / "Deselect All" functionality
  - Shows current assignments on open
  - Loading state during save operation

```typescript
interface ChannelAssignModalProps {
  isOpen: boolean                    // Modal visibility
  onClose: () => void                // Close handler
  onConfirm: (channelIds: string[]) => Promise<void>  // Save handler
  transcriptionId: string            // Transcription to assign
  currentChannelIds?: string[]       // Currently assigned channels
  loading?: boolean                  // Loading state
}
```

**Integration with Transcription Pages**:

**TranscriptionList** (`frontend/src/pages/TranscriptionList.tsx`):
- Displays `ChannelFilter` dropdown in page header
- Shows `ChannelBadge` for each transcription item in table
- Filter state persisted via `channelFilterAtom`
- API call passes `channel_id` parameter to filter results

**TranscriptionDetail** (`frontend/src/pages/TranscriptionDetail.tsx`):
- Displays current channel badges with "管理频道" button
- Opens `ChannelAssignModal` on button click
- Loads and displays current channel assignments
- Refreshes data after assignment is saved

**Channel Type Definitions** (`frontend/src/types/index.ts`):
```typescript
export interface Channel {
  id: string;
  name: string;
  description?: string;
}

export interface TranscriptionChannel extends Channel {
  // Extends Channel for use in transcription context
}
```

### Environment Variables

Required in `.env`:

```bash
# Supabase (Auth only - no Storage used)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Database (Development - PostgreSQL 18 Alpine)
POSTGRES_DB=whisper_summarizer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Database (Production - Supabase PostgreSQL)
# DATABASE_URL=postgresql://postgres:pass@db.project.supabase.co:5432/postgres

# GLM API (OpenAI-compatible)
# Get API key from https://z.ai/ (international platform)
GLM_API_KEY=your-key
GLM_MODEL=GLM-4.5-Air
# International endpoint (recommended for global users)
GLM_BASE_URL=https://api.z.ai/api/paas/v4/
# China domestic endpoint (alternative for mainland China users)
# GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
REVIEW_LANGUAGE=zh    # zh, ja, en

# faster-whisper Configuration
FASTER_WHISPER_DEVICE=cuda                  # cuda (GPU) or cpu
FASTER_WHISPER_COMPUTE_TYPE=int8_float16     # int8_float16 (default, GPU), float16 (GPU), float32 (GPU), int8 (CPU)
FASTER_WHISPER_MODEL_SIZE=large-v3-turbo
WHISPER_LANGUAGE=zh                         # auto, zh, ja, en, etc.
WHISPER_THREADS=4

# Audio Chunking (for faster transcription of long audio)
ENABLE_CHUNKING=true              # Master toggle for chunking
CHUNK_SIZE_MINUTES=10             # Target chunk length in minutes
CHUNK_OVERLAP_SECONDS=15          # Overlap duration in seconds
MAX_CONCURRENT_CHUNKS=2           # Max parallel chunks (GPU: 4-8 recommended)
USE_VAD_SPLIT=true                # Use Voice Activity Detection for smart splitting
VAD_SILENCE_THRESHOLD=-30         # Silence threshold in dB
VAD_MIN_SILENCE_DURATION=0.5      # Minimum silence duration for split point
MERGE_STRATEGY=lcs                # Merge strategy: lcs (text-based) or timestamp (simple)

# Backend
CORS_ORIGINS=http://localhost:3000
```

## Important Notes

1. **faster-whisper with cuDNN** runs in-process within the backend container
2. **Base image**: `whisper-summarizer-fastwhisper-base` contains pre-downloaded model
3. **First-time setup**: Run `./build_fastwhisper_base.sh` before building backend (takes ~10-15 min)
4. **Hot reload**: Development uses volume mounts for instant code updates
5. **Test coverage target**: 70%+ (currently 73.37% for backend)
6. **uv** is used for Python dependency management (not pip)
7. **Tailwind CSS** is the styling framework - prefer utility classes over custom CSS
8. **Jotai** is used for global state - prefer atoms over React Context
9. **Data persistence**: `data/` directory is volume-mounted (uploads, output, test artifacts)

## Database Relationships & Cascade Deletes

The application uses SQLAlchemy ORM with PostgreSQL foreign key constraints for data integrity.

### Cascade Delete Configuration

When deleting a transcription, related records in `summaries` and `gemini_request_logs` tables are automatically deleted via database-level `ON DELETE CASCADE`:

**Model Configuration:**
```python
# In child models (e.g., gemini_request_log.py)
transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=False)
transcription = relationship("Transcription", back_populates="gemini_logs", passive_deletes=True)

# In parent model (transcription.py)
gemini_logs = relationship("GeminiRequestLog", back_populates="transcription", passive_deletes=True)
summaries = relationship("Summary", back_populates="transcription", passive_deletes=True)
```

**Key Points:**
- `ondelete="CASCADE"` - Database-level constraint (requires migration to update existing tables)
- `passive_deletes=True` - Tells SQLAlchemy to let database handle cascades (no ORM-level UPDATE statements)
- `cascade="merge,save-update"` - Default cascade (no `delete`, `delete-orphan`)
- Use explicit `back_populates` instead of `backref` for clarity

**Migration for existing tables:**
```python
db.execute(text('ALTER TABLE gemini_request_logs DROP CONSTRAINT IF EXISTS gemini_request_logs_transcription_id_fkey'))
db.execute(text('ALTER TABLE gemini_request_logs ADD CONSTRAINT gemini_request_logs_transcription_id_fkey FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE CASCADE'))
```

**Rebuild required:** After model changes, rebuild backend container: `docker-compose -f docker-compose.dev.yml up -d --build --force-recreate backend`

## Local File Storage for Transcription Text

Transcription text is stored on the local filesystem as gzip-compressed files to avoid database size limits and improve performance.

### Storage Service (`storage_service.py`)

```python
from app.services.storage_service import get_storage_service

# Save transcription text to local filesystem
storage_service = get_storage_service()
storage_path = storage_service.save_transcription_text(
    transcription_id=str(transcription.id),
    text=text  # Automatically compressed with gzip level 6
)
# Returns: "{transcription_id}.txt.gz"

# Read and decompress
text = storage_service.get_transcription_text(transcription_id)

# Delete
storage_service.delete_transcription_text(transcription_id)

# Check existence
exists = storage_service.transcription_exists(transcription_id)
```

### Storage Configuration

- **Directory**: `/app/data/transcribes/` (auto-created on initialization)
- **File format**: `{uuid}.txt.gz`
- **Compression**: gzip level 6
- **Permissions**: Managed by Docker container (root:root)
- **Persistence**: Volume-mounted to host `./data/transcribes/`

### Transcription Model Property

The `Transcription` model provides a `.text` property that automatically reads and decompresses:

```python
# In transcription.py model
@property
def text(self) -> str:
    """Get decompressed text from local filesystem."""
    if not self.storage_path:
        return ""
    from app.services.storage_service import get_storage_service
    storage_service = get_storage_service()
    return storage_service.get_transcription_text(str(self.id))
```

### Database Schema

```python
# In transcriptions table
storage_path = Column(String, nullable=True)  # Path to file in local filesystem
# Format: "{uuid}.txt.gz"
```

## Audio Chunking for Faster Transcription

The application implements intelligent audio chunking to significantly speed up transcription of long audio files (10+ minutes).

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    transcribe_with_chunking()                  │
├────────────────────────────────────────────────────────────────┤
│  1. Split Audio                                                 │
│     ├── VAD Silence Detection (FFmpeg silencedetect)           │
│     └── Calculate optimal split points (at silence)            │
│                                                                 │
│  2. Extract Chunks (FFmpeg segment extraction)                 │
│     └── Output: chunk_000.wav, chunk_001.wav, ...              │
│                                                                 │
│  3. Parallel Transcription (ThreadPoolExecutor)                 │
│     ├── Worker 1: chunk_000.wav                                │
│     ├── Worker 2: chunk_001.wav                                │
│     └── ...                                                    │
│                                                                 │
│  4. Merge Results                                               │
│     ├── LCS (text-based alignment) - removes duplicates        │
│     └── Timestamp offset adjustment                             │
└────────────────────────────────────────────────────────────────┘
```

### Key Methods in `whisper_service.py`

| Method | Purpose |
|--------|---------|
| `transcribe_with_chunking()` | Main orchestrator for chunked transcription |
| `_run_faster_whisper()` | Core faster-whisper transcription |
| `_detect_silence_segments()` | Use FFmpeg to find silence in audio |
| `_calculate_split_points()` | Determine optimal split points at silence |
| `_split_audio_into_chunks()` | Split audio into chunk files |
| `_transcribe_chunks_parallel()` | Process chunks with ThreadPoolExecutor |
| `_transcribe_chunk()` | Transcribe single chunk with timestamp offset |
| `_merge_chunk_results()` | Route to LCS or timestamp-based merge |
| `_merge_with_lcs()` | Text-based deduplication using `difflib.SequenceMatcher` |
| `_merge_with_timestamps()` | Simple timestamp filtering (may have duplicates) |

### Config Settings

See Environment Variables section above for all chunking-related settings.

### Trade-offs

| Aspect | Benefit | Consideration |
|--------|---------|---------------|
| **Speed** | 2-3x faster for long audio with chunking | Higher memory usage |
| **VAD Splitting** | No words cut at boundaries | Requires silence in audio |
| **LCS Merging** | Seamless text alignment | More complex than simple join |
| **Parallel Processing** | Better GPU/CPU utilization | More disk I/O for temp chunks |

### Recommended Settings

**faster-whisper (CPU):**
```python
CHUNK_SIZE_MINUTES = 10      # Larger chunks reduce overhead
MAX_CONCURRENT_CHUNKS = 2    # Based on CPU cores
USE_VAD_SPLIT = True         # Smart splitting at silence
MERGE_STRATEGY = "lcs"       # Text-based merging
```

**faster-whisper (GPU with cuDNN):**
```python
CHUNK_SIZE_MINUTES = 10      # Can use larger chunks with GPU
MAX_CONCURRENT_CHUNKS = 4-8  # Based on VRAM (RTX 3080: 4-6 chunks, RTX 3090: 6-8)
USE_VAD_SPLIT = True         # Smart splitting at silence
MERGE_STRATEGY = "lcs"       # Text-based merging
```

**GPU Performance Tips:**
- RTX 3080 8GB: 4-6 concurrent chunks recommended
- RTX 3090/4080 10GB+: 6-8 concurrent chunks
- For very long files (60+ min), consider smaller chunks (5 min) for better progress visibility
- faster-whisper with cuDNN provides 40-60x speedup over CPU (vs 20-30x with whisper.cpp)

## Debugging & Logging

### Debug Log Output Limits

**IMPORTANT:** When adding debug logging, **always restrict by max bytes, NOT line count**. Single lines (especially JSON, base64, or transcribed text) can be extremely long and overwhelm the output.

```python
# GOOD - Restrict by bytes
logger.debug(f"Transcription result: {result[:5000]}")  # First 5000 bytes

# BAD - Restricting by lines doesn't help with long single lines
logger.debug(f"Transcription result: {result}")  # Could be 100KB+ in one line
```

**Recommended limits:**
- General debug output: **1000-5000 bytes**
- Large objects (JSON, transcriptions): **5000-10000 bytes**
- Binary/base64 data: **500-1000 bytes**

**Python pattern:**
```python
MAX_DEBUG_BYTES = 5000
debug_output = str(some_large_object)[:MAX_DEBUG_BYTES]
logger.debug(f"Data: {debug_output}")
```

### Reading Backend Logs

**IMPORTANT:** Backend logs can grow extremely large (10,000+ lines) during hot reload or transcription processing. **NEVER read the full TaskOutput at once** - this will consume excessive tokens.

**When checking task output:**
- Use `timeout` parameter to limit output size
- Look for specific patterns using grep/filter instead of reading all lines
- For chrome-devtools MCP tasks, use `list_console_messages` or `list_network_requests` with pagination instead of reading raw output

```python
# GOOD - Limit output size
TaskOutput(task_id="xxx", block=True, timeout=5000)

# GOOD - Use specific tools
mcp__chrome-devtools__list_console_messages(pageSize=20, pageIdx=0)

# BAD - Reading all logs at once
TaskOutput(task_id="xxx", block=True)  # Could return 18,000+ lines
```

## Frontend UI Patterns

### Confirmation Dialogs (NEVER use window.confirm)

**CRITICAL:** Never use `window.confirm()`, `window.alert()`, or `window.prompt()` in the frontend codebase. These browser native dialogs:
- **Block the JavaScript thread** - prevents test frameworks from working properly
- **Cannot be customized** - poor UX
- **Cannot be tested** - test frameworks cannot interact with them

**Instead, always use the `ConfirmDialog` component:**

```tsx
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { useState } from 'react'

function MyComponent() {
  const [confirmState, setConfirmState] = useState({
    isOpen: false,
    id: null
  })

  const handleActionClick = (id: string) => {
    setConfirmState({ isOpen: true, id })
  }

  const handleConfirm = async () => {
    // Perform the action
    await doSomething(confirmState.id)
    setConfirmState({ isOpen: false, id: null })
  }

  const handleCancel = () => {
    setConfirmState({ isOpen: false, id: null })
  }

  return (
    <>
      <button onClick={() => handleActionClick('123')}>Delete</button>

      <ConfirmDialog
        isOpen={confirmState.isOpen}
        onClose={handleCancel}
        onConfirm={handleConfirm}
        title="确认删除"
        message="确定要删除吗？"
        confirmLabel="删除"
        cancelLabel="取消"
        variant="danger"  // 'default' or 'danger'
      />
    </>
  )
}
```

**ConfirmDialog props:**
- `isOpen`: boolean - Controls visibility
- `onClose`: () => void - Called when user cancels or closes modal
- `onConfirm`: () => void | Promise<void> - Called when user clicks confirm button
- `title`: string - Dialog title
- `message`: string | ReactNode - Dialog message content
- `confirmLabel`: string - Text for confirm button (default: "确定")
- `cancelLabel`: string - Text for cancel button (default: "取消")
- `variant`: 'default' | 'danger' - Style variant (danger shows red warning icon)

### Loading States

Use the `Loader2` component from lucide-react with `animate-spin` for loading indicators:

```tsx
import { Loader2 } from 'lucide-react'

const [isLoading, setIsLoading] = useState(true)

{isLoading ? (
    <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="w-10 h-10 text-blue-500 dark:text-blue-400 animate-spin" />
        <p className="mt-4 text-gray-500 dark:text-gray-400">加载中...</p>
    </div>
) : (
    // content
)}
```

### Conditional Button Display

The `shouldAllowDelete` function in `TranscriptionList.tsx` controls delete button visibility based on item status and age.
