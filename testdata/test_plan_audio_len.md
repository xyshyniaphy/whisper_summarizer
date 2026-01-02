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

### System Configuration
```
GPU: RTX 3080 with cuDNN
Backend: faster-whisper with CTranslate2
Chunk Size Threshold: 10 minutes (600 seconds)
Max Concurrent Chunks: 2
Merge Strategy: LCS (text-based alignment)
```

### Settings
```bash
ENABLE_CHUNKING=true
CHUNK_SIZE_MINUTES=10
CHUNK_OVERLAP_SECONDS=15
MAX_CONCURRENT_CHUNKS=2
USE_VAD_SPLIT=true
MERGE_STRATEGY=lcs
AUDIO_PARALLELISM=1
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
┌─────────────────────────────────────────────────────────────────────┐
│                    TRANSCRIPTION PROCESS FLOW                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. UPLOAD STAGE                                                     │
│     ├── POST /api/audio/upload                                      │
│     ├── Create transcription record in DB                           │
│     ├── Save file to /app/data/uploads/                             │
│     └── Start background task                                       │
│                                                                      │
│  2. TRANSCRIBING STAGE                                               │
│     ├── Get audio duration (ffprobe)                                │
│     ├── Decision: duration > 600s? → Use chunking                   │
│     │                                                                │
│     ├── IF NO CHUNKING (2_min.m4a):                                 │
│     │   ├── [TRANSCRIBE START]                                      │
│     │   ├── Run faster-whisper on full file                         │
│     │   └── [TRANSCRIBE] ✓ Completed                                │
│     │                                                                │
│     └── IF CHUNKING (20_min, 60_min, 210_min):                               │
│         ├── [CHUNKING] Starting chunked transcription              │
│         ├── Detect silence points (VAD)                             │
│         ├── Split audio into chunks                                 │
│         ├── [CHUNKING] Created N chunks                            │
│         ├── [PARALLEL TRANSCRIPTION] Starting N chunks             │
│         ├── Process chunks in parallel (ThreadPoolExecutor)         │
│         │   ├── [CHUNK 0] Starting transcription                   │
│         │   ├── [CHUNK 0] ✓ Completed                               │
│         │   ├── [CHUNK 1] Starting transcription                   │
│         │   └── [CHUNK 1] ✓ Completed                               │
│         ├── [PARALLEL TRANSCRIPTION] Completed                     │
│         └── [CHUNKING] ✓ Merge complete (LCS alignment)             │
│                                                                      │
│  3. FORMATTING STAGE (NEW)                                          │
│     ├── Call TextFormattingService with transcription text          │
│     ├── Split into chunks if > MAX_FORMAT_CHUNK (10KB)              │
│     ├── Send chunks to GLM-4.5-Air for formatting                   │
│     │   ├── [FORMAT] Calling GLM API for chunk ({N} chars)          │
│     │   └── [FORMAT] GLM returned {N} chars                         │
│     ├── Save formatted text as .formatted.txt.gz                    │
│     └── Fallback to original if formatting fails                     │
│                                                                      │
│  4. SUMMARIZING STAGE                                                │
│     ├── Call GLM API with transcription text                         │
│     ├── [SUMMARY] Starting summarization for: {id}                  │
│     ├── Save summary to database                                     │
│     ├── [SUMMARY] Summarization successful: {N} tokens               │
│     └── Update pptx_status                                          │
│                                                                      │
│  5. COMPLETION                                                       │
│     ├── Set stage = "completed"                                     │
│     ├── Set completed_at timestamp                                 │
│     └── Return success                                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Checkpoints

### CP1: Upload Request
- **Action**: POST /api/audio/upload with file
- **Expected**: HTTP 201 Created
- **Verify**: Response contains `id`, `file_name`, `status="processing"`, `stage="uploading"`

### CP2: Database Record Created
- **Action**: Query `transcriptions` table by ID
- **Expected**: Record exists with correct `user_id`, `file_name`
- **Verify**: `file_path` is set, `stage="uploading"`

### CP3: Background Task Started
- **Log**: "Starting background processing for: {transcription_id}"
- **Expected**: Task registered in processor

### CP4: Stage Transition - Uploading → Transcribing
- **Action**: Poll GET /api/transcriptions/{id}
- **Expected**: `stage` changes from "uploading" to "transcribing"
- **Timeout**: 30 seconds

### CP5: Duration Detection
- **Log**: "Audio duration: {seconds} seconds"
- **Verify**: Duration matches expected (120s, 1200s, 3600s, 12600s)

### CP6: Chunking Decision
- **For 2_min.m4a**:
  - **Log**: "Using standard transcription for {duration}s audio"
  - **NO**: [CHUNKING] logs should appear
- **For 20_min.m4a, 60_min.m4a, 210_min.m4a**:
  - **Log**: "Using chunked transcription for {duration}s audio"
  - **YES**: [CHUNKING] logs should appear

### CP7: Chunk Creation (for 20_min, 60_min, 210_min)
- **Log**: "[CHUNKING] Splitting audio into chunks..."
- **Log**: "[CHUNKING] Created {N} chunks"
- **For 20_min**: N ≈ 2 chunks
- **For 60_min**: N ≈ 6 chunks
- **For 210_min**: N ≈ 21 chunks

### CP8: VAD Split Detection (for chunking)
- **Log**: "VAD splitting: found {N} silence regions, {M} split points"
- **Verify**: Split points calculated at silence

### CP9: Parallel Transcription Start (for chunking)
- **Log**: "[PARALLEL TRANSCRIPTION] Starting {N} chunks with {M} workers"
- **Verify**: M = MAX_CONCURRENT_CHUNKS (2)

### CP10: Individual Chunk Progress
- **Log**: "[CHUNK {N}] Starting transcription"
- **Log**: "[CHUNK {N}] ✓ Completed: {chars} chars, {segments} segments"
- **Verify**: All chunks complete

### CP11: Parallel Transcription Complete
- **Log**: "[PARALLEL TRANSCRIPTION] Completed: {succeeded} succeeded, {failed} failed out of {total}"
- **Verify**: failed = 0

### CP12: Chunk Merge (for chunking)
- **Log**: "[CHUNKING] Merging results from {N} chunks..."
- **Log**: "[CHUNKING] ✓ Merge complete: {chars} chars, {segments} segments"
- **Verify**: LCS alignment removed duplicates

### CP12a: Formatting Stage (NEW)
- **Log**: "Starting text formatting for: {transcription_id}"
- **Expected**: TextFormattingService is initialized
- **Storage Check**: `{transcription_id}.txt.gz` exists (original text)
- **Storage Check**: `{transcription_id}.segments.json.gz` exists (for SRT)
- **Storage Check**: `{transcription_id}.original.json.gz` exists (debug output)
- **Log**: "[FORMAT] Calling GLM API for chunk ({N} chars)"
- **Expected**: GLM-4.5-Air API is called with transcription text
- **Log**: "[FORMAT] GLM returned {N} chars"
- **Expected**: Formatted text length is logged
- **Storage Check**: `{transcription_id}.formatted.txt.gz` exists
- **Content Check**:
  - If GLM returns valid formatted text: Formatted version should have proper punctuation
  - If GLM fails: Formatted text equals original (fallback behavior)
- **Log**: "Text formatting completed: {id} | Original: {N} chars -> Formatted: {M} chars"
- **Verify**: Formatting is non-blocking (failure doesn't stop workflow)

### CP12b: Stage Transition - Transcribing → Formatting → Summarizing
- **Action**: Poll GET /api/transcriptions/{id}
- **Expected**: `stage` transitions: "transcribing" → "summarizing"
- **Note**: Formatting happens quickly between stages (no explicit stage value)
- **Verify**: `text` property returns decompressed text from storage

### CP13: Summarization Stage (ENHANCED)
- **Log**: "Starting summarization for: {transcription_id}"
- **Expected**: GLM client is initialized
- **Log**: "Summarization successful: {id} | Tokens: {N} | Time: {M}ms"
- **Database Check**: `summaries` table has entry with:
  - `transcription_id` matches
  - `summary_text` is non-empty
  - `model_name` is "GLM-4.5-Air" (or configured model)
  - `created_at` timestamp is set
- **GeminiRequestLog Check**: `gemini_request_logs` table has debug entry with:
  - `input_tokens` recorded
  - `output_tokens` recorded
  - `total_tokens` recorded
  - `response_time_ms` recorded
  - `status = "success"`

### CP14: Stage Transition - Summarizing → Completed
- **Action**: Poll GET /api/transcriptions/{id}
- **Expected**: `stage` changes to "completed"
- **Timeout**: 60 seconds (depends on audio length)
- **Verify**: All four storage files exist:
  - `{id}.txt.gz` (original transcribed text)
  - `{id}.segments.json.gz` (segments for SRT)
  - `{id}.original.json.gz` (debug output)
  - `{id}.formatted.txt.gz` (LLM-formatted text)

### CP15: Final Completion
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

### Must Pass (Required)
- [ ] HTTP 201 response on upload
- [ ] Stage reaches "completed"
- [ ] `text` property returns non-empty transcribed text
- [ ] `storage_path` is set and file exists
- [ ] `language` is detected
- [ ] `duration_seconds` is set
- [ ] `error_message` is null
- [ ] `completed_at` timestamp is set

### Storage Files Verification
- [ ] `{id}.txt.gz` exists (original transcribed text)
- [ ] `{id}.segments.json.gz` exists (segments with timestamps for SRT)
- [ ] `{id}.original.json.gz` exists (full Whisper output for debugging)
- [ ] `{id}.formatted.txt.gz` exists (LLM-formatted text with punctuation)

### Formatting Stage (NEW)
- [ ] "Starting text formatting for: {id}" log present
- [ ] "[FORMAT] Calling GLM API" log present
- [ ] "[FORMAT] GLM returned {N} chars" log present
- [ ] "Text formatting completed" log present
- [ ] Formatted text file exists and is readable
- [ ] Formatting is non-blocking (workflow continues even if formatting fails)

### Summarization Stage (ENHANCED)
- [ ] At least one entry in `summaries` table for this transcription
- [ ] `summary_text` is non-empty
- [ ] `model_name` is recorded (e.g., "GLM-4.5-Air")
- [ ] "Starting summarization for: {id}" log present
- [ ] "Summarization successful" log present
- [ ] Token counts are logged (input_tokens, output_tokens, total_tokens)
- [ ] Response time is logged (response_time_ms)

### SRT Download Verification (NEW)
- [ ] GET /api/transcriptions/{id}/download?format=srt works
- [ ] SRT file contains proper timestamps (not fake ones)
- [ ] SRT file format is valid (sequential numbering, time codes)

### Chunking-Specific (20_min, 60_min, 210_min)
- [ ] [CHUNKING] logs present
- [ ] [PARALLEL TRANSCRIPTION] logs present
- [ ] Multiple [CHUNK N] logs present
- [ ] Merge completion log present

### Non-Chunking (2_min)
- [ ] NO [CHUNKING] logs
- [ ] NO [PARALLEL TRANSCRIPTION] logs
- [ ] [TRANSCRIBE START] log present
- [ ] [TRANSCRIBE] ✓ Completed log present

### Log Verification
- [ ] No unbounded log outputs (all < 5000 bytes for large data)
- [ ] All milestone logs present
- [ ] No ERROR or WARNING logs (unless expected)

## Expected Log Patterns

### For 2_min.m4a (NO Chunking)
```
[TRANSCRIBE START] Starting transcription
[TRANSCRIBE] Input file: /app/data/uploads/...
[TRANSCRIBE] Model: large-v3-turbo
[TRANSCRIBE] Language: auto
[TRANSCRIBE] Device: cuda (float16)
[TRANSCRIBE] Processed 10 segments...
[TRANSCRIBE] Processed 20 segments...
[TRANSCRIBE] ✓ Completed: {N} chars, {M} segments
[TRANSCRIBE] Language: {lang} (probability: {p})
```

### For 20_min.m4a, 60_min.m4a, 210_min.m4a (WITH Chunking)
```
[CHUNKING] Starting chunked transcription for: /app/data/uploads/...
[CHUNKING] Audio duration: {N}s ({M} minutes)
[CHUNKING] Splitting audio into chunks...
VAD splitting: found {N} silence regions, {M} split points
[CHUNKING] Created {N} chunks
[PARALLEL TRANSCRIPTION] Starting {N} chunks with {M} workers
[CHUNK 0] Starting transcription
[CHUNK 0]   Path: /app/data/output/chunk_000.wav
[CHUNK 0]   Start time: 0.00s
[CHUNK 0]   Duration: {N}s
[CHUNK 0] ✓ Completed: {N} chars, {M} segments
[CHUNK 1] Starting transcription
...
[PARALLEL TRANSCRIPTION] Completed: {N} succeeded, 0 failed out of {total}
[CHUNKING] Merging results from {N} chunks...
[CHUNKING] ✓ Merge complete: {N} chars, {M} segments
```

### Formatting Stage Logs (NEW - applies to ALL transcriptions)
```
[TRANSCRIPTION PROCESSOR] Saved text: {id}.txt.gz
[TRANSCRIPTION PROCESSOR] Saved segments: {id}.segments.json.gz
[TRANSCRIPTION PROCESSOR] Saved original output: {id}.original.json.gz
Starting text formatting for: {transcription_id}
[FORMAT] Calling GLM API for chunk ({N} chars)
[FORMAT] GLM returned {N} chars
Text formatting completed: {id} | Original: {N} chars -> Formatted: {M} chars
Successfully saved formatted text: {id}.formatted.txt.gz
```

**Note**: If GLM formatting fails, expect:
```
[FORMAT] Failed to format text chunk: {error}
[FORMAT] GLM returned empty response, returning original text
Text formatting completed: {id} | Original: {N} chars -> Formatted: {N} chars
```

### Summarization Stage Logs (ENHANCED - applies to ALL transcriptions)
```
Starting summarization for: {transcription_id}
[SUMMARY] Calling GLM-4.5-Air API
[SUMMARY] Generated summary: {N} chars
Summarization successful: {id} | Tokens: {N} | Time: {M}ms
[SUMMARY] Saved summary to database with model: GLM-4.5-Air
```

### Storage Files Created (NEW - applies to ALL transcriptions)
```
/app/data/transcribes/{id}.txt.gz                 (original text)
/app/data/transcribes/{id}.segments.json.gz       (segments for SRT)
/app/data/transcribes/{id}.original.json.gz       (debug output)
/app/data/transcribes/{id}.formatted.txt.gz       (formatted text)
```

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

1. **Prerequisites**:
   - Backend container running
   - Test user exists in database (ID: 123e4567-e89b-42d3-a456-426614174000)
   - DISABLE_AUTH=true (or valid auth token)

2. **Run sequentially** (NOT in parallel):
   ```bash
   python3 testdata/test_upload.py
   ```

3. **Monitor**:
   - Watch console output for stage transitions
   - Check `docker logs whisper_backend_dev` for milestone logs
   - Verify each checkpoint before proceeding

4. **Verify**:
   - Check final status in database
   - Verify log patterns match expected
   - Compare timing against benchmarks

## Results Recording

For each test file, record:
- Upload time
- Transcription time
- **Formatting time** (NEW)
- **Summarization time** (ENHANCED)
- Total end-to-end time
- Number of chunks created (if applicable)
- Character count of transcription (original)
- **Character count of formatted text** (NEW)
- **Format success/failure** (NEW)
- Detected language
- **Summary length** (NEW)
- **Summary model used** (NEW)
- **Token counts** (input/output/total) (NEW)
- Any errors or warnings
- Log file reference

**Storage files created** (NEW):
- [ ] {id}.txt.gz
- [ ] {id}.segments.json.gz
- [ ] {id}.original.json.gz
- [ ] {id}.formatted.txt.gz

## Exit Criteria

Test is considered **PASSED** when:
- All four audio files successfully transcribed
- All checkpoints verified (CP1-CP15)
- **All four storage files created for each transcription** (NEW)
  - Original text (.txt.gz)
  - Segments (.segments.json.gz)
  - Original output (.original.json.gz)
  - Formatted text (.formatted.txt.gz)
- Log patterns match expectations
- Performance within acceptable range
- No unhandled transcription errors
- **Formatting completed (with or without GLM success)** (NEW)
- **Summarization completed with valid summary** (ENHANCED)
- **SRT download returns valid subtitle format** (NEW)

Test is **FAILED** when:
- Any file fails to reach "completed" stage
- Critical transcription errors in logs
- Chunking logic behaves incorrectly
- Performance significantly degrades
- **Storage files missing** (NEW)
- **Summarization completely fails (no summary created)** (NEW)
