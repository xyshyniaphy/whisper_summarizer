# Server/Runner Split Implementation Plan

**Created**: 2026-01-05
**Status**: READY FOR EXECUTION
**Goal**: Split monolithic backend into lightweight server + GPU runner

---

## Executive Summary

**Current Architecture**:
```
Frontend (Vite:3000) → Backend (FastAPI:8000, ~8GB) → PostgreSQL
                                    ↓
                            faster-whisper (cuDNN) + GLM API
```

**Target Architecture**:
```
Frontend (Vite:3000) → Server (FastAPI, ~150MB) ←→ Runner (GPU, ~8GB)
                           ↓                              ↓
                      PostgreSQL                faster-whisper + GLM
```

**Benefits**:
- Server runs on cheap VPS (no GPU needed)
- Horizontal scaling (multiple runners)
- Independent deployment
- Cost optimization

**Key Decisions**:
- ✅ Delete audio after runner completes (save disk space)
- ✅ Simple API key authentication
- ✅ Replace backend/ with server/ immediately
- ✅ GLM summarization on Runner (keeps server lighter)

---

## Architecture Overview

### Server (Lightweight API)
- **Base Image**: `python:3.12-slim` (~150MB vs 8GB)
- **Contains**:
  - FastAPI application
  - Database models and session
  - Supabase auth integration
  - Admin endpoints
  - Job queue management
  - User-facing API endpoints
- **Removed**:
  - Whisper/faster-whisper
  - ffmpeg
  - CUDA/cuDNN
  - GLM API (moved to runner)

### Runner (GPU Processing)
- **Base Image**: `whisper-summarizer-fastwhisper-base`
- **Contains**:
  - faster-whisper (cuDNN)
  - Audio processing (ffmpeg)
  - GLM API summarization
  - Job polling client
  - Result uploader
- **Runs on**: Separate GPU server

### Communication Protocol

```
1. User uploads audio → Server stores (status=pending)
2. Runner polls GET /api/runner/jobs?status=pending
3. Runner claims job POST /api/runner/jobs/{id}/start
4. Runner downloads audio GET /api/runner/audio/{id}
5. Runner transcribes (whisper) + summarizes (GLM)
6. Runner uploads result POST /api/runner/jobs/{id}/complete
7. Server updates DB, status=completed, deletes audio
```

---

## Database Schema Changes

### New Transcription Status Field

```sql
ALTER TABLE transcriptions
ADD COLUMN status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN runner_id VARCHAR(100),
ADD COLUMN started_at TIMESTAMP,
ADD COLUMN completed_at TIMESTAMP,
ADD COLUMN error_message TEXT,
ADD COLUMN processing_time_seconds INTEGER;

-- Index for runner queries
CREATE INDEX idx_transcriptions_status ON transcriptions(status);
CREATE INDEX idx_transcriptions_status_created ON transcriptions(status, created_at);

-- Set existing records to completed
UPDATE transcriptions SET status='completed' WHERE status IS NULL;
```

### Status Enum

```python
class TranscriptionStatus(str, Enum):
    PENDING = "pending"        # Audio uploaded, waiting for runner
    PROCESSING = "processing"  # Runner is working on it
    COMPLETED = "completed"    # Done successfully
    FAILED = "failed"          # Processing failed
```

### Optional: Runners Table (Monitoring)

```sql
CREATE TABLE runners (
    id VARCHAR(100) PRIMARY KEY,
    last_ping TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    max_concurrent_jobs INTEGER DEFAULT 2,
    current_jobs INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Phase 1: Database Migration

**Priority**: HIGHEST - Must be done first
**Estimated Time**: 30 minutes

### Step 1.1: Create Migration Script

**File**: `server/alembic/versions/xxx_add_transcription_status.py`

```python
"""add transcription status fields

Revision ID: xxx_add_status
Revises: xxx
Create Date: 2026-01-05

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add new columns
    op.add_column('transcriptions', sa.Column('status', sa.String(20), nullable=True, server_default='pending'))
    op.add_column('transcriptions', sa.Column('runner_id', sa.String(100), nullable=True))
    op.add_column('transcriptions', sa.Column('started_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('transcriptions', sa.Column('completed_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('transcriptions', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('transcriptions', sa.Column('processing_time_seconds', sa.Integer(), nullable=True))

    # Create indexes
    op.create_index('idx_transcriptions_status', 'transcriptions', ['status'])
    op.create_index('idx_transcriptions_status_created', 'transcriptions', ['status', 'created_at'])

    # Update existing records
    op.execute("UPDATE transcriptions SET status='completed' WHERE status IS NULL")

    # Make status non-nullable after update
    op.alter_column('transcriptions', 'status', nullable=False)

def downgrade():
    op.drop_index('idx_transcriptions_status_created', table_name='transcriptions')
    op.drop_index('idx_transcriptions_status', table_name='transcriptions')
    op.drop_column('transcriptions', 'processing_time_seconds')
    op.drop_column('transcriptions', 'error_message')
    op.drop_column('transcriptions', 'completed_at')
    op.drop_column('transcriptions', 'started_at')
    op.drop_column('transcriptions', 'runner_id')
    op.drop_column('transcriptions', 'status')
```

### Step 1.2: Update Transcription Model

**File**: `server/app/models/transcription.py`

```python
from enum import Enum

class TranscriptionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Transcription(Base):
    __tablename__ = "transcriptions"

    # ... existing fields ...

    status = Column(String(20), default=TranscriptionStatus.PENDING, nullable=False)
    runner_id = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time_seconds = Column(Integer, nullable=True)

    @property
    def processing_time(self) -> Optional[int]:
        """Get processing time in seconds."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None
```

---

## Phase 2: Create Server Directory Structure

**Priority**: HIGHEST
**Estimated Time**: 2 hours

### Step 2.1: Create Directory Structure

```bash
# Create server directory (copy from backend)
mkdir -p server/app

# Copy structure
cp -r backend/app/* server/app/

# Create runner directory
mkdir -p runner/app/{services,worker,models}
```

### Step 2.2: Update Server Models

**File**: `server/app/models/transcription.py`

Add status fields (see Phase 1.2)

### Step 2.3: Create Server Requirements

**File**: `server/requirements.txt`

```txt
# FastAPI and server
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.9

# Database
sqlalchemy==2.0.35
psycopg2-binary==2.9.9

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.1

# Supabase
supabase==2.7.4

# Validation
pydantic==2.10.0
pydantic-settings==2.6.0

# HTTP client
httpx==0.27.2

# Utilities
python-dateutil==2.9.0

# REMOVE: whisper, faster-whisper, ffmpeg, torch, CUDA
```

### Step 2.4: Create Server Dockerfile

**File**: `server/Dockerfile`

```dockerfile
# Lightweight Python image
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY ./app ./app

# Create data directory
RUN mkdir -p /app/data/uploads /app/data/transcribes

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Step 2.5: Create Runner API Endpoints

**File**: `server/app/api/runner.py`

```python
"""
Runner API endpoints - for job queue management
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
import os

from app.db.session import get_db
from app.models.transcription import Transcription, TranscriptionStatus
from app.schemas.runner import (
    JobResponse, JobListResponse,
    JobCompleteRequest, JobStartRequest,
    AudioDownloadResponse
)

router = APIRouter()
security = HTTPBearer()

# API key for runner authentication
RUNNER_API_KEY = os.getenv("RUNNER_API_KEY")

async def verify_runner(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify runner API key."""
    if credentials.credentials != RUNNER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid runner API key"
        )
    return credentials.credentials

@router.get("/jobs", response_model=List[JobResponse])
async def get_pending_jobs(
    status_filter: TranscriptionStatus = TranscriptionStatus.PENDING,
    limit: int = 10,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """Get pending transcription jobs."""
    jobs = db.query(Transcription)\
        .filter(Transcription.status == status_filter)\
        .order_by(Transcription.created_at)\
        .limit(limit)\
        .all()

    return [
        JobResponse(
            id=str(job.id),
            file_name=job.file_name,
            file_path=job.file_path,
            language=job.language,
            created_at=job.created_at
        )
        for job in jobs
    ]

@router.post("/jobs/{job_id}/start")
async def start_job(
    job_id: str,
    request: JobStartRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """Mark job as started (claimed by runner)."""
    job = db.query(Transcription).filter(Transcription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != TranscriptionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Job not available")

    job.status = TranscriptionStatus.PROCESSING
    job.runner_id = request.runner_id
    job.started_at = datetime.utcnow()

    db.commit()
    return {"status": "started"}

@router.post("/jobs/{job_id}/complete")
async def complete_job(
    job_id: str,
    result: JobCompleteRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """Submit transcription result."""
    job = db.query(Transcription).filter(Transcription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = TranscriptionStatus.COMPLETED
    job.text = result.text
    job.summary = result.summary
    job.completed_at = datetime.utcnow()
    job.processing_time_seconds = result.processing_time_seconds

    # Delete audio file to save space
    if job.file_path and os.path.exists(job.file_path):
        os.remove(job.file_path)
        job.file_path = None

    db.commit()
    return {"status": "completed"}

@router.post("/jobs/{job_id}/fail")
async def fail_job(
    job_id: str,
    error_message: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """Report job failure."""
    job = db.query(Transcription).filter(Transcription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = TranscriptionStatus.FAILED
    job.error_message = error_message
    job.completed_at = datetime.utcnow()

    db.commit()
    return {"status": "failed"}

@router.get("/audio/{job_id}", response_model=AudioDownloadResponse)
async def get_audio(
    job_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """Get audio file for processing."""
    job = db.query(Transcription).filter(Transcription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.file_path or not os.path.exists(job.file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return AudioDownloadResponse(
        file_path=job.file_path,
        file_size=os.path.getsize(job.file_path),
        content_type=job.content_type
    )

@router.post("/heartbeat")
async def runner_heartbeat(
    runner_id: str,
    current_jobs: int = 0,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """Update runner heartbeat (optional, for monitoring)."""
    # Optional: Update runners table
    return {"status": "ok"}
```

### Step 2.6: Create Runner Schemas

**File**: `server/app/schemas/runner.py`

```python
"""Runner API schemas"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class JobResponse(BaseModel):
    id: str
    file_name: str
    file_path: str
    language: str
    created_at: datetime

class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    count: int

class JobStartRequest(BaseModel):
    runner_id: str

class JobCompleteRequest(BaseModel):
    text: str
    summary: Optional[str] = None
    processing_time_seconds: int

class AudioDownloadResponse(BaseModel):
    file_path: str
    file_size: int
    content_type: str
```

### Step 2.7: Update Server Main App

**File**: `server/app/main.py`

```python
from fastapi import FastAPI
from app.api import auth, audio, transcriptions, admin, runner
from app.db.session import engine
from app.db.base import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Whisper Summarizer Server")

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(audio.router, prefix="/api/audio", tags=["audio"])
app.include_router(transcriptions.router, prefix="/api/transcriptions", tags=["transcriptions"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(runner.router, prefix="/api/runner", tags=["runner"])

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "server"}
```

---

## Phase 3: Create Runner Service

**Priority**: HIGH
**Estimated Time**: 3 hours

### Step 3.1: Runner Directory Structure

```
runner/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI for health checks
│   ├── config.py           # Configuration
│   ├── services/
│   │   ├── __init__.py
│   │   ├── whisper_service.py      # Copied from backend
│   │   ├── glm_service.py          # Copied from backend
│   │   └── audio_processor.py      # Processing orchestration
│   ├── worker/
│   │   ├── __init__.py
│   │   └── poller.py               # Main polling loop
│   └── models/
│       └── job_schemas.py          # Job DTOs
├── Dockerfile
├── requirements.txt
└── .env.sample
```

### Step 3.2: Runner Configuration

**File**: `runner/app/config.py`

```python
"""Runner configuration"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server connection
    server_url: str = "http://localhost:8000"
    runner_api_key: str = ""
    runner_id: str = "runner-01"

    # Polling config
    poll_interval_seconds: int = 10
    max_concurrent_jobs: int = 2
    job_timeout_seconds: int = 3600

    # Whisper config
    faster_whisper_device: str = "cuda"
    faster_whisper_compute_type: str = "int8_float16"
    faster_whisper_model_size: str = "large-v3-turbo"
    whisper_language: str = "zh"
    whisper_threads: int = 4

    # Audio chunking
    enable_chunking: bool = True
    chunk_size_minutes: int = 10
    chunk_overlap_seconds: int = 15
    max_concurrent_chunks: int = 4
    use_vad_split: bool = True

    # GLM API
    glm_api_key: str = ""
    glm_model: str = "GLM-4.5-Air"
    glm_base_url: str = "https://api.z.ai/api/paas/v4/"
    review_language: str = "zh"

    class Config:
        env_file = ".env"

settings = Settings()
```

### Step 3.3: Runner Job Client

**File**: `runner/app/services/job_client.py`

```python
"""Client for communicating with server"""
import httpx
import os
from typing import List, Optional
from ..models.job_schemas import Job, JobResult
from ..config import settings

class JobClient:
    def __init__(self):
        self.base_url = settings.server_url.rstrip('/')
        self.api_key = settings.runner_api_key
        self.runner_id = settings.runner_id
        self.client = httpx.Client(
            base_url=f"{self.base_url}/api/runner",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0
        )

    def get_pending_jobs(self, limit: int = 1) -> List[Job]:
        """Get pending jobs from server."""
        try:
            response = self.client.get("/jobs", params={"limit": limit})
            response.raise_for_status()
            return [Job(**job) for job in response.json()]
        except httpx.HTTPError as e:
            print(f"Error fetching jobs: {e}")
            return []

    def start_job(self, job_id: str) -> bool:
        """Claim a job from server."""
        try:
            response = self.client.post(
                f"/jobs/{job_id}/start",
                json={"runner_id": self.runner_id}
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            print(f"Error starting job {job_id}: {e}")
            return False

    def get_audio_path(self, job_id: str) -> Optional[str]:
        """Get audio file path for job."""
        try:
            response = self.client.get(f"/audio/{job_id}")
            response.raise_for_status()
            data = response.json()
            return data["file_path"]
        except httpx.HTTPError as e:
            print(f"Error getting audio for job {job_id}: {e}")
            return None

    def complete_job(self, job_id: str, result: JobResult) -> bool:
        """Submit job result to server."""
        try:
            response = self.client.post(
                f"/jobs/{job_id}/complete",
                json={
                    "text": result.text,
                    "summary": result.summary,
                    "processing_time_seconds": result.processing_time_seconds
                }
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            print(f"Error completing job {job_id}: {e}")
            return False

    def fail_job(self, job_id: str, error: str) -> bool:
        """Report job failure."""
        try:
            response = self.client.post(
                f"/jobs/{job_id}/fail",
                content=error.encode(),
                headers={"Content-Type": "text/plain"}
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            print(f"Error reporting failure for job {job_id}: {e}")
            return False

    def send_heartbeat(self, current_jobs: int = 0) -> bool:
        """Send heartbeat to server."""
        try:
            response = self.client.post(
                "/heartbeat",
                params={"runner_id": self.runner_id, "current_jobs": current_jobs}
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def close(self):
        """Close the HTTP client."""
        self.client.close()
```

### Step 3.4: Runner Poller

**File**: `runner/app/worker/poller.py`

```python
"""Main polling loop for runner"""
import asyncio
import signal
import sys
from typing import Set
from concurrent.futures import ThreadPoolExecutor
from ..services.job_client import JobClient
from ..services.audio_processor import AudioProcessor
from ..config import settings
from ..models.job_schemas import Job

class RunnerPoller:
    def __init__(self):
        self.client = JobClient()
        self.processor = AudioProcessor()
        self.running = False
        self.active_jobs: Set[str] = set()
        self.executor = ThreadPoolExecutor(max_workers=settings.max_concurrent_jobs)

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        """Graceful shutdown."""
        print(f"\nReceived signal {signum}, shutting down...")
        self.running = False
        sys.exit(0)

    async def process_job(self, job: Job):
        """Process a single job."""
        print(f"[{job.id}] Processing {job.file_name}")

        # Claim job
        if not self.client.start_job(job.id):
            print(f"[{job.id}] Failed to claim job")
            return

        # Get audio path
        audio_path = self.client.get_audio_path(job.id)
        if not audio_path:
            self.client.fail_job(job.id, "Audio file not found")
            return

        # Process audio
        try:
            result = self.processor.process(audio_path, job.language)
            self.client.complete_job(job.id, result)
            print(f"[{job.id}] Completed in {result.processing_time_seconds}s")
        except Exception as e:
            print(f"[{job.id}] Failed: {e}")
            self.client.fail_job(job.id, str(e))
        finally:
            self.active_jobs.discard(job.id)

    async def poll_loop(self):
        """Main polling loop."""
        print(f"Runner started: {settings.runner_id}")
        print(f"Max concurrent jobs: {settings.max_concurrent_jobs}")
        print(f"Poll interval: {settings.poll_interval_seconds}s")

        self.running = True

        while self.running:
            # Send heartbeat
            self.client.send_heartbeat(len(self.active_jobs))

            # Check if we can accept more jobs
            if len(self.active_jobs) >= settings.max_concurrent_jobs:
                print(f"Max concurrent jobs reached ({len(self.active_jobs)})")
                await asyncio.sleep(settings.poll_interval_seconds)
                continue

            # Fetch pending jobs
            slots_available = settings.max_concurrent_jobs - len(self.active_jobs)
            jobs = self.client.get_pending_jobs(limit=slots_available)

            if not jobs:
                await asyncio.sleep(settings.poll_interval_seconds)
                continue

            # Process jobs concurrently
            for job in jobs:
                self.active_jobs.add(job.id)
                asyncio.create_task(self.process_job(job))

            # Wait before next poll
            await asyncio.sleep(settings.poll_interval_seconds)

    def run(self):
        """Run the poller."""
        try:
            asyncio.run(self.poll_loop())
        finally:
            self.client.close()
            self.executor.shutdown(wait=True)

def main():
    poller = RunnerPoller()
    poller.run()

if __name__ == "__main__":
    main()
```

### Step 3.5: Runner Dockerfile

**File**: `runner/Dockerfile`

```dockerfile
# Base image with faster-whisper and CUDA
FROM whisper-summarizer-fastwhisper-base:latest

WORKDIR /app

# Install additional Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY ./app ./app

# Expose health check port
EXPOSE 8001

# Run poller
CMD ["python", "-m", "app.worker.poller"]
```

### Step 3.6: Runner Requirements

**File**: `runner/requirements.txt`

```txt
# HTTP client
httpx==0.27.2

# Configuration
pydantic-settings==2.6.0
python-dotenv==1.0.1

# Copy from backend requirements:
faster-whisper==1.0.3
ctranslate2==4.4.0
ffmpeg-python==0.2.0
openai==1.54.0  # For GLM API (OpenAI-compatible)
```

### Step 3.7: Runner Environment

**File**: `runner/.env.sample`

```bash
# Server Connection
SERVER_URL=http://localhost:8000
RUNNER_API_KEY=your-secret-runner-api-key
RUNNER_ID=runner-gpu-01

# Polling Config
POLL_INTERVAL_SECONDS=10
MAX_CONCURRENT_JOBS=2
JOB_TIMEOUT_SECONDS=3600

# Whisper Config
FASTER_WHISPER_DEVICE=cuda
FASTER_WHISPER_COMPUTE_TYPE=int8_float16
FASTER_WHISPER_MODEL_SIZE=large-v3-turbo
WHISPER_LANGUAGE=zh
WHISPER_THREADS=4

# Audio Chunking
ENABLE_CHUNKING=true
CHUNK_SIZE_MINUTES=10
CHUNK_OVERLAP_SECONDS=15
MAX_CONCURRENT_CHUNKS=4
USE_VAD_SPLIT=true

# GLM API
GLM_API_KEY=your-glm-api-key
GLM_MODEL=GLM-4.5-Air
GLM_BASE_URL=https://api.z.ai/api/paas/v4/
REVIEW_LANGUAGE=zh
```

---

## Phase 4: Update Docker Compose

**Priority**: HIGH
**Estimated Time**: 1 hour

### Step 4.1: Development Docker Compose

**File**: `docker-compose.dev.yml`

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - server

  server:
    build:
      context: ./server
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./server:/app
      - ./data:/app/data
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/whisper_summarizer
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - RUNNER_API_KEY=${RUNNER_API_KEY:-dev-secret-key}
    depends_on:
      - postgres
    restart: unless-stopped

  runner:
    build:
      context: ./runner
      dockerfile: Dockerfile
    environment:
      - SERVER_URL=http://server:8000
      - RUNNER_API_KEY=${RUNNER_API_KEY:-dev-secret-key}
      - RUNNER_ID=runner-dev
      - MAX_CONCURRENT_JOBS=2
      - FASTER_WHISPER_DEVICE=cuda
      - GLM_API_KEY=${GLM_API_KEY}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - runner-cache:/tmp/whisper_models
      - ./data:/app/data
    depends_on:
      - server
    restart: unless-stopped

  postgres:
    image: postgres:18-alpine
    environment:
      - POSTGRES_DB=whisper_summarizer
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres-data:
  runner-cache:
```

### Step 4.2: Production Docker Compose

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    ports:
      - "80:80"
    depends_on:
      - server
    restart: unless-stopped

  server:
    build:
      context: ./server
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - RUNNER_API_KEY=${RUNNER_API_KEY}
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  # Runner runs on separate GPU server
  # See docker-compose.runner.yml for runner configuration

volumes:
  postgres-data:
```

### Step 4.3: Runner Docker Compose

**File**: `docker-compose.runner.yml`

```yaml
version: '3.8'

services:
  runner:
    build:
      context: ./runner
      dockerfile: Dockerfile
    environment:
      - SERVER_URL=${SERVER_URL}
      - RUNNER_API_KEY=${RUNNER_API_KEY}
      - RUNNER_ID=${RUNNER_ID:-runner-prod-01}
      - MAX_CONCURRENT_JOBS=${MAX_CONCURRENT_JOBS:-4}
      - POLL_INTERVAL_SECONDS=${POLL_INTERVAL_SECONDS:-10}
      - FASTER_WHISPER_DEVICE=cuda
      - GLM_API_KEY=${GLM_API_KEY}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - runner-cache:/tmp/whisper_models
    restart: unless-stopped

volumes:
  runner-cache:
```

---

## Phase 5: Update Development Scripts

**Priority**: MEDIUM
**Estimated Time**: 30 minutes

### Step 5.1: Update run_dev.sh

```bash
#!/bin/bash

case "$1" in
  up-d)
    echo "Starting development environment..."
    docker-compose -f docker-compose.dev.yml up -d
    echo "Server: http://localhost:8000"
    echo "Frontend: http://localhost:3000"
    ;;
  logs)
    docker-compose -f docker-compose.dev.yml logs -f ${2:-}
    ;;
  runner-logs)
    docker-compose -f docker-compose.dev.yml logs -f runner
    ;;
  down)
    docker-compose -f docker-compose.dev.yml down
    ;;
  restart)
    docker-compose -f docker-compose.dev.yml restart ${2:-}
    ;;
  *)
    echo "Usage: $0 {up-d|logs|runner-logs|down|restart}"
    exit 1
esac
```

---

## Phase 6: Documentation Updates

**Priority**: MEDIUM
**Estimated Time**: 1 hour

- [ ] Update README.md with server/runner architecture
- [ ] Update CLAUDE.md with new structure
- [ ] Create deployment guide for runner on separate server
- [ ] Add troubleshooting section for runner connectivity

---

## Phase 7: Testing & Migration

**Priority**: HIGH
**Estimated Time**: 2 hours

### Step 7.1: Test Server Independently

```bash
# Start server only
docker-compose -f docker-compose.dev.yml up server postgres

# Test health check
curl http://localhost:8000/health

# Test runner API (with auth)
curl -H "Authorization: Bearer dev-secret-key" \
  http://localhost:8000/api/runner/jobs
```

### Step 7.2: Test Runner

```bash
# Start runner
docker-compose -f docker-compose.dev.yml up runner

# Check logs for job polling
docker-compose -f docker-compose.dev.yml logs -f runner
```

### Step 7.3: Test Full Integration

1. Upload audio via frontend
2. Verify status=pending in database
3. Watch runner logs for job processing
4. Verify status=completed after processing
5. Verify audio file was deleted
6. Check transcription result in frontend

### Step 7.4: Migrate Existing Data

```sql
-- Set existing transcriptions to completed
UPDATE transcriptions
SET status = 'completed',
    completed_at = COALESCE(updated_at, created_at)
WHERE status IS NULL;

-- Handle failed transcriptions
UPDATE transcriptions
SET status = 'failed',
    error_message = 'Migration: marked as failed'
WHERE text IS NULL AND status IS NULL;
```

---

## File Structure After Split

```
whisper_summarizer/
├── frontend/              # No changes
├── server/                # NEW: Lightweight server (replaces backend)
│   ├── app/
│   │   ├── api/           # + runner.py
│   │   ├── core/          # Config, Supabase
│   │   ├── models/        # + transcription status fields
│   │   ├── schemas/       # + runner.py
│   │   ├── services/      # Lightweight only (no whisper)
│   │   └── db/
│   ├── Dockerfile         # python:3.12-slim
│   └── requirements.txt   # No whisper/ffmpeg/CUDA
├── runner/                # NEW: Whisper runner
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── services/      # whisper, glm, audio_processor
│   │   ├── worker/        # poller.py
│   │   └── models/        # job_schemas.py
│   ├── Dockerfile         # Based on fastwhisper-base
│   ├── requirements.txt
│   └── .env.sample
├── backend/               # DEPRECATED - will be removed after migration
├── data/                  # Shared storage
├── docker-compose.yml
├── docker-compose.dev.yml
└── docker-compose.runner.yml
```

---

## Environment Variables

### Server (.env)

```bash
# Database
DATABASE_URL=postgresql://...

# Supabase
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Runner Authentication (NEW)
RUNNER_API_KEY=your-super-secret-key-here

# Server Config
CORS_ORIGINS=http://localhost:3000
```

### Runner (.env)

```bash
# Server Connection (NEW)
SERVER_URL=https://your-server.com
RUNNER_API_KEY=your-super-secret-key-here
RUNNER_ID=runner-gpu-01

# Polling Config (NEW)
POLL_INTERVAL_SECONDS=10
MAX_CONCURRENT_JOBS=4

# Whisper Config (from backend)
FASTER_WHISPER_DEVICE=cuda
FASTER_WHISPER_COMPUTE_TYPE=int8_float16
# ... etc

# GLM API (from backend - moved here)
GLM_API_KEY=your-glm-api-key
GLM_MODEL=GLM-4.5-Air
# ... etc
```

---

## Deployment Guide

### Server Deployment (No GPU)

```bash
# On any VPS (DigitalOcean, AWS, etc.)
git clone <repo>
cd whisper_summarizer

# Configure .env
cp .env.sample .env
# Edit .env with your settings

# Run database migration
docker-compose -f docker-compose.dev.yml run server alembic upgrade head

# Start server
docker-compose up -d server
```

### Runner Deployment (GPU Server)

```bash
# On GPU server (e.g., RunPod, Lambda Labs)
git clone <repo>
cd whisper_summarizer

# Configure runner
cp runner/.env.sample runner/.env
# Edit runner/.env with SERVER_URL and API keys

# Build and start runner
docker-compose -f docker-compose.runner.yml up -d runner

# View logs
docker-compose -f docker-compose.runner.yml logs -f runner
```

### Multiple Runners

```bash
# On multiple GPU servers, just change RUNNER_ID
# Runner 1:
RUNNER_ID=runner-gpu-01 docker-compose -f docker-compose.runner.yml up -d runner

# Runner 2:
RUNNER_ID=runner-gpu-02 docker-compose -f docker-compose.runner.yml up -d runner
```

---

## Monitoring & Troubleshooting

### Check Runner Status

```sql
-- View active runners
SELECT runner_id,
       COUNT(*) FILTER (WHERE status = 'processing') as active_jobs,
       MAX(last_ping) as last_seen
FROM transcriptions
WHERE started_at > NOW() - INTERVAL '1 hour'
GROUP BY runner_id;
```

### Check Job Queue

```sql
-- View pending jobs
SELECT id, file_name, created_at
FROM transcriptions
WHERE status = 'pending'
ORDER BY created_at;

-- View processing jobs
SELECT id, file_name, runner_id, started_at,
       NOW() - started_at as duration
FROM transcriptions
WHERE status = 'processing';
```

### Common Issues

1. **Runner can't connect to server**
   - Check SERVER_URL is reachable
   - Verify RUNNER_API_KEY matches
   - Check firewall allows traffic

2. **Jobs stuck in processing**
   - Runner may have crashed
   - Check runner logs
   - Manual reset: `UPDATE transcriptions SET status='pending' WHERE status='processing' AND started_at < NOW() - INTERVAL '1 hour'`

3. **Audio file not found**
   - Check server data volume is mounted
   - Verify file permissions
   - Check storage path configuration

---

## Rollback Plan

If issues arise:

```bash
# Stop new services
docker-compose -f docker-compose.dev.yml down

# Switch back to backend
docker-compose -f docker-compose.backend.yml up -d  # Old config

# Revert database migration
alembic downgrade -1
```

---

## Success Criteria

- [ ] Server starts without GPU
- [ ] Runner polls and claims jobs
- [ ] Audio processing completes successfully
- [ ] Results uploaded to server
- [ ] Audio files deleted after processing
- [ ] Multiple runners can run simultaneously
- [ ] Server image < 200MB
- [ ] Runner image ~8GB (unchanged)
- [ ] All tests pass with new architecture

---

**Status**: ✅ READY FOR EXECUTION
**Created**: 2026-01-05
**Priority**: HIGH - Architectural improvement for scalability
**Estimated Total Time**: 8-12 hours

**Next Step**: Execute Phase 1 (Database Migration)
