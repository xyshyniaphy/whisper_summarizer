---
name: test_long_audio
description: Test 4 long audio files (2_min, 20_min, 60_min, 210_min) according to test_plan_audio_len.md. Verify checkpoints CP1-CP16, check logs, database records, storage files, and SRT format (especially for 210_min with fixed-duration chunks).
---

# test_long_audio - Long Audio Testing

## Purpose

Automated testing of 4 long audio files to verify the transcription system works correctly at different scales:

- **2_min.m4a** (0.08 MB, ~120 sec) - Standard transcription (no chunking)
- **20_min.m4a** (4.82 MB, ~1200 sec) - 10-min chunking
- **60_min.m4a** (14.58 MB, ~3600 sec) - 10-min chunking
- **210_min.m4a** (51.8 MB, ~12600 sec) - Fixed-duration SRT chunking (10-30s chunks)

## Prerequisites

1. **Dev environment running**:
   ```bash
   ./run_dev.sh up-d
   ```

2. **Check services are healthy**:
   ```bash
   docker ps | grep -E "whisper_(server|runner)_dev"
   ```

3. **Test files exist**:
   ```bash
   ls -lh testdata/{2_min,20_min,60_min,210_min}.m4a
   ```

4. **For fixed-duration SRT testing (210_min)**, verify runner config:
   ```bash
   grep ENABLE_FIXED_CHUNKS runner/.env  # Should be true
   grep FIXED_CHUNK_THRESHOLD_MINUTES runner/.env  # Should be 60
   ```

## Quick Start

```bash
# Test all 4 files sequentially (recommended)
/test_long_audio test_all

# Test specific file
/test_long_audio test 210_min

# Verify checkpoints for a completed transcription
/test_long_audio verify <transcription_id>

# Check SRT format for 210_min
/test_long_audio check_srt <transcription_id>

# View logs for a transcription
/test_long_audio logs <transcription_id>

# Show test status
/test_long_audio status
```

## Test Files Summary

| File | Size | Duration | Chunking | Expected Chunks | Key Verification |
|------|------|----------|----------|-----------------|------------------|
| 2_min.m4a | 0.08 MB | ~120 sec | NO | 1 (standard) | No [CHUNKING] logs |
| 20_min.m4a | 4.82 MB | ~1200 sec | YES (10-min) | ~2 chunks | VAD splitting + LCS merge |
| 60_min.m4a | 14.58 MB | ~3600 sec | YES (10-min) | ~6 chunks | VAD splitting + LCS merge |
| 210_min.m4a | 51.8 MB | ~12600 sec | YES (fixed 20s) | ~630 chunks | Fixed-duration SRT (10-30s) |

## Commands Reference

### test_all

Test all 4 audio files **sequentially** (IMPORTANT: no parallel execution):

```bash
/test_long_audio test_all
```

This will:
1. Start log monitoring (`docker logs -f` for both containers)
2. Upload each file via `POST /api/audio/upload`
3. Wait for completion (poll status every 10 seconds)
4. Verify checkpoints CP1-CP16
5. Generate test report

**IMPORTANT**: Tests run **sequentially** to avoid race conditions and ensure clear log separation.

### test <file>

Test a specific audio file:

```bash
/test_long_audio test 2_min
/test_long_audio test 20_min
/test_long_audio test 60_min
/test_long_audio test 210_min
```

Process:
1. Upload file via API
2. Get transcription ID
3. Monitor logs until completion
4. Run automatic verification
5. Return test results

### verify <id>

Verify all checkpoints (CP1-CP16) for a completed transcription:

```bash
/test_long_audio verify <transcription_id>
```

Checks:
- **Server logs**: Upload, job queue, storage, database
- **Runner logs**: Polling, download, transcription, formatting, summarization
- **Database**: `transcriptions` and `summaries` tables
- **Storage**: 4 gzip files exist and are readable
- **SRT format**: Valid timestamps and structure

### check_srt <id>

Specifically verify SRT format (critical for 210_min with fixed-duration chunks):

```bash
/test_long_audio check_srt <transcription_id>
```

For **210_min.m4a** with `ENABLE_FIXED_CHUNKS=true`, verifies:
- SRT entries have **consistent 10-30s duration** per line
- No extremely long (>60s) or short (<5s) entries
- Timestamps aligned to chunk boundaries (no gaps/overlaps)
- Approximately ~630 SRT entries (one per chunk)

### logs <id>

Show relevant logs for a transcription:

```bash
/test_long_audio logs <transcription_id>
```

Filters and displays:
- Server logs for this transcription ID
- Runner logs for this transcription ID
- Milestone logs (CP1-CP16)
- Chunking/transcription/formatting/summarization logs

### status

Show current test status:

```bash
/test_long_audio status
```

Displays:
- Running tests (if any)
- Completed tests with results
- Pending tests
- Container health status

## Checkpoints Quick Reference

### Server-Side (CP1-CP2)

| Checkpoint | Description | Expected |
|------------|-------------|----------|
| CP1 | Upload Request | HTTP 201, id returned |
| CP2 | Database Record | `status="pending"`, `runner_id=null` |

### Runner-Side (CP2a-CP10)

| Checkpoint | Description | Expected |
|------------|-------------|----------|
| CP2a | Job Queued | Runner claims job |
| CP2b | Audio Download | File downloaded to runner |
| CP3 | Transcription Started | Duration logged |
| CP4 | Chunking Decision | Correct mode selected |
| CP5 | Chunk Creation | Expected chunk count |
| CP6 | Parallel Start | Worker count correct |
| CP7 | Chunk Progress | All chunks complete |
| CP8 | Parallel Complete | All succeeded |
| CP9 | Chunk Merge | LCS strategy used |
| CP10 | Transcription Complete | Segments and chars logged |

### Formatting & Summarization (CP11-CP12)

| Checkpoint | Description | Expected |
|------------|-------------|----------|
| CP11 | Formatting Stage | GLM called, formatted text created |
| CP12 | Summarization Stage | Summary generated |

### Completion (CP13-CP16)

| Checkpoint | Description | Expected |
|------------|-------------|----------|
| CP13 | Result Upload | POST to /api/runner/jobs/{id}/complete |
| CP14 | Client Polling | Status="completed" |
| CP15 | Storage Verification | 4 gzip files exist |
| CP16 | Database Verification | All fields correct |

## Expected Log Patterns

### For 2_min.m4a (NO Chunking)

```
[INFO] Using standard transcription (duration: 120s < 600s threshold)
[INFO] Processing with faster-whisper (large-v3-turbo, cuda)
[INFO] Transcription completed for job {id}
[INFO] Total segments: {N}
```

**NO** `[CHUNKING]` or `[PARALLEL TRANSCRIPTION]` logs should appear.

### For 20_min.m4a, 60_min.m4a (10-min Chunking)

```
[INFO] Using chunked transcription (duration: {seconds}s > 600s threshold)
[INFO] [CHUNKING] Splitting audio into chunks...
[INFO] [CHUNKING] Target chunk size: 600 seconds (10 minutes)
[INFO] [CHUNKING] Overlap: 15 seconds
[INFO] VAD splitting: found {N} silence regions, {M} split points
[INFO] [CHUNKING] Created {N} chunks
[INFO] [PARALLEL TRANSCRIPTION] Starting {N} chunks with {M} workers
[INFO] [CHUNK 0] Starting transcription
...
[INFO] [CHUNKING] Merging results from {N} chunks...
[INFO] Using LCS (Longest Common Subsequence) merge strategy
```

### For 210_min.m4a (Fixed-Duration Chunking)

```
[INFO] Using fixed-chunk transcription (duration: 12600s >= 3600s threshold)
[INFO] Loading audio: /app/data/uploads/{filename}
[INFO] Detecting speech segments...
[INFO] Created ~630 chunks from 12600000ms audio
[INFO] Processing chunk 1/630 (0-15000ms)
[INFO] Processing chunk 2/630 (15000-30000ms)
...
[INFO] Transcription completed for job {id}
[INFO] Total segments: ~630 (one per chunk, aligned to chunk boundaries)
[INFO] [FORMAT] Text appears to be SRT format, chunking by sections
[INFO] [FORMAT] Splitting into 13 SRT sections (max 50 per chunk)
[INFO] [FORMAT] Processing chunk 1/13 (1-50 sections)
```

**Key differences**:
- **No** `[PARALLEL TRANSCRIPTION]` logs (sequential processing)
- **No** LCS merge (chunks don't overlap)
- **SRT-aware formatting** (section-based, not byte-based)

### Formatting Stage (SRT Format Detection)

```
[INFO] [FORMAT] Input text length: {N} characters
[INFO] [FORMAT] Text appears to be SRT format, chunking by sections
[INFO] [FORMAT] Splitting into {N} SRT sections (max 50 per chunk)
[INFO] [FORMAT] Processing chunk 1/{N} (1-50 sections)
[INFO] [FORMAT] Calling GLM-4.5-Air API for chunk (50 sections)
[INFO] [FORMAT] GLM returned {N} chars
[INFO] [FORMAT] Merging {N} formatted chunks
```

## Success Criteria

### Test PASSED

All of the following must be true:

#### Server-Side
- [x] HTTP 201 response on upload
- [x] Status transitions: `pending → processing → completed`
- [x] `runner_id` is set
- [x] `started_at` and `completed_at` timestamps set
- [x] `error_message = null`
- [x] All 4 storage files created

#### Runner-Side
- [x] Transcription completes successfully
- [x] Formatting completes (GLM or fallback)
- [x] Summarization completes with valid summary

#### Chunking-Specific (20_min, 60_min)
- [x] `[CHUNKING]` logs present
- [x] `[PARALLEL TRANSCRIPTION]` logs present
- [x] VAD splitting detected silence points
- [x] LCS merge strategy used

#### Fixed-Duration Specific (210_min)
- [x] `Using fixed-chunk transcription` log present
- [x] `Created ~630 chunks` log present
- [x] `Text appears to be SRT format` log present
- [x] SRT entries have 10-30s duration (verified via download)

#### Storage Files
- [x] `{id}.txt.gz` exists and decompresses
- [x] `{id}.segments.json.gz` exists and is valid JSON
- [x] `{id}.original.json.gz` exists and is valid JSON
- [x] `{id}.formatted.txt.gz` exists and decompresses

#### SRT Format (All Files)
- [x] SRT download works: `GET /api/transcriptions/{id}/download?format=srt`
- [x] SRT contains proper timestamps (`HH:MM:SS,mmm --> HH:MM:SS,mmm`)
- [x] SRT has sequential numbering (1, 2, 3, ...)

#### SRT Format (210_min Fixed-Duration)
- [x] Each SRT entry is 10-30s duration
- [x] No entries >60s or <5s
- [x] Timestamps aligned (no gaps between entries)

### Test FAILED

Test fails if **ANY** of these occur:

#### Critical Failures
- [ ] Status != "completed" or `error_message` is set
- [ ] Storage files missing or corrupted
- [ ] Runner fails to claim or process job

#### SRT Format Failures (210_min)
- [ ] SRT entries have highly variable duration (indicates standard chunking)
- [ ] Entries >60s or <5s (indicates incorrect chunking)
- [ ] Large gaps between timestamps (indicates alignment issues)

## Fixed-Duration SRT Verification (210_min)

### Quick Verification Command

```bash
# Download SRT and check entry count
curl "http://localhost:8130/api/transcriptions/{id}/download?format=srt" -o test.srt
grep -c "^$" test.srt  # Count blank lines (approximate entry count)
# Expected: ~630 entries for 210_min with fixed chunks
```

### Detailed SRT Analysis

```bash
# Analyze SRT entry durations
grep -A1 "^--> $" test.srt | grep -E "^--> $" | \
  awk '{
    split($1, start, ":")
    split($3, end, ":")
    start_sec = start[1]*3600 + start[2]*60 + start[3]
    end_sec = end[1]*3600 + end[2]*60 + end[3]
    duration = end_sec - start_sec
    print duration
  }' | sort -n | uniq -c
```

**Expected output** (for fixed-duration chunks):
```
   50 12
  100 15
  200 18
  250 20
   30 25
```

All durations should be between 10-30 seconds.

### What to Look For

| Issue | Symptom | Cause |
|-------|---------|-------|
| Variable durations | Mix of 5s, 30s, 2min entries | Standard chunking, not fixed |
| Too short | Many entries <10s | MIN_DURATION too low |
| Too long | Entries >30s | MAX_DURATION exceeded |
| Gaps | Timestamps don't align | Chunk boundary issue |
| Duplicates | Same timestamp appears twice | Merge issue |

## Full Test Plan Reference

See `testdata/test_plan_audio_len.md` for:
- Complete checkpoint descriptions (CP1-CP16)
- Detailed process flow diagram
- Architecture overview
- Failure scenarios
- Performance benchmarks
- Test execution procedure

## Tips & Troubleshooting

### Sequential Testing Only

**ALWAYS** run tests sequentially, never in parallel:
```bash
# GOOD
/test_long_audio test 2_min
# Wait for completion
/test_long_audio test 20_min

# BAD - Do NOT do this
/test_long_audio test_all  # This runs sequentially anyway
```

### Clear Old Test Data

Before running tests, consider clearing old transcriptions:
```bash
docker exec whisper_server_dev python -c "
from app.db.session import SessionLocal
from app.models.transcription import Transcription
db = SessionLocal()
db.query(Transcription).delete()
db.commit()
print('Cleared all transcriptions')
"
```

### Enable Fixed-Duration Chunks for 210_min

Verify runner `.env` has:
```bash
ENABLE_FIXED_CHUNKS=true
FIXED_CHUNK_THRESHOLD_MINUTES=60
FIXED_CHUNK_TARGET_DURATION=20
FIXED_CHUNK_MIN_DURATION=10
FIXED_CHUNK_MAX_DURATION=30
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Runner not claiming job | Check RUNNER_API_KEY matches |
| Chunking not triggered | Check duration threshold |
| Fixed chunks not used | Check ENABLE_FIXED_CHUNKS=true |
| SRT format wrong | Check chunking mode (standard vs fixed) |
| GLM formatting fails | Check GLM_API_KEY in runner .env |

## Performance Benchmarks (GPU: RTX 3080)

| File | Expected Time |
|------|---------------|
| 2_min | ~2-5 seconds |
| 20_min | ~30-60 seconds |
| 60_min | ~90-120 seconds |
| 210_min (fixed chunks) | ~360-500 seconds (+10-20%) |

If times are significantly longer, investigate:
- GPU utilization (`nvidia-smi`)
- Chunk count (too many chunks)
- GLM API delays
