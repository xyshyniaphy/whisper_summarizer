# Runner Setup Guide

This guide covers setting up the **GPU Runner** on a separate machine.

## Architecture

```
┌─────────────────────────────────────┐
│   Production Server (No GPU)        │
│   ← Runs start_prd.sh               │
│   ├── Frontend (nginx) :3080        │
│   ├── API Server (FastAPI)          │
│   └── PostgreSQL                    │
└─────────────────────────────────────┘
                  ↑
                  │ HTTP + RUNNER_API_KEY
                  │
┌─────────────────────────────────────┐
│   GPU Runner (Separate Machine)     │
│   ← This guide                      │
│   ├── faster-whisper (CUDA)         │
│   ├── GLM API                       │
│   └── Polls for jobs                │
└─────────────────────────────────────┘
```

## Prerequisites

- GPU with CUDA support (tested: RTX 3080)
- Docker & Docker Compose
- 10GB+ disk space
- Network access to production server

## Quick Start

### 1. On Production Server

After starting production services with `./start_prd.sh`:

```bash
# Get your server IP
hostname -I  # Example: 192.168.1.100

# Note the RUNNER_API_KEY from .env
grep RUNNER_API_KEY .env
```

### 2. On GPU Runner Machine

Clone the repository:

```bash
git clone <your-repo-url>
cd whisper_summarizer
```

Create `.env` file for the runner:

```bash
cat > .env << EOF
# Server Connection
SERVER_URL=http://192.168.1.100:3080  # Your production server URL
RUNNER_API_KEY=your-api-key-from-server
RUNNER_ID=runner-gpu-01

# Polling Configuration
POLL_INTERVAL_SECONDS=10
MAX_CONCURRENT_JOBS=2
JOB_TIMEOUT_SECONDS=3600

# faster-whisper (GPU)
FASTER_WHISPER_DEVICE=cuda
FASTER_WHISPER_COMPUTE_TYPE=int8_float16
FASTER_WHISPER_MODEL_SIZE=large-v3-turbo
WHISPER_LANGUAGE=zh

# Audio Chunking
ENABLE_CHUNKING=true
CHUNK_SIZE_MINUTES=10
CHUNK_OVERLAP_SECONDS=15
MAX_CONCURRENT_CHUNKS=4
USE_VAD_SPLIT=true
MERGE_STRATEGY=lcs

# GLM API
GLM_API_KEY=your-glm-api-key
GLM_MODEL=GLM-4.5-Air
GLM_BASE_URL=https://api.z.ai/api/paas/v4/
