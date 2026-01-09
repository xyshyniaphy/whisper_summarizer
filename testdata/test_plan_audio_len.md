# Audio Length Test Plan

## Overview

Test the transcription system with audio files of varying lengths to verify:
- Chunking logic triggers correctly based on audio duration
- Performance scales appropriately with file size
- All process stages complete successfully
- Logs contain expected milestone messages
- Error handling works correctly

**IMPORTANT**: Test files sequentially, no parallel execution.

## Test Environment

### System Architecture
```
Server (API, Database, Job Queue) → Runner (GPU Worker, faster-whisper, GLM)
     ↓                                      ↓
PostgreSQL 18                        Local Filesystem Storage
                                      /app/data/transcribes/
```

**Key Points**:
- **Server**: Lightweight FastAPI server (~150MB), handles auth, database, job queue
- **Runner**: GPU worker with faster-whisper + GLM-4.5-Air (~8GB)
- **Communication**: HTTP-based job queue with API key authentication
- **Storage**: Local filesystem with gzip compression (4 files per transcription)
- **Chunking**: Runner-specific feature, VAD-based splitting with LCS merge

### System Configuration
```
GPU: RTX 3080 with cuDNN
Backend: faster-whisper with CTranslate2
Chunk Size Threshold: 10 minutes (600 seconds)
Max Concurrent Chunks: 4 (GPU) / 2 (CPU)
Merge Strategy: LCS (text-based alignment)
```

### Runner Settings (.env in runner container)
```bash
# Server Connection
SERVER_URL=http://localhost:8000
RUNNER_API_KEY=your-super-secret-runner-api-key-here
RUNNER_ID=runner-gpu-01

# Polling Configuration
POLL_INTERVAL_SECONDS=10
MAX_CONCURRENT_JOBS=4              # Max parallel jobs per runner
JOB_TIMEOUT_SECONDS=3600           # Max time per job

# faster-whisper Configuration
FASTER_WHISPER_DEVICE=cuda              # cuda (GPU) or cpu
FASTER_WHISPER_COMPUTE_TYPE=int8_float16 # int8_float16 (GPU), int8 (CPU)
FASTER_WHISPER_MODEL_SIZE=large-v3-turbo
WHISPER_LANGUAGE=zh
WHISPER_THREADS=4

# Audio Chunking (Runner-side)
ENABLE_CHUNKING=true
CHUNK_SIZE_MINUTES=10
CHUNK_OVERLAP_SECONDS=15
MAX_CONCURRENT_CHUNKS=4           # GPU: 4-8, CPU: 2
USE_VAD_SPLIT=true
MERGE_STRATEGY=lcs

# GLM API
GLM_API_KEY=your-glm-api-key
GLM_MODEL=GLM-4.5-Air
GLM_BASE_URL=https://api.z.ai/api/paas/v4/
REVIEW_LANGUAGE=zh
```

### Server Settings (.env in server container)
```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/whisper_summarizer

# Supabase Auth
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Runner Authentication
RUNNER_API_KEY=your-super-secret-runner-api-key-here

# CORS
CORS_ORIGINS=http://localhost:3000
```

## Test Files

| File | Size | Duration | Chunking | Expected Chunks |
|------|------|----------|----------|-----------------|
| 2_min.m4a | 0.08 MB | ~120 sec | NO | 1 (standard) |
| 20_min.m4a | 4.82 MB | ~1200 sec | YES | ~2 chunks |
| 60_min.m4a | 14.58 MB | ~3600 sec | YES | ~6 chunks |
| 210_min.m4a | 51.8 MB | ~12600 sec | YES | ~21 chunks |

## Process Flow

```
┌───────────────────────────────────────────────────────────────────────┐
│                    TRANSCRIPTION PROCESS FLOW                          │
├───────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  0. USER UPLOAD STAGE (Server)                                         │
│     ├── POST /api/audio/upload (Server endpoint)                       │
│     ├── Create transcription record in DB (status: pending)           │
│     ├── Save file to /app/data/uploads/ (Server)                      │
│     └── Return 201 Created with transcription ID                      │
│                                                                         │
│  1. RUNNER POLLING (Runner)                                            │
│     ├── Runner polls: GET /api/runner/jobs?status=pending              │
│     ├── Server returns pending jobs (auth: RUNNER_API_KEY)             │
│     └── Runner claims job: POST /api/runner/jobs/{id}/start            │
│                                                                         │
│  2. AUDIO DOWNLOAD (Runner)                                            │
│     ├── Runner downloads audio: GET /api/runner/audio/{id}             │
│     ├── Server streams file from /app/data/uploads/                    │
│     └── Runner saves to local /app/data/uploads/                       │
│                                                                         │
│  3. TRANSCRIBING STAGE (Runner)                                         │
│     ├── Get audio duration (ffprobe)                                   │
│     ├── Decision: duration > 600s? → Use chunking                      │
│     │                                                                   │
│     ├── IF NO CHUNKING (2_min.m4a):                                    │
│     │   ├── Run faster-whisper on full file                            │
│     │   ├── Extract segments with timestamps                           │
│     │   └── Return transcription result                                │
│     │                                                                   │
│     └── IF CHUNKING (20_min, 60_min, 210_min):                         │
│         ├── Detect silence points (VAD)                                │
│         ├── Split audio into chunks with overlap                       │
│         ├── Process chunks in parallel (ThreadPoolExecutor)            │
│         │   ├── Chunk 0: faster-whisper → segments                    │
│         │   ├── Chunk 1: faster-whisper → segments                    │
│         │   └── Chunk N: faster-whisper → segments                    │
│         └── Merge results using LCS (text-based alignment)             │
│                                                                         │
│  4. FORMATTING STAGE (Runner)                                          │
│     ├── Call TextFormattingService with raw transcription             │
│     ├── Split into chunks if > MAX_FORMAT_CHUNK (10KB)                 │
│     ├── Send chunks to GLM-4.5-Air for formatting                      │
│     │   ├── [FORMAT] Calling GLM API for chunk ({N} chars)             │
│     │   └── [FORMAT] GLM returned {N} chars                            │
│     ├── Merge formatted chunks                                         │
│     └── Fallback to original if formatting fails                        │
│                                                                         │
│  5. SUMMARIZING STAGE (Runner)                                          │
│     ├── Call GLM API with formatted (or original) text                 │
│     ├── Generate summary with key points                               │
│     └── Return summary text                                            │
│                                                                         │
│  6. RESULT UPLOAD (Runner → Server)                                    │
│     ├── POST /api/runner/jobs/{id}/complete                            │
│     │   {                                                               │
│     │     "text": "...",               // Original transcribed text     │
│     │     "segments": [...],          // Timestamps for SRT            │
│     │     "original_output": {...},   // Full Whisper output           │
│     │     "formatted_text": "...",    // GLM-formatted text            │
│     │     "summary_text": "...",      // GLM summary                   │
│     │     "language": "zh",           // Detected language             │
│     │     "duration_seconds": 1200    // Audio duration                │
│     │   }                                                               │
│     ├── Server saves to database and storage                           │
│     │   ├── text → {id}.txt.gz                                         │
│     │   ├── segments → {id}.segments.json.gz                           │
│     │   ├── original_output → {id}.original.json.gz                    │
│     │   └── formatted_text → {id}.formatted.txt.gz                     │
│     ├── Update transcription status: pending → completed              │
│     └── Delete audio file from server (/app/data/uploads/{id})         │
│                                                                         │
│  7. CLIENT POLLING (Frontend)                                           │
│     ├── GET /api/transcriptions/{id}                                   │
│     ├── Server returns transcription with status=completed             │
│     └── Frontend displays results                                      │
│                                                                         │
└───────────────────────────────────────────────────────────────────────┘
```

**Key Differences from Monolithic Architecture**:
- **Server/Runner Split**: Server handles API/auth/storage, Runner handles GPU processing
- **Job Queue**: Runner polls for jobs instead of background tasks on server
- **Audio Cleanup**: Server deletes audio after runner downloads it (saves space)
- **Storage**: Server stores 4 gzip-compressed files per transcription
- **No Blocking**: Upload returns immediately, processing happens asynchronously

## Checkpoints

### CP1: Upload Request (Server)
- **Action**: POST /api/audio/upload with file
- **Expected**: HTTP 201 Created
- **Verify**: Response contains `id`, `file_name`, `status=\"pending\"`, `stage=null`
- **Server Log**: "Audio file uploaded successfully: {filename} ({size} bytes)"

### CP2: Database Record Created (Server)
- **Action**: Query `transcriptions` table by ID
- **Expected**: Record exists with:
  - `user_id` matches uploaded user
  - `file_name` matches uploaded file
  - `file_path` is set (in /app/data/uploads/)
  - `status = "pending"`
  - `runner_id = null`
  - `started_at = null`
  - `error_message = null`

### CP2a: Job Queued (Server → Runner)
- **Runner Log**: "Polling for pending jobs..."
- **Server Log**: "Runner {runner_id} requesting jobs"
- **Runner Action**: GET /api/runner/jobs?status=pending&limit=10
- **Server Response**: Returns job with `{id, file_name, file_path}`
- **Runner Action**: POST /api/runner/jobs/{id}/start
- **Server Log**: "Job {id} claimed by runner {runner_id}"
- **Database Check**: `runner_id` is set, `status = "processing"`, `started_at` is set

### CP2b: Audio Download (Runner)
- **Runner Action**: GET /api/runner/audio/{id}
- **Server Log**: "Streaming audio file for job {id}"
- **Runner Log**: "Downloaded audio file: {filename} ({size} bytes)"
- **Verify**: Audio file saved to runner's /app/data/uploads/

### CP3: Transcription Started (Runner)
- **Runner Log**: "Starting transcription for job {id}"
- **Runner Log**: "Audio duration: {seconds} seconds ({minutes} minutes)"
- **Verify**: Duration matches expected (120s, 1200s, 3600s, 12600s)
- **Action**: Query `transcriptions` table by ID
- **Expected**: Record exists with correct `user_id`, `file_name`
- **Verify**: `file_path` is set, `stage="uploading"`

### CP4: Chunking Decision (Runner)
- **For 2_min.m4a** (duration < 600s):
  - **Runner Log**: "Using standard transcription (duration: 120s < 600s threshold)"
  - **NO**: [CHUNKING] logs should appear
- **For 20_min.m4a, 60_min.m4a, 210_min.m4a** (duration > 600s):
  - **Runner Log**: "Using chunked transcription (duration: {seconds}s > 600s threshold)"
  - **YES**: [CHUNKING] logs should appear

### CP5: Chunk Creation (for 20_min, 60_min, 210_min)
- **Runner Log**: "[CHUNKING] Splitting audio into chunks..."
- **Runner Log**: "[CHUNKING] Target chunk size: 600 seconds (10 minutes)"
- **Runner Log**: "[CHUNKING] Overlap: 15 seconds"
- **If USE_VAD_SPLIT=true**:
  - **Runner Log**: "VAD splitting: found {N} silence regions, {M} split points"
  - **Verify**: Split points at silence (not hard cuts)
- **Runner Log**: "[CHUNKING] Created {N} chunks"
- **For 20_min (1200s)**: N ≈ 2 chunks (600s + 600s with overlap)
- **For 60_min (3600s)**: N ≈ 6 chunks
- **For 210_min (12600s)**: N ≈ 21 chunks

### CP6: Parallel Transcription Start (for chunking)
- **Runner Log**: "[PARALLEL TRANSCRIPTION] Starting {N} chunks with {M} workers"
- **Verify**: M = MAX_CONCURRENT_CHUNKS (4 for GPU, 2 for CPU)
- **Note**: ThreadPoolExecutor manages concurrent chunk processing

### CP7: Individual Chunk Progress (for chunking)
- **Runner Log**: "[CHUNK 0] Starting transcription"
- **Runner Log**: "[CHUNK 0] Path: /app/data/uploads/chunk_000.wav"
- **Runner Log**: "[CHUNK 0] Duration: {N}s"
- **Runner Log**: "[CHUNK 0] Processing with faster-whisper..."
- **Runner Log**: "[CHUNK 0] ✓ Completed: {chars} chars, {segments} segments"
- **Repeat** for each chunk (0, 1, 2, ... N-1)
- **Verify**: All chunks complete successfully

### CP8: Parallel Transcription Complete (for chunking)
- **Runner Log**: "[PARALLEL TRANSCRIPTION] Completed: {succeeded} succeeded, {failed} failed out of {total}"
- **Verify**: failed = 0, succeeded = total

### CP9: Chunk Merge (for chunking)
- **Runner Log**: "[CHUNKING] Merging results from {N} chunks..."
- **If MERGE_STRATEGY=lcs**:
  - **Runner Log**: "Using LCS (Longest Common Subsequence) merge strategy"
  - **Verify**: Text-based alignment removes duplicate content in overlaps
- **Runner Log**: "[CHUNKING] ✓ Merge complete: {chars} chars, {segments} segments"
- **Verify**: Final character count is reasonable (no huge duplicates)

### CP10: Transcription Complete (ALL files)
- **Runner Log**: "Transcription completed for job {id}"
- **Runner Log**: "Total segments: {N}"
- **Runner Log**: "Total characters: {N}"
- **Runner Log**: "Detected language: {language_code} (confidence: {p})"

### CP11: Formatting Stage (Runner)
- **Runner Log**: "Starting text formatting for: {transcription_id}"
- **Expected**: TextFormattingService is initialized with GLM client
- **Runner Log**: "[FORMAT] Input text length: {N} characters"
- **If text > MAX_FORMAT_CHUNK (10KB)**:
  - **Runner Log**: "[FORMAT] Splitting into {N} chunks for formatting"
  - **Runner Log**: "[FORMAT] Processing chunk 1/{N} ({start}-{end} chars)"
- **Runner Log**: "[FORMAT] Calling GLM-4.5-Air API for chunk ({N} chars)"
- **Expected**: GLM API is called with formatting prompt
- **Runner Log**: "[FORMAT] GLM returned {N} chars"
- **Expected**: Formatted text has proper punctuation and spacing
- **If multiple chunks**:
  - **Runner Log**: "[FORMAT] Merging {N} formatted chunks"
- **On GLM failure**:
  - **Runner Log**: "[FORMAT] GLM formatting failed: {error}"
  - **Runner Log**: "[FORMAT] Falling back to original text"
- **Runner Log**: "Text formatting completed: {id} | Original: {N} chars -> Formatted: {M} chars"
- **Verify**: Formatting is non-blocking (failure doesn't stop workflow)

### CP12: Summarization Stage (Runner)
- **Runner Log**: "Starting summarization for: {transcription_id}"
- **Expected**: GLM client initialized for summarization
- **Runner Log**: "[SUMMARY] Input text: formatted ({N} chars)"
- **Runner Log**: "[SUMMARY] Calling GLM-4.5-Air API"
- **Expected**: GLM API called with summarization prompt
- **Runner Log**: "[SUMMARY] GLM returned summary: {N} chars"
- **Runner Log**: "Summarization successful: {id} | Tokens: {N} | Time: {M}ms"
- **Expected**: Summary contains key points from transcription

### CP13: Result Upload (Runner → Server)
- **Runner Action**: POST /api/runner/jobs/{id}/complete with JSON payload
- **Payload Contains**:
  - `text`: Original transcribed text
  - `segments`: Array of {start, end, text} for SRT
  - `original_output`: Full Whisper output (debug)
  - `formatted_text`: GLM-formatted text
  - `summary_text`: GLM summary
  - `language`: Detected language code
  - `duration_seconds`: Audio duration
- **Server Log**: "Received completion for job {id} from runner {runner_id}"
- **Server Log**: "Saving transcription text to storage: {id}.txt.gz"
- **Server Log**: "Saving segments to storage: {id}.segments.json.gz"
- **Server Log**: "Saving original output to storage: {id}.original.json.gz"
- **Server Log**: "Saving formatted text to storage: {id}.formatted.txt.gz"
- **Server Log**: "Updating transcription status: pending -> completed"
- **Server Log**: "Deleting audio file: /app/data/uploads/{id}"
- **Database Check**:
  - `status = "completed"`
  - `completed_at` is set
  - `storage_path` is set
  - `error_message = null`

### CP14: Client Polling (Frontend)
- **Frontend Action**: Poll GET /api/transcriptions/{id}
- **Server Response**: Returns transcription with `status = "completed"`
- **Frontend**: Displays results, enables downloads
- **Verify**: Can download TXT, SRT, and formatted versions

### CP15: Storage Verification (Server)
- **Action**: Check /app/data/transcribes/ directory
- **Verify**: All four storage files exist:
  - `{id}.txt.gz` (original transcribed text)
  - `{id}.segments.json.gz` (segments with timestamps for SRT)
  - `{id}.original.json.gz` (full Whisper output for debugging)
  - `{id}.formatted.txt.gz` (GLM-formatted text)
- **Content Checks**:
  - `.txt.gz`: Decompresses to non-empty text
  - `.segments.json.gz`: Valid JSON with start/end/text fields
  - `.original.json.gz`: Valid JSON with full Whisper output
  - `.formatted.txt.gz`: Decompresses to formatted text (or original if GLM failed)

### CP16: Final Database Verification
- **Action**: Query `transcriptions` table by ID
- **Verify**:
  - `status = "completed"`
  - `storage_path` is set
  - `language` is detected
  - `duration_seconds` matches audio
  - `error_message = null`
  - `completed_at` timestamp is set
  - `runner_id` is set
- **Query** `summaries` table:
  - At least one entry for this `transcription_id`
  - `summary_text` is non-empty
  - `model_name = "GLM-4.5-Air"` (or configured model)
  - `created_at` is set
- **Action**: Poll GET /api/transcriptions/{id}
- **Expected**: `stage = "completed"`
- **Verify**: All fields populated:
  - `text` is accessible (via .text property that decompresses from storage)
  - `storage_path` is set (to .txt.gz file)
  - `language` (detected language code)
  - `duration_seconds` (matches audio duration)
  - `error_message = null`
  - `completed_at` (timestamp set)
  - `summaries` relationship has at least one entry

## Performance Benchmarks (GPU)

| Audio Duration | Expected Transcription Time |
|----------------|------------------------------|
| 2 minutes | ~2-5 seconds |
| 20 minutes | ~30-60 seconds |
| 60 minutes | ~90-120 seconds |
| 210 minutes | ~300-420 seconds |

**Note**: These are approximate for GPU (RTX 3080) with cuDNN. Speedup ~40-60x real-time.

## Success Criteria

### Must Pass (Server)
- [ ] HTTP 201 response on upload
- [ ] `status` transitions: pending → processing → completed
- [ ] `runner_id` is set after job claimed
- [ ] `started_at` timestamp is set when processing begins
- [ ] `completed_at` timestamp is set when finished
- [ ] `error_message = null`

### Must Pass (Runner)
- [ ] Runner polls and claims job successfully
- [ ] Audio file downloaded from server
- [ ] Transcription completes (chunking or standard)
- [ ] Formatting completes (with fallback on GLM failure)
- [ ] Summarization completes with valid summary
- [ ] Result uploaded to server via `/api/runner/jobs/{id}/complete`

### Storage Files Verification (Server)
- [ ] `{id}.txt.gz` exists (original transcribed text)
- [ ] `{id}.segments.json.gz` exists (segments with timestamps for SRT)
- [ ] `{id}.original.json.gz` exists (full Whisper output for debugging)
- [ ] `{id}.formatted.txt.gz` exists (GLM-formatted text with punctuation)
- [ ] Original audio file deleted from `/app/data/uploads/{id}`

### Database Verification (Server)
- [ ] `transcriptions` table:
  - [ ] `status = "completed"`
  - [ ] `storage_path` is set
  - [ ] `language` is detected
  - [ ] `duration_seconds` matches audio
  - [ ] `runner_id` is set
  - [ ] `error_message = null`
  - [ ] `completed_at` timestamp is set
- [ ] `summaries` table:
  - [ ] At least one entry for this `transcription_id`
  - [ ] `summary_text` is non-empty
  - [ ] `model_name` is recorded (e.g., "GLM-4.5-Air")
  - [ ] `created_at` timestamp is set

### Formatting Stage (Runner)
- [ ] "Starting text formatting for: {id}" log present
- [ ] "[FORMAT] Input text length: {N} characters" log present
- [ ] "[FORMAT] Calling GLM-4.5-Air API" log present
- [ ] "[FORMAT] GLM returned {N} chars" log present
- [ ] "Text formatting completed" log present
- [ ] If GLM fails: "Falling back to original text" log present
- [ ] Formatted text file exists and is readable

### Summarization Stage (Runner)
- [ ] "Starting summarization for: {id}" log present
- [ ] "[SUMMARY] Input text: formatted ({N} chars)" log present
- [ ] "[SUMMARY] Calling GLM-4.5-Air API" log present
- [ ] "[SUMMARY] GLM returned summary: {N} chars" log present
- [ ] "Summarization successful: {id} | Tokens: {N} | Time: {M}ms" log present

### SRT Download Verification (Server API)
- [ ] GET /api/transcriptions/{id}/download?format=srt works
- [ ] SRT file contains proper timestamps (not fake ones)
- [ ] SRT file format is valid (sequential numbering, time codes)

### Chunking-Specific (20_min, 60_min, 210_min)
- [ ] [CHUNKING] logs present in runner logs
- [ ] [PARALLEL TRANSCRIPTION] logs present
- [ ] Multiple [CHUNK N] logs present
- [ ] VAD splitting logs present (if USE_VAD_SPLIT=true)
- [ ] Merge completion log present with LCS strategy mentioned

### Non-Chunking (2_min)
- [ ] NO [CHUNKING] logs in runner logs
- [ ] NO [PARALLEL TRANSCRIPTION] logs
- [ ] Standard transcription completion log present
- [ ] Total segments and characters logged

### Log Verification
- [ ] No unbounded log outputs (all < 5000 bytes for large data)
- [ ] All milestone logs present
- [ ] No ERROR or WARNING logs (unless expected)

## Expected Log Patterns

## Server Logs (All Files)
```
[INFO] Audio file uploaded successfully: {filename} ({size} bytes)
[INFO] Created transcription record: {id}
[INFO] Runner {runner_id} requesting jobs
[INFO] Job {id} claimed by runner {runner_id}
[INFO] Streaming audio file for job {id}
[INFO] Received completion for job {id} from runner {runner_id}
[INFO] Saving transcription text to storage: {id}.txt.gz
[INFO] Saving segments to storage: {id}.segments.json.gz
[INFO] Saving original output to storage: {id}.original.json.gz
[INFO] Saving formatted text to storage: {id}.formatted.txt.gz
[INFO] Updating transcription status: pending -> completed
[INFO] Deleting audio file: /app/data/uploads/{id}
```

### Runner Logs - For 2_min.m4a (NO Chunking)
```
[INFO] Polling for pending jobs...
[INFO] Claimed job {id}: {filename}
[INFO] Downloaded audio file: {filename} ({size} bytes)
[INFO] Starting transcription for job {id}
[INFO] Audio duration: 120 seconds (2.0 minutes)
[INFO] Using standard transcription (duration: 120s < 600s threshold)
[INFO] Processing with faster-whisper (large-v3-turbo, cuda)
[INFO] Transcription completed for job {id}
[INFO] Total segments: {N}
[INFO] Total characters: {N}
[INFO] Detected language: zh (confidence: 0.95)
[INFO] Starting text formatting for: {id}
[INFO] [FORMAT] Input text length: {N} characters
[INFO] [FORMAT] Calling GLM-4.5-Air API for chunk ({N} chars)
[INFO] [FORMAT] GLM returned {N} chars
[INFO] Text formatting completed: {id} | Original: {N} chars -> Formatted: {M} chars
[INFO] Starting summarization for: {id}
[INFO] [SUMMARY] Input text: formatted ({N} chars)
[INFO] [SUMMARY] Calling GLM-4.5-Air API
[INFO] [SUMMARY] GLM returned summary: {N} chars
[INFO] Summarization successful: {id} | Tokens: {N} | Time: {M}ms
[INFO] Uploading result to server: POST /api/runner/jobs/{id}/complete
```

### Runner Logs - For 20_min.m4a, 60_min.m4a, 210_min.m4a (WITH Chunking)
```
[INFO] Polling for pending jobs...
[INFO] Claimed job {id}: {filename}
[INFO] Downloaded audio file: {filename} ({size} bytes)
[INFO] Starting transcription for job {id}
[INFO] Audio duration: {seconds} seconds ({minutes} minutes)
[INFO] Using chunked transcription (duration: {seconds}s > 600s threshold)
[INFO] [CHUNKING] Splitting audio into chunks...
[INFO] [CHUNKING] Target chunk size: 600 seconds (10 minutes)
[INFO] [CHUNKING] Overlap: 15 seconds
[INFO] VAD splitting: found {N} silence regions, {M} split points
[INFO] [CHUNKING] Created {N} chunks
[INFO] [PARALLEL TRANSCRIPTION] Starting {N} chunks with {M} workers
[INFO] [CHUNK 0] Starting transcription
[INFO] [CHUNK 0] Path: /app/data/uploads/chunk_000.wav
[INFO] [CHUNK 0] Duration: {N}s
[INFO] [CHUNK 0] Processing with faster-whisper...
[INFO] [CHUNK 0] ✓ Completed: {N} chars, {M} segments
[INFO] [CHUNK 1] Starting transcription
[INFO] [CHUNK 1] Path: /app/data/uploads/chunk_001.wav
[INFO] [CHUNK 1] Duration: {N}s
[INFO] [CHUNK 1] Processing with faster-whisper...
[INFO] [CHUNK 1] ✓ Completed: {N} chars, {M} segments
...
[INFO] [PARALLEL TRANSCRIPTION] Completed: {succeeded} succeeded, 0 failed out of {total}
[INFO] [CHUNKING] Merging results from {N} chunks...
[INFO] Using LCS (Longest Common Subsequence) merge strategy
[INFO] [CHUNKING] ✓ Merge complete: {N} chars, {M} segments
[INFO] Transcription completed for job {id}
[INFO] Total segments: {N}
[INFO] Total characters: {N}
[INFO] Detected language: zh (confidence: 0.95)
[INFO] Starting text formatting for: {id}
[INFO] [FORMAT] Input text length: {N} characters
[INFO] [FORMAT] Splitting into {N} chunks for formatting
[INFO] [FORMAT] Processing chunk 1/{N} (0-10000 chars)
[INFO] [FORMAT] Calling GLM-4.5-Air API for chunk (10000 chars)
[INFO] [FORMAT] GLM returned 9800 chars
[INFO] [FORMAT] Processing chunk 2/{N} (10000-20000 chars)
...
[INFO] [FORMAT] Merging {N} formatted chunks
[INFO] Text formatting completed: {id} | Original: {N} chars -> Formatted: {M} chars
[INFO] Starting summarization for: {id}
[INFO] [SUMMARY] Input text: formatted ({N} chars)
[INFO] [SUMMARY] Calling GLM-4.5-Air API
[INFO] [SUMMARY] GLM returned summary: {N} chars
[INFO] Summarization successful: {id} | Tokens: {N} | Time: {M}ms
[INFO] Uploading result to server: POST /api/runner/jobs/{id}/complete
```

### On GLM Formatting Failure (Runner Logs)
```
[INFO] Starting text formatting for: {id}
[INFO] [FORMAT] Input text length: {N} characters
[INFO] [FORMAT] Calling GLM-4.5-Air API for chunk ({N} chars)
[ERROR] [FORMAT] GLM formatting failed: Connection timeout
[INFO] [FORMAT] Falling back to original text
[INFO] Text formatting completed: {id} | Original: {N} chars -> Formatted: {N} chars
```

### Storage Files Created (Server)
```
/app/data/transcribes/{id}.txt.gz                 (original text)
/app/data/transcribes/{id}.segments.json.gz       (segments for SRT)
/app/data/transcribes/{id}.original.json.gz       (debug output)
/app/data/transcribes/{id}.formatted.txt.gz       (formatted text)
```

**Note**: `/app/data/uploads/{id}` (original audio) is deleted after runner downloads it.

## Failure Scenarios

### Potential Failure Points
1. **Upload timeout** - Large files may timeout (mitigation: 300s timeout)
2. **Chunk creation failure** - FFmpeg errors during VAD splitting
3. **Transcription worker failure** - GPU OOM or CUDA errors
4. **Merge failure** - LCS algorithm issues
5. **Formatting failure** - GLM API errors, rate limits, or network errors (non-blocking)
6. **Summarization failure** - GLM API errors, rate limits, or network errors
7. **Database constraint violation** - Foreign key or unique violations
8. **Storage write failure** - Disk full or permission issues

### Formatting-Specific Failures (NEW)
- **GLM API timeout** - Formatting request times out (falls back to original)
- **GLM API rate limit** - Too many formatting requests (falls back to original)
- **GLM returns empty** - Model fails to format (falls back to original)
- **GLM returns truncated** - Model response cut off (falls back to original if < 50% length)

### Summarization-Specific Failures (ENHANCED)
- **GLM API timeout** - Summarization request times out (retries up to 3 times)
- **GLM API rate limit** - Too many summarization requests (retries with backoff)
- **Empty summary returned** - Model returns empty string (logs warning, continues)
- **Token limit exceeded** - Text too long for model (chunking should handle this)

### Graceful Degradation
- If chunk(s) fail, partial results should be saved
- Failed chunks should be logged with error details
- **Formatting failure is non-blocking**: Falls back to original text
- **Summarization failure**: Logs error but transcription completes
- `error_message` should be set on failure
- Stage should be "failed" only on unrecoverable transcription error

### Retry Logic
- MAX_RETRIES = 3 for transcription/summarization
- Exponential backoff between retries
- Semaphore prevents concurrent overload (AUDIO_PARALLELISM = 1)
- **Formatting**: Single attempt (no retry, falls back to original)
- **Summarization**: Retries up to 3 times with backoff

## Test Execution Procedure

### Prerequisites
1. **Server container running**:
   ```bash
   docker compose -f docker-compose.dev.yml up -d backend
   ```

2. **Runner container running**:
   ```bash
   docker compose -f docker-compose.runner.yml up -d runner
   ```

3. **Test user exists in database**:
   ```bash
   # Create test user if needed
   INSERT INTO users (id, email, is_active, is_admin)
   VALUES ('123e4567-e89b-42d3-a456-426614174000', 'test@example.com', true, false);
   ```

4. **Authentication**:
   - DISABLE_AUTH=true in server .env (development only)
   - OR valid Supabase auth token (production)

### Test Execution Steps

1. **Start monitoring logs** (separate terminals):
   ```bash
   # Server logs
   docker logs -f whisper_backend_dev
   
   # Runner logs
   docker logs -f whisper_runner_dev
   ```

2. **Upload test files sequentially** (NOT in parallel):
   ```bash
   # Use curl, Postman, or test script
   curl -X POST http://localhost:8000/api/audio/upload \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "file=@testdata/2_min.m4a"
   
   # Wait for completion before uploading next file
   # Poll status: GET /api/transcriptions/{id}
   ```

3. **Monitor stage transitions**:
   - Watch for status changes: pending → processing → completed
   - Verify runner claims job (runner_id set)
   - Check logs for chunking/formatting/summarization milestones

4. **Verify checkpoints**:
   - After each upload, verify CP1-CP4 before proceeding
   - Check storage files exist after completion
   - Verify database records are correct

### Monitoring Commands

```bash
# Check transcription status
curl http://localhost:8000/api/transcriptions/{id}

# Check storage files
docker exec whisper_backend_dev ls -lh /app/data/transcribes/

# Check database records
docker exec whisper_backend_dev python -c "
from app.db.session import SessionLocal
from app.models.transcription import Transcription
db = SessionLocal()
t = db.query(Transcription).first()
print(f'status={t.status}, runner_id={t.runner_id}')
"
```

## Results Recording

For each test file, record:

### Timing Metrics
- **Upload Time**: Time from POST request to 201 response
- **Job Claim Time**: Time from upload to runner claiming job
- **Transcription Time**: Time from job start to transcription complete
- **Formatting Time**: Time from transcription start to formatting complete
- **Summarization Time**: Time from formatting start to summarization complete
- **Upload Result Time**: Time from summarization complete to server storage
- **Total End-to-End Time**: Time from initial upload to completed status

### Transcription Metrics
- Number of chunks created (if applicable)
- Chunk duration and size (if chunking)
- Character count of original transcription
- Character count of formatted text
- Segment count (for SRT generation)
- Detected language and confidence score
- Audio duration (seconds)

### Formatting Metrics
- Format success/failure
- Formatting method (GLM success vs fallback)
- Character count reduction (original → formatted)
- Number of formatting chunks (if text > 10KB)

### Summarization Metrics
- Summary length (characters)
- Summary model used (GLM-4.5-Air)
- Token counts (input, output, total)
- Response time (ms)
- Retry attempts (if any)

### Storage Verification
- [ ] {id}.txt.gz (original transcribed text)
- [ ] {id}.segments.json.gz (segments for SRT)
- [ ] {id}.original.json.gz (debug output)
- [ ] {id}.formatted.txt.gz (GLM-formatted text)
- [ ] Original audio deleted from /app/data/uploads/

### Error Tracking
- Any ERROR or WARNING logs
- GLM formatting failures (with fallback)
- GLM summarization retries
- Chunk processing failures
- Network or timeout issues

### Log References
- Server log file path
- Runner log file path
- Relevant log line numbers for each checkpoint

## Exit Criteria

### Test PASSED

All four audio files (2_min, 20_min, 60_min, 210_min) must meet:

#### Server-Side Requirements
- [ ] HTTP 201 response on upload
- [ ] Status transitions: pending → processing → completed
- [ ] `runner_id` is set (job claimed by runner)
- [ ] `started_at` and `completed_at` timestamps set
- [ ] `error_message = null`
- [ ] All four storage files created:
  - [ ] {id}.txt.gz (original transcribed text)
  - [ ] {id}.segments.json.gz (segments for SRT)
  - [ ] {id}.original.json.gz (debug output)
  - [ ] {id}.formatted.txt.gz (GLM-formatted text)
- [ ] Original audio file deleted from /app/data/uploads/
- [ ] Database records correct:
  - [ ] `transcriptions` table: status, language, duration_seconds
  - [ ] `summaries` table: at least one summary entry

#### Runner-Side Requirements
- [ ] Runner polls and claims job successfully
- [ ] Audio file downloaded from server
- [ ] Transcription completes (with or without chunking)
- [ ] Formatting completes (GLM success OR fallback to original)
- [ ] Summarization completes with valid summary
- [ ] Result uploaded to server successfully

#### Chunking-Specific (20_min, 60_min, 210_min)
- [ ] [CHUNKING] logs present
- [ ] [PARALLEL TRANSCRIPTION] logs present
- [ ] Multiple [CHUNK N] logs present
- [ ] VAD splitting detected silence points
- [ ] LCS merge strategy used
- [ ] Merge removed duplicates from overlaps

#### Non-Chunking (2_min)
- [ ] NO [CHUNKING] logs
- [ ] NO [PARALLEL TRANSCRIPTION] logs
- [ ] Standard transcription completed

#### Performance Requirements
- [ ] Processing time within acceptable range (see benchmarks)
- [ ] No significant performance degradation
- [ ] GPU utilization efficient (chunking)

#### Log Requirements
- [ ] All milestone logs present (CP1-CP16)
- [ ] No unbounded log outputs (< 5000 bytes for large data)
- [ ] No unexpected ERROR or WARNING logs

#### Functionality Requirements
- [ ] SRT download returns valid subtitle format
- [ ] Formatted text has proper punctuation (if GLM succeeded)
- [ ] Summary contains key points from transcription
- [ ] Storage files decompress correctly

### Test FAILED

Test fails if ANY of these occur:

#### Critical Failures
- [ ] Any file fails to reach "completed" status
- [ ] `error_message` is set (unrecoverable error)
- [ ] Storage files missing or corrupted
- [ ] Database records inconsistent
- [ ] Runner fails to claim or process job

#### Transcription Failures
- [ ] Chunking logic behaves incorrectly
- [ ] Merge fails (duplicates, corruption)
- [ ] Language detection fails
- [ ] Duration detection incorrect

#### GLM Service Failures
- [ ] Summarization completely fails (no summary created)
- [ ] GLM API errors cause workflow to stop
- [ ] Formatting fallback doesn't work

#### Performance Failures
- [ ] Processing significantly slower than benchmarks
- [ ] GPU OOM or CUDA errors
- [ ] Memory leaks or resource exhaustion

#### Log Failures
- [ ] Critical ERROR logs
- [ ] Missing milestone logs
- [ ] Unbounded log outputs (> 5000 bytes)

#### Architecture Failures
- [ ] Server/Runner communication breaks
- [ ] Job queue polling fails
- [ ] Result upload fails
- [ ] Audio cleanup fails

## Architecture Summary

### Server/Runner Split Benefits

**Server (Lightweight ~150MB)**:
- Runs on cheap VPS without GPU
- Handles authentication, database, job queue
- Stores transcription results (4 gzip files)
- Serves API to frontend
- Manages user/channel permissions

**Runner (GPU Worker ~8GB)**:
- Runs on GPU server (RTX 3080, A100, etc.)
- Polls server for jobs
- Downloads audio, transcribes with faster-whisper
- Formats with GLM-4.5-Air
- Summarizes with GLM-4.5-Air
- Uploads results to server
- Horizontal scaling (multiple runners)

### Key Improvements from Monolithic Architecture

1. **Scalability**: Add more runners without modifying server
2. **Cost Optimization**: Server on cheap VPS, only runner needs GPU
3. **Fault Isolation**: Runner crash doesn't affect server
4. **Independent Deployment**: Update server without affecting processing
5. **Audio Cleanup**: Server deletes audio after runner downloads (saves space)
6. **Storage Efficiency**: 4 gzip-compressed files per transcription

### Test Coverage

This test plan verifies:
- ✅ Server/Runner job queue communication
- ✅ Audio upload and download flow
- ✅ Chunking logic (VAD + LCS merge)
- ✅ Standard transcription (no chunking)
- ✅ GLM formatting with fallback
- ✅ GLM summarization with retries
- ✅ Storage file creation and cleanup
- ✅ Database record accuracy
- ✅ Performance benchmarks
- ✅ Error handling and graceful degradation

### Testing Strategy

**Sequential Testing**: Test files must be processed one at a time to:
- Avoid race conditions in job queue
- Ensure clear log separation
- Verify each checkpoint thoroughly
- Track performance accurately

**Log Analysis**: Monitor both server and runner logs:
- Server: Upload, job queue, storage, database
- Runner: Polling, download, transcription, formatting, summarization, upload

**Database Verification**: Check after each test:
- `transcriptions` table: status, timestamps, storage paths
- `summaries` table: summary text, model, tokens
- `transcription_channels` table: channel assignments

**Storage Verification**: Confirm file creation:
- 4 gzip files per transcription
- Files decompress correctly
- Audio file deleted after processing

---

**Document Version**: 2.0 (Server/Runner Architecture)
**Last Updated**: 2025-01-09
**Status**: Ready for execution
