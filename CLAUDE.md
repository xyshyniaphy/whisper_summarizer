# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Whisper Summarizer is a microservices web application for audio transcription and AI-powered summarization. It uses:
- **Whisper.cpp** (v3-turbo) for CPU-based audio transcription
- **Google Gemini 2.0 Flash** API for summarization
- **Supabase** for authentication and PostgreSQL database
- **Docker Compose** for orchestration

### Services Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Frontend   │────▶│  Backend    │────▶│  Whisper.cpp     │
│  (React)    │     │  (FastAPI)  │     │  Service         │
│  :3000      │     │  :8000      │     │  :8001           │
└─────────────┘     └─────────────┘     └──────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Supabase   │
                    │  (Auth+DB)  │
                    └─────────────┘
```

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
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

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
# Whisper.cpp base image
./build_whisper.sh              # With cache
./build_whisper.sh --no-cache   # Without cache

# Production
docker-compose up -d --build

# Development rebuild (when package.json changes)
docker-compose -f docker-compose.dev.yml build --no-cache frontend
docker-compose -f docker-compose.dev.yml up -d --force-recreate
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
│   └── gemini.py     # Gemini API integration
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
- Service layer pattern for external API calls (Gemini)

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
- `useAuth` hook returns tuple: `[{ user, session, role, loading }, { signUp, signIn, signOut }]`
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

### Authentication Flow

1. Frontend: `useAuth` hook manages auth state via Supabase client
2. Backend: Validates JWT via `SUPABASE_ANON_KEY` on protected routes
3. Tokens stored in `localStorage` (access token) and Supabase client (refresh)

**Supabase keys usage:**
- `SUPABASE_ANON_KEY` - Frontend client, bypasses RLS for public policies
- `SUPABASE_SERVICE_ROLE_KEY` - Backend admin operations, bypasses all RLS

### Environment Variables

Required in `.env`:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
DATABASE_URL=postgresql://postgres:pass@host:5432/postgres

# Gemini API
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-2.0-flash-exp
REVIEW_LANGUAGE=zh    # zh, ja, en
GEMINI_API_ENDPOINT=  # Optional custom endpoint

# Whisper
WHISPER_LANGUAGE=zh
WHISPER_THREADS=4

# Audio Chunking (for faster transcription of long audio)
ENABLE_CHUNKING=true              # Master toggle for chunking
CHUNK_SIZE_MINUTES=10             # Target chunk length in minutes
CHUNK_OVERLAP_SECONDS=15          # Overlap duration in seconds
MAX_CONCURRENT_CHUNKS=2           # Max parallel chunks (CPU: 2-4, GPU: 4-8)
USE_VAD_SPLIT=true                # Use Voice Activity Detection for smart splitting
VAD_SILENCE_THRESHOLD=-30         # Silence threshold in dB
VAD_MIN_SILENCE_DURATION=0.5      # Minimum silence duration for split point
MERGE_STRATEGY=lcs                # Merge strategy: lcs (text-based) or timestamp (simple)

# Backend
CORS_ORIGINS=http://localhost:3000
```

## Important Notes

1. **Whisper.cpp service** runs as separate Docker container (3.46GB image with v3-turbo model)
2. **Hot reload**: Development uses volume mounts for instant code updates
3. **Test coverage target**: 70%+ (currently 73.37% for backend)
4. **uv** is used for Python dependency management (not pip)
5. **Tailwind CSS** is the styling framework - prefer utility classes over custom CSS
6. **Jotai** is used for global state - prefer atoms over React Context
7. **Data persistence**: `data/` directory is volume-mounted (uploads, output, test artifacts)

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
| **Speed** | 2-3x faster for long audio | Higher memory usage |
| **VAD Splitting** | No words cut at boundaries | Requires silence in audio |
| **LCS Merging** | Seamless text alignment | More complex than simple join |
| **Parallel Processing** | Better CPU utilization | More disk I/O for temp chunks |

### Recommended Settings

**whisper.cpp (CPU):**
```python
CHUNK_SIZE_MINUTES = 10      # Larger chunks reduce overhead
MAX_CONCURRENT_CHUNKS = 2    # Based on CPU cores
USE_VAD_SPLIT = True         # Smart splitting at silence
MERGE_STRATEGY = "lcs"       # Text-based merging
```

**faster-whisper (GPU):**
```python
CHUNK_SIZE_MINUTES = 15      # Can use larger chunks with GPU
MAX_CONCURRENT_CHUNKS = 4    # Based on VRAM (INT8 quantization)
USE_VAD_SPLIT = True
MERGE_STRATEGY = "lcs"
```

## Frontend UI Patterns

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
