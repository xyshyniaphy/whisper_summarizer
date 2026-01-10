# Remote Server Integration Test Plan

## Overview

Test the local runner connecting to the remote production server to verify end-to-end audio processing workflow across network boundaries.

**Architecture**:
```
Local Runner (GPU Worker) ←→ HTTPS API ←→ Remote Production Server (https://w.198066.xyz/)
     ↓                                                  ↓
faster-whisper + GLM                          PostgreSQL + File Storage
```

**Key Points**:
- **Local Runner**: Runs on local machine with GPU (RTX 3080)
- **Remote Server**: Production VPS at `ssh root@192.3.249.169`
- **Communication**: HTTPS-based job queue with API key authentication
- **Audio Transfer**: Runner downloads audio via HTTP from remote server
- **Debug Mode**: Watch both local runner logs and remote server logs
- **Deployment**: Build images locally → Push to registry → Remote pulls and restarts

## Test Environment

### Remote Production Server

**Connection**:
```bash
ssh root@192.3.249.169
cd /root/whisper_summarizer
```

**URL**: https://w.198066.xyz

**Containers**:
- `whisper_server_prd` - FastAPI server (lightweight, no GPU)
- `whisper_postgres_prd` - PostgreSQL 18 Alpine
- `whisper_web_prd` - Frontend (nginx)

### Local Runner

**Configuration**: `runner/.env`
```bash
# Server Connection (PRODUCTION)
SERVER_URL=https://w.198066.xyz
RUNNER_API_KEY=<from remote server .env>
RUNNER_ID=runner-local-gpu-01

# Polling Config
POLL_INTERVAL_SECONDS=10
MAX_CONCURRENT_JOBS=2
JOB_TIMEOUT_SECONDS=3600

# Whisper Config (Local GPU)
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
USE_VAD_SPLIT=false  # Fixed-length chunking (VAD causes hangs with many silence segments)

# GLM API
GLM_API_KEY=<your key>
GLM_MODEL=GLM-4.5-Air
GLM_BASE_URL=https://api.z.ai/api/paas/v4/
REVIEW_LANGUAGE=zh
```

## Test Files

| File | Size | Duration | Expected Chunks | Processing Time |
|------|------|----------|-----------------|-----------------|
| 2_min.m4a | 85 KB | ~120 sec | 1 (standard) | ~5-10 seconds |
| 20_min.m4a | 5 MB | ~1200 sec | ~2 chunks | ~30-60 seconds |
| 60_min.m4a | 15 MB | ~3600 sec | ~6 chunks | ~90-120 seconds |
| 210_min.m4a | 52 MB | ~12600 sec | ~21 chunks | ~5-7 minutes |

**Note**: VAD splitting disabled (USE_VAD_SPLIT=false) due to hang issues with 300+ silence segments. Fixed-length chunking is more reliable.

## Process Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│              REMOTE SERVER INTEGRATION TEST FLOW                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  0. USER UPLOAD (Local Machine → Remote Server)                     │
│     ├── Upload file via web UI: https://w.198066.xyz/             │
│     ├── OR curl POST to: https://w.198066.xyz/api/audio/upload    │
│     ├── Remote server creates DB record (status: pending)          │
│     └── Remote server saves file to /app/data/uploads/             │
│                                                                     │
│  1. LOCAL RUNNER POLLING (Local Runner → Remote Server)            │
│     ├── Runner polls: GET https://w.198066.xyz/api/runner/jobs    │
│     ├── Remote server authenticates RUNNER_API_KEY                 │
│     └── Returns pending jobs                                      │
│                                                                     │
│  2. JOB CLAIM (Local Runner → Remote Server)                       │
│     ├── Runner claims: POST /api/runner/jobs/{id}/start            │
│     ├── Remote server updates: status=processing, runner_id=xxx    │
│     └── Sets started_at timestamp                                 │
│                                                                     │
│  3. AUDIO DOWNLOAD (Local Runner ← Remote Server)                  │
│     ├── GET https://w.198066.xyz/api/runner/audio/{id}/download    │
│     ├── Remote server streams file from /app/data/uploads/        │
│     └── Runner saves to /tmp/whisper_runner/{id}.m4a              │
│                                                                     │
│  4. TRANSCRIPTION (Local Runner)                                   │
│     ├── Get audio duration (ffprobe)                               │
│     ├── IF duration > 600s: Chunking (fixed-length)               │
│     │   ├── Split into 600s chunks with 15s overlap               │
│     │   ├── Process chunks in parallel (4 workers)                │
│     │   └── Merge with timestamp-based strategy                   │
│     └── ELSE: Standard transcription                              │
│         ├── Run faster-whisper on full file                       │
│         └── Extract segments with timestamps                      │
│                                                                     │
│  5. FORMATTING (Local Runner)                                      │
│     ├── Split text into chunks if > 10KB                           │
│     ├── Send to GLM-4.5-Air for formatting                        │
│     └── Fallback to original if GLM fails                          │
│                                                                     │
│  6. SUMMARIZATION (Local Runner)                                   │
│     ├── Send formatted text to GLM-4.5-Air                         │
│     └── Generate summary with key points                          │
│                                                                     │
│  7. RESULT UPLOAD (Local Runner → Remote Server)                   │
│     ├── POST https://w.198066.xyz/api/runner/jobs/{id}/complete   │
│     ├── Remote server saves to storage (4 gzip files)              │
│     ├── Remote server deletes audio from /app/data/uploads/       │
│     └── Updates: status=completed, completed_at=timestamp          │
│                                                                     │
│  8. VERIFICATION (Remote Server)                                   │
│     ├── Check storage files exist                                  │
│     ├── Verify database records                                    │
│     └── Confirm audio cleanup                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Debugging Workflow

When errors occur, follow this debugging process:

### Step 1: Check Local Runner Logs

```bash
# View recent logs
docker logs whisper_runner --tail=100

# Follow logs in real-time
docker logs -f whisper_runner

# Search for errors
docker logs whisper_runner 2>&1 | grep -i "error\|exception\|fail"

# Search for specific job
docker logs whisper_runner 2>&1 | grep "1834a137-f121-47d0-89fb-8dde0a437e88"
```

### Step 2: Check Remote Server Logs

```bash
# SSH to production server
ssh root@192.3.249.169

# View server logs
cd /root/whisper_summarizer
docker logs whisper_server_prd --tail=100

# Follow logs in real-time
docker logs -f whisper_server_prd

# Search for errors
docker logs whisper_server_prd 2>&1 | grep -i "error\|exception\|fail"
```

### Step 3: Check Database State

```bash
# SSH to production server
ssh root@192.3.249.169

# Check transcription status
cd /root/whisper_summarizer
docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c \
  "SELECT id, status, stage, runner_id, error_message, started_at, completed_at
   FROM transcriptions
   WHERE id='<transcription_id>'"
```

### Step 4: Identify Error Type

Based on logs, identify the error category:

| Error Type | Location | Fix Strategy |
|------------|----------|--------------|
| Network/Connectivity | Runner | Check SERVER_URL, API key, firewall |
| Audio Download | Runner/Server | Verify file exists on server, check download endpoint |
| Transcription Failure | Runner | GPU memory, model loading, chunking issues |
| GLM API Failure | Runner | API quota, timeout, network |
| Database Error | Server | Connection, constraints, migrations |
| Storage Error | Server | Disk space, permissions |

### Step 5: Fix and Deploy

**For Runner Issues (Local)**:
```bash
# 1. Fix code locally
# 2. Rebuild runner image
./start_runner.sh build

# 3. Runner restarts automatically
# No need to push - runner runs locally
```

**For Server Issues (Remote)**:
```bash
# 1. Fix code locally
# 2. Build and push server image
docker build -t xyshyniaphy/whisper_summarizer-server:latest -f server/Dockerfile server
docker push xyshyniaphy/whisper_summarizer-server:latest

# 3. SSH to production server
ssh root@192.3.249.169
cd /root/whisper_summarizer

# 4. Pull and restart
git pull
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## Deployment Commands Reference

### Local Runner Management

```bash
# Start runner
./start_runner.sh

# Stop runner
./start_runner.sh down

# Rebuild runner
./start_runner.sh build

# View runner logs
docker logs whisper_runner --tail=50

# Follow runner logs
docker logs -f whisper_runner

# Check runner status
docker ps | grep whisper_runner
```

### Remote Server Management

```bash
# SSH to production
ssh root@192.3.249.169
cd /root/whisper_summarizer

# Check status
docker compose -f docker-compose.prod.yml ps

# View server logs
docker logs whisper_server_prd --tail=50

# Follow server logs
docker logs -f whisper_server_prd

# Pull and restart (after building locally)
git pull
docker compose -f docker-compose.prod.yml pull server
docker compose -f docker-compose.prod.yml up -d server

# Pull and restart all services
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Building Server Image (Local)

```bash
# Build server image
docker build -t xyshyniaphy/whisper_summarizer-server:latest -f server/Dockerfile server

# Push to Docker Hub
docker push xyshyniaphy/whisper_summarizer-server:latest
```

## Checkpoints

### CP1: Upload to Remote Server
- **Action**: Upload file via https://w.198066.xyz/ (web UI)
- **Expected**: File appears in transcriptions list
- **Remote Server Log**: "Audio file uploaded successfully: {filename} ({size} bytes)"
- **Verify**: Check https://w.198066.xyz/ for new transcription

### CP2: Job Pending State
- **Action**: Query remote database
- **Command**: `ssh root@192.3.249.169 "cd /root/whisper_summarizer && docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c \"SELECT id, status, stage FROM transcriptions ORDER BY created_at DESC LIMIT 1\""`
- **Expected**:
  - `status = "pending"`
  - `stage = "uploading"`
  - `runner_id = null`

### CP3: Runner Polls and Claims Job
- **Local Runner Log**: "Fetched 1 pending jobs"
- **Local Runner Log**: "Job {id} claimed successfully"
- **Remote Server Log**: "Job {id} claimed by runner runner-local-gpu-01"
- **Database Check**: `runner_id = "runner-local-gpu-01"`, `status = "processing"`

### CP4: Audio Download
- **Local Runner Log**: "Downloading audio from /api/runner/audio/{id}/download"
- **Local Runner Log**: "Downloaded audio for job {id}: /tmp/whisper_runner/{id}.m4a ({size} bytes)"
- **Remote Server Log**: "GET /api/runner/audio/{id}/download HTTP/1.1 200 OK"

### CP5: Transcription Decision
- **For 2_min.m4a** (< 600s):
  - **Log**: "Using standard transcription for 120s audio"
  - **NO**: [CHUNKING] logs
- **For 20_min, 60_min, 210_min** (> 600s):
  - **Log**: "Using chunked transcription for {seconds}s audio"
  - **YES**: [CHUNKING] logs present

### CP6: Chunking (for longer files)
- **Log**: "[CHUNKING] Splitting audio into chunks..."
- **Log**: "[CHUNKING] Created {N} chunks"
- **Note**: Fixed-length splitting (USE_VAD_SPLIT=false)
- **Expected Chunks**:
  - 20_min: ~2 chunks
  - 60_min: ~6 chunks
  - 210_min: ~21 chunks

### CP7: Parallel Transcription
- **Log**: "[PARALLEL TRANSCRIPTION] Starting {N} chunks with 4 workers"
- **Log**: "[CHUNK 0] Starting transcription"
- **Log**: "[CHUNK 0] ✓ Completed: {chars} chars, {segments} segments"
- **Log**: "[PARALLEL TRANSCRIPTION] Completed: {succeeded} succeeded, 0 failed"

### CP8: Merge Complete
- **Log**: "[CHUNKING] Merging results from {N} chunks..."
- **Log**: "[CHUNKING] Using timestamp-based merge"
- **Log**: "[CHUNKING] ✓ Merge complete: {chars} chars, {segments} segments"

### CP9: Formatting
- **Log**: "Step 2: Formatting with LLM..."
- **Log**: "[FORMAT] Calling GLM API for chunk ({N} chars)"
- **Log**: "[FORMAT] GLM returned {N} chars"
- **Log**: "Formatting complete: {original} -> {formatted} chars"

### CP10: Result Upload
- **Local Runner Log**: "Job {id} completed successfully"
- **Local Runner Log**: "Completed successfully in {seconds}s"
- **Remote Server Log**: "POST /api/runner/jobs/{id}/complete HTTP/1.1 200 OK"
- **Remote Server Log**: "Updating transcription status: processing -> completed"

### CP11: Storage Files Created (Remote)
- **Action**: Check remote server storage
- **Command**: `ssh root@192.3.249.169 "cd /root/whisper_summarizer && docker exec whisper_server_prd ls -lh /app/data/transcribes/ | grep {id}"`
- **Expected Files**:
  - `{id}.txt.gz` - Original transcribed text
  - `{id}.segments.json.gz` - Segments for SRT
  - `{id}.original.json.gz` - Full Whisper output
  - `{id}.formatted.txt.gz` - GLM-formatted text

### CP12: Audio Cleanup (Remote)
- **Action**: Verify audio file deleted
- **Command**: `ssh root@192.3.249.169 "cd /root/whisper_summarizer && docker exec whisper_server_prd ls -lh /app/data/uploads/ | grep {id}"`
- **Expected**: No file found (deleted after processing)

### CP13: Final Database State (Remote)
- **Action**: Query final state
- **Command**: `ssh root@192.3.249.169 "cd /root/whisper_summarizer && docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c \"SELECT id, status, stage, runner_id, processing_time_seconds, error_message FROM transcriptions WHERE id='{id}'\""`
- **Expected**:
  - `status = "completed"`
  - `stage = "completed"`
  - `processing_time_seconds` is set
  - `error_message = null`

## Test Execution Procedure

### Prerequisites

1. **Local Runner Ready**:
   ```bash
   ./start_runner.sh
   docker logs -f whisper_runner  # Verify polling starts
   ```

2. **Remote Server Running**:
   ```bash
   ssh root@192.3.249.169
   cd /root/whisper_summarizer
   docker compose -f docker-compose.prod.yml ps
   ```

3. **Verify Connectivity**:
   ```bash
   # From local machine, test API access
   curl https://w.198066.xyz/api/runner/jobs?status=pending&limit=1 \
     -H "Authorization: Bearer YOUR_RUNNER_API_KEY"
   ```

### Test Execution

1. **Upload Test File**:
   - Option A: Use web UI at https://w.198066.xyz/
   - Option B: Use curl with auth token
   - Option C: Use frontend upload feature

2. **Get Transcription ID**:
   - From web UI: Copy ID from URL
   - From API: Check response from upload
   - From database: `ORDER BY created_at DESC LIMIT 1`

3. **Monitor Local Runner**:
   ```bash
   docker logs -f whisper_runner | grep -E "Fetched|Processing|Completed|ERROR"
   ```

4. **Monitor Remote Server** (separate terminal):
   ```bash
   ssh root@192.3.249.169
   cd /root/whisper_summarizer
   docker logs -f whisper_server_prd
   ```

5. **Wait for Completion**:
   - 2_min: ~10-20 seconds
   - 20_min: ~30-60 seconds
   - 60_min: ~90-120 seconds
   - 210_min: ~5-7 minutes

6. **Verify Result**:
   - Check web UI: https://w.198066.xyz/
   - Check database state
   - Verify storage files

### Quick Verification Commands

```bash
# Check job status
curl https://w.198066.xyz/api/transcriptions/{id} \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check runner is processing
docker logs whisper_runner --tail=20 | grep -E "Processing|Completed"

# Check server logs (remote)
ssh root@192.3.249.169 \
  "docker logs whisper_server_prd --tail=20 | grep -E '{id}|upload|complete'"

# Quick database check
ssh root@192.3.249.169 \
  "docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c \
   \"SELECT status, stage, processing_time_seconds FROM transcriptions WHERE id='{id}'\""
```

## Error Scenarios and Solutions

### Scenario 1: Runner Cannot Connect to Server

**Symptoms**:
- Runner log: "Connection refused" or "Network unreachable"
- Runner log: "Max retries exceeded"

**Debug**:
```bash
# Test connectivity from local machine
curl -v https://w.198066.xyz/api/runner/jobs?status=pending

# Check runner env
docker exec whisper_runner env | grep -E "SERVER_URL|RUNNER_API_KEY"

# Check firewall
ping w.198066.xyz
telnet w.198066.xyz 443
```

**Solutions**:
1. Check `SERVER_URL=https://w.198066.xyz` in `runner/.env`
2. Verify `RUNNER_API_KEY` matches remote server
3. Check internet connectivity
4. Verify DNS resolution

### Scenario 2: Audio Download Fails

**Symptoms**:
- Runner log: "Audio file not found"
- Runner log: "HTTP 404" on download

**Debug**:
```bash
# Check if file exists on remote server
ssh root@192.3.249.169 \
  "docker exec whisper_server_prd ls -lh /app/data/uploads/ | grep {id}"

# Check database file_path field
ssh root@192.3.249.169 \
  "docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c \
   \"SELECT file_path FROM transcriptions WHERE id='{id}'\""
```

**Solutions**:
1. Verify upload completed successfully
2. Check storage mount on remote server
3. Re-upload file if missing

### Scenario 3: Transcription Fails

**Symptoms**:
- Runner log: "CUDA out of memory"
- Runner log: "WhisperError"
- Runner log: "Process failed after N retries"

**Debug**:
```bash
# Check GPU status
nvidia-smi

# Check runner logs
docker logs whisper_runner 2>&1 | grep -A 10 "ERROR\|Exception"

# Test with smaller file
# Upload 2_min.m4a and verify it works
```

**Solutions**:
1. Reduce `MAX_CONCURRENT_CHUNKS` in `runner/.env`
2. Reduce `CHUNK_SIZE_MINUTES`
3. Close other GPU applications
4. Restart runner: `./start_runner.sh down && ./start_runner.sh`

### Scenario 4: GLM API Fails

**Symptoms**:
- Runner log: "GLM API timeout"
- Runner log: "GLM formatting failed"
- Runner log: "Rate limit exceeded"

**Debug**:
```bash
# Check GLM API key
docker exec whisper_runner env | grep GLM_API_KEY

# Test GLM API directly
curl -X POST https://api.z.ai/api/paas/v4/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"GLM-4.5-Air","messages":[{"role":"user","content":"test"}]}'
```

**Solutions**:
1. Verify `GLM_API_KEY` is valid
2. Check API quota/balance
3. Formatting fallback should work (non-blocking)
4. Wait and retry for rate limits

### Scenario 5: Result Upload Fails

**Symptoms**:
- Runner log: "Failed to upload result"
- Runner log: "HTTP 500" on complete endpoint
- Status stuck at "processing"

**Debug**:
```bash
# Check remote server logs
ssh root@192.3.249.169 \
  "docker logs whisper_server_prd --tail=50 | grep -A 10 ERROR"

# Check database connectivity
ssh root@192.3.249.169 \
  "docker compose -f docker-compose.prod.yml ps"

# Check disk space
ssh root@192.3.249.169 \
  "df -h /app/data"
```

**Solutions**:
1. Fix server code (build, push, remote pulls)
2. Check database connection
3. Verify storage permissions
4. Reset job: `UPDATE transcriptions SET status='pending', ...`

## Success Criteria

### Test PASSED if:

For each test file (2_min, 20_min, 60_min, 210_min):

#### Upload Phase
- [ ] File uploaded successfully to https://w.198066.xyz/
- [ ] Database record created with status="pending"
- [ ] file_path set correctly

#### Processing Phase
- [ ] Local runner polls and claims job
- [ ] Audio downloaded to /tmp/whisper_runner/
- [ ] Transcription completes (standard or chunked)
- [ ] Formatting completes (GLM or fallback)
- [ ] Summarization completes
- [ ] Result uploaded to remote server

#### Completion Phase
- [ ] Remote database shows status="completed"
- [ ] processing_time_seconds is set
- [ ] All 4 storage files created on remote server:
  - [ ] {id}.txt.gz
  - [ ] {id}.segments.json.gz
  - [ ] {id}.original.json.gz
  - [ ] {id}.formatted.txt.gz
- [ ] Original audio deleted from /app/data/uploads/
- [ ] error_message = null

#### Performance
- [ ] Processing time within expected range
- [ ] No significant memory leaks
- [ ] GPU utilization efficient

### Test FAILED if:

#### Critical Failures
- [ ] Any file fails to reach "completed" status
- [ ] Runner cannot connect to remote server
- [ ] Audio download fails
- [ ] Transcription crashes
- [ ] Result upload fails

#### Data Integrity
- [ ] Storage files missing or corrupted
- [ ] Database records inconsistent
- [ ] Audio file not cleaned up

#### Performance
- [ ] Processing significantly slower than expected
- [ ] GPU OOM errors
- [ ] Memory exhaustion

## Results Recording Template

For each test file, record:

```markdown
### Test: {filename}

**Upload Time**: {timestamp}
**Transcription ID**: {id}

#### Timing
- Upload to Pending: {seconds}s
- Pending to Processing: {seconds}s
- Processing Time: {seconds}s
- Total End-to-End: {seconds}s

#### Results
- Chunks: {N} (or "standard")
- Characters: {N}
- Segments: {N}
- Language: {code}

#### Storage Files
- [ ] txt.gz
- [ ] segments.json.gz
- [ ] original.json.gz
- [ ] formatted.txt.gz

#### Status
- Database: {status}
- Stage: {stage}
- Error: {message if any}

#### Logs
- Runner: {key log excerpt}
- Server: {key log excerpt}

#### Notes
{any observations or issues}
```

## Architecture Summary

### Why This Architecture Works

**Local Runner Benefits**:
- Full GPU control (RTX 3080)
- Direct debugging access
- No remote GPU costs
- Instant code iterations

**Remote Server Benefits**:
- Always available
- Shared storage
- Database persistence
- User authentication

**Communication Flow**:
1. Server manages queue, authentication, storage
2. Runner polls for work (firewall-friendly)
3. Audio transfer via HTTPS (secure, reliable)
4. Result upload completes the cycle

### Scaling Considerations

**Current**: 1 local runner → 1 remote server

**Future**: N runners → 1 remote server
- Add more runners without server changes
- Each runner has unique RUNNER_ID
- Server distributes work automatically
- Runners can be in different locations

### Deployment Workflow

```
Local Development:
1. Code changes
2. Test locally
3. Commit to git

Server Deployment:
1. Build image locally: docker build -t xyshyniaphy/whisper_summarizer-server:latest
2. Push to registry: docker push xyshyniaphy/whisper_summarizer-server:latest
3. SSH to remote: ssh root@192.3.249.169
4. Pull code: git pull
5. Pull image: docker compose -f docker-compose.prod.yml pull
6. Restart: docker compose -f docker-compose.prod.yml up -d

Runner Deployment:
1. Code changes
2. Rebuild locally: ./start_runner.sh build
3. Auto-restarts with new code
```

---

**Document Version**: 1.0
**Created**: 2026-01-10
**Status**: Ready for execution
