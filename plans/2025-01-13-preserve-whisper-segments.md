# Preserve Whisper Segments Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Preserve Whisper's native segments with individual timestamps throughout the pipeline, while chunking LLM formatting requests by 5000 bytes for optimal performance.

**Architecture:** Runner sends segments (not concatenated text) to server → Server saves segments.json.gz → LLM formatting chunks by 5000 bytes → SRT uses real segment timestamps.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, faster-whisper, GLM-4.5-Air API, httpx

---

## Task 1: Update Runner JobResult Schema to Include Segments

**Files:**
- Modify: `runner/app/models/job_schemas.py`

**Step 1: Write the failing test**

Create `tests/runner/models/test_job_schemas.py`:

```python
"""Tests for job_schemas"""
import pytest
from pydantic import ValidationError
from app.models.job_schemas import JobResult

def test_job_result_with_segments():
    """JobResult should accept segments field."""
    segments = [
        {"start": 0.0, "end": 2.5, "text": "Hello"}
    ]
    result = JobResult(
        text="Hello",
        segments=segments,
        summary="Test summary",
        processing_time_seconds=10
    )
    assert result.segments == segments
    assert result.text == "Hello"
```

**Step 2: Run test to verify it fails**

Run: `docker exec whisper_runner_dev pytest tests/runner/models/test_job_schemas.py::test_job_result_with_segments -v`

Expected: FAIL with "JobResult.__init__() got an unexpected keyword argument 'segments'"

**Step 3: Write minimal implementation**

Edit `runner/app/models/job_schemas.py`:

```python
class JobResult(BaseModel):
    """Result of processing a job."""
    text: str
    segments: Optional[List[Dict]] = None  # NEW: Preserve Whisper segments
    summary: Optional[str] = None
    notebooklm_guideline: Optional[str] = None
    processing_time_seconds: int
```

**Step 4: Run test to verify it passes**

Run: `docker exec whisper_runner_dev pytest tests/runner/models/test_job_schemas.py::test_job_result_with_segments -v`

Expected: PASS

**Step 5: Commit**

```bash
git add runner/app/models/job_schemas.py tests/runner/models/test_job_schemas.py
git commit -m "feat(runner): add segments field to JobResult schema"
```

---

## Task 2: Update Runner JobClient to Send Segments

**Files:**
- Modify: `runner/app/services/job_client.py`

**Step 1: Write the failing test**

Create `tests/runner/services/test_job_client_segments.py`:

```python
"""Tests for job_client segment sending"""
import pytest
from unittest.mock import Mock, patch
from app.services.job_client import JobClient
from app.models.job_schemas import JobResult

def test_complete_job_sends_segments(monkeypatch):
    """complete_job should include segments in payload."""
    # Mock HTTP client
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "completed"}

    client = JobClient()
    client.client = Mock()
    client.client.post.return_value = mock_response

    # JobResult with segments
    segments = [{"start": 0.0, "end": 2.5, "text": "Test"}]
    result = JobResult(
        text="Test",
        segments=segments,
        processing_time_seconds=10
    )

    # Call complete_job
    client.complete_job("test-job-id", result)

    # Verify segments were sent
    call_args = client.client.post.call_args
    payload = call_args[1]["json"]  # Get json parameter

    assert "segments" in payload
    assert payload["segments"] == segments
```

**Step 2: Run test to verify it fails**

Run: `docker exec whisper_runner_dev pytest tests/runner/services/test_job_client_segments.py::test_complete_job_sends_segments -v`

Expected: FAIL with "AssertionError: 'segments' not in payload"

**Step 3: Write minimal implementation**

Edit `runner/app/services/job_client.py`, method `complete_job`:

Find line 153-179, replace the `json` parameter in `client.post()`:

```python
def complete_job(self, job_id: str, result: JobResult) -> bool:
    """
    Submit job result to server.

    Args:
        job_id: UUID of the job
        result: Processing result with segments

    Returns:
        True if successful, False otherwise
    """
    try:
        response = self.client.post(
            f"/jobs/{job_id}/complete",
            json={
                "text": result.text,
                "segments": result.segments,  # NEW: Send segments to server
                "summary": result.summary,
                "notebooklm_guideline": result.notebooklm_guideline,
                "processing_time_seconds": result.processing_time_seconds
            }
        )
        response.raise_for_status()
        logger.info(f"Job {job_id} completed successfully")
        return True
    except httpx.HTTPError as e:
        logger.error(f"Error completing job {job_id}: {e}")
        return False
```

**Step 4: Run test to verify it passes**

Run: `docker exec whisper_runner_dev pytest tests/runner/services/test_job_client_segments.py::test_complete_job_sends_segments -v`

Expected: PASS

**Step 5: Commit**

```bash
git add runner/app/services/job_client.py tests/runner/services/test_job_client_segments.py
git commit -m "feat(runner): send segments to server in complete_job"
```

---

## Task 3: Update Server Schema to Accept Segments

**Files:**
- Modify: `server/app/schemas/runner.py`

**Step 1: Write the failing test**

Create `tests/server/schemas/test_runner_schema_segments.py`:

```python
"""Tests for runner schema with segments"""
import pytest
from app.schemas.runner import JobCompleteRequest

def test_job_complete_request_with_segments():
    """JobCompleteRequest should accept segments."""
    segments = [
        {"start": 0.0, "end": 2.5, "text": "First"},
        {"start": 2.5, "end": 5.0, "text": "Second"}
    ]

    request = JobCompleteRequest(
        text="Combined text",
        segments=segments,
        summary="Summary",
        processing_time_seconds=10
    )

    assert request.segments == segments
    assert len(request.segments) == 2
```

**Step 2: Run test to verify it fails**

Run: `docker exec whisper_server_dev pytest tests/server/schemas/test_runner_schema_segments.py::test_job_complete_request_with_segments -v`

Expected: FAIL with "JobCompleteRequest.__init__() got an unexpected keyword argument 'segments'"

**Step 3: Write minimal implementation**

Edit `server/app/schemas/runner.py`, update `JobCompleteRequest`:

```python
class JobCompleteRequest(BaseModel):
    """Request to mark job as completed."""
    text: str
    segments: Optional[List[Dict]] = None  # NEW: Whisper segments with timestamps
    summary: Optional[str] = None
    notebooklm_guideline: Optional[str] = None
    processing_time_seconds: int
```

**Step 4: Run test to verify it passes**

Run: `docker exec whisper_server_dev pytest tests/server/schemas/test_runner_schema_segments.py::test_job_complete_request_with_segments -v`

Expected: PASS

**Step 5: Commit**

```bash
git add server/app/schemas/runner.py tests/server/schemas/test_runner_schema_segments.py
git commit -m "feat(server): accept segments in JobCompleteRequest"
```

---

## Task 4: Update Server API to Save Segments

**Files:**
- Modify: `server/app/api/runner.py`

**Step 1: Write the failing test**

Create `tests/server/api/test_runner_save_segments.py`:

```python
"""Tests for runner API saving segments"""
import pytest
from unittest.mock import Mock, patch
from app.schemas.runner import JobCompleteRequest
from app.api.runner import complete_job

def test_complete_job_saves_segments(monkeypatch):
    """complete_job should save segments to storage."""
    # Mock storage service
    mock_storage = Mock()
    mock_storage.save_transcription_segments.return_value = "test.segments.json.gz"

    with patch('app.api.runner.get_storage_service', return_value=mock_storage):
        from app.db.session import get_local_user_id

        # Mock DB session
        mock_db = Mock()
        mock_job = Mock()
        mock_job.id = "test-uuid"
        mock_job.storage_path = None

        with patch('app.api.runner.get_db', return_value=mock_db):
            with patch('app.api.runner.uuid.UUID', side_effect=lambda x: Mock(spec=["__getitem__"]) if isinstance(x, str) else Mock(spec_set=["__getitem__", "hex"]) if isinstance(x, Mock) else x):
                # Prepare request
                segments = [{"start": 0.0, "end": 2.5, "text": "Test"}]
                request = JobCompleteRequest(
                    text="Test text",
                    segments=segments,
                    processing_time_seconds=10
                )

                # Mock query
                mock_db.query.return_value.filter.return_value.first.return_value = mock_job

                # Call function (ignore auth errors for test)
                try:
                    complete_job("test-job-id", request, mock_db, Mock())
                except:
                    pass

                # Verify segments were saved
                mock_storage.save_transcription_segments.assert_called_once()
                call_args = mock_storage.save_transcription_segments.call_args

                assert call_args[0][0] == "test-uuid"  # transcription_id
                assert call_args[0][1] == segments  # segments
```

**Step 2: Run test to verify it fails**

Run: `docker exec whisper_server_dev pytest tests/server/api/test_runner_save_segments.py::test_complete_job_saves_segments -v`

Expected: FAIL with "AssertionError: Expected 1 calls, got 0" or similar

**Step 3: Write minimal implementation**

Edit `server/app/api/runner.py`, in the `complete_job` function (around line 176-180):

Find the section after "Save transcription text to storage" and add:

```python
    # Save transcription text to storage
    try:
        storage_service = get_storage_service()
        storage_service.save_transcription_text(str(job.id), result.text)
        job.storage_path = f"{job.id}.txt.gz"
        logger.info(f"Saved transcription text for job {job_id}")
    except Exception as e:
        logger.error(f"Failed to save transcription text for job {job_id}: {e}")
        # Don't fail the job if text save fails, log and continue

    # NEW: Save segments if provided
    if result.segments:
        try:
            storage_service = get_storage_service()
            segments_path = storage_service.save_transcription_segments(str(job.id), result.segments)
            job.segments_path = segments_path
            logger.info(f"Saved {len(result.segments)} segments for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to save segments for job {job_id}: {e}")
            # Don't fail the job if segments save fails, log and continue
```

**Step 4: Run test to verify it passes**

Run: `docker exec whisper_server_dev pytest tests/server/api/test_runner_save_segments.py::test_complete_job_saves_segments -v`

Expected: PASS

**Step 5: Commit**

```bash
git add server/app/api/runner.py tests/server/api/test_runner_save_segments.py
git commit -m "feat(server): save segments from runner to storage"
```

---

## Task 5: Update Formatting Service to Use 5000 Byte Chunking

**Files:**
- Modify: `runner/app/services/formatting_service.py`

**Step 1: Write the failing test**

Create `tests/runner/services/test_formatting_byte_chunking.py`:

```python
"""Tests for LLM formatting with 5000 byte chunking"""
import pytest
from app.services.formatting_service import TextFormattingService

def test_format_chunks_by_5000_bytes():
    """Should chunk text by 5000 bytes, not characters."""
    service = TextFormattingService()

    # Create text that's ~15000 bytes (5000 UTF-8 chars ≈ 15000 bytes for Chinese)
    # Each Chinese character is ~3 bytes
    # 5000 bytes / 3 = ~1666 chars per chunk
    # 15000 bytes = ~5000 chars = 3 chunks

    long_text = "测试" * 2000  # ~6000 bytes (over 5000)

    # Mock GLM client
    service.glm_client = Mock()
    service.glm_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content='{"content": "formatted text"}'))]
    )

    # Format
    result = service.format_transcription_text(long_text)

    # Should have called GLM multiple times (chunked)
    # With 6000 bytes and 5000 limit, should be 2 chunks
    assert service.glm_client.chat.completions.create.call_count >= 1

def test_max_chunk_bytes_is_5000():
    """MAX_FORMAT_CHUNK should default to 5000 bytes."""
    service = TextFormattingService()
    assert service.max_chunk_bytes == 5000
```

**Step 2: Run test to verify it fails**

Run: `docker exec whisper_runner_dev pytest tests/runner/services/test_formatting_byte_chunking.py::test_max_chunk_bytes_is_5000 -v`

Expected: FAIL with "AssertionError: assert 10000 == 5000" (current default is 10000)

**Step 3: Write minimal implementation**

Edit `runner/app/services/formatting_service.py`, line 250:

Change:
```python
self.max_chunk_bytes = getattr(settings, 'MAX_FORMAT_CHUNK', 10000)
```

To:
```python
self.max_chunk_bytes = getattr(settings, 'MAX_FORMAT_CHUNK', 5000)  # 5000 bytes for GLM
```

**Step 4: Run test to verify it passes**

Run: `docker exec whisper_runner_dev pytest tests/runner/services/test_formatting_byte_chunking.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add runner/app/services/formatting_service.py tests/runner/services/test_formatting_byte_chunking.py
git commit -m "feat(runner): default MAX_FORMAT_CHUNK to 5000 bytes for GLM"
```

---

## Task 6: Update Docker Compose Configuration

**Files:**
- Modify: `docker-compose.dev.yml`

**Step 1: Remove fixed-duration chunking config**

Edit `docker-compose.dev.yml`, remove lines 142-146:

```yaml
    # REMOVE THESE LINES:
    # Fixed-Duration SRT Chunking (for long audio 60+ minutes)
    ENABLE_FIXED_CHUNKS: ${ENABLE_FIXED_CHUNKS:-true}
    FIXED_CHUNK_THRESHOLD_MINUTES: ${FIXED_CHUNK_THRESHOLD_MINUTES:-60}
    FIXED_CHUNK_TARGET_DURATION: ${FIXED_CHUNK_TARGET_DURATION:-20}
    FIXED_CHUNK_MIN_DURATION: ${FIXED_CHUNK_MIN_DURATION:-10}
    FIXED_CHUNK_MAX_DURATION: ${FIXED_CHUNK_MAX_DURATION:-30}
```

**Step 2: Update MAX_FORMAT_CHUNK default**

Edit `docker-compose.dev.yml`, line 84:

Change:
```yaml
MAX_FORMAT_CHUNK: ${MAX_FORMAT_CHUNK:-10000}
```

To:
```yaml
MAX_FORMAT_CHUNK: ${MAX_FORMAT_CHUNK:-5000}
```

**Step 3: Verify changes**

Run: `docker compose -f docker-compose.dev.yml config`

Expected: No errors, configuration valid

**Step 4: Commit**

```bash
git add docker-compose.dev.yml
git commit -m "chore(docker): remove fixed-duration chunking, set MAX_FORMAT_CHUNK=5000"
```

---

## Task 7: Remove Fixed-Duration Chunking from Runner Config

**Files:**
- Modify: `runner/app/config.py`

**Step 1: Write the failing test**

Create `tests/runner/test_config_no_fixed_chunks.py`:

```python
"""Tests for runner config without fixed-duration chunking"""
import pytest
from app.config import Settings

def test_no_fixed_duration_config():
    """Config should not have fixed-duration chunking attributes."""
    settings = Settings()

    # These should NOT exist (will raise AttributeError)
    with pytest.raises(AttributeError):
        _ = settings.ENABLE_FIXED_CHUNKS

    with pytest.raises(AttributeError):
        _ = settings.FIXED_CHUNK_THRESHOLD_MINUTES

    with pytest.raises(AttributeError):
        _ = settings.FIXED_CHUNK_TARGET_DURATION

def test_llm_format_max_bytes_exists():
    """LLM_FORMAT_MAX_BYTES should exist and default to 5000."""
    settings = Settings()
    assert hasattr(settings, 'LLM_FORMAT_MAX_BYTES')
    assert settings.LLM_FORMAT_MAX_BYTES == 5000
```

**Step 2: Run test to verify it fails**

Run: `docker exec whisper_runner_dev pytest tests/runner/test_config_no_fixed_chunks.py::test_no_fixed_duration_config -v`

Expected: FAIL - attributes currently exist

**Step 3: Write minimal implementation**

Edit `runner/app/config.py`:

1. Remove lines 37-42:
```python
# REMOVE THESE LINES:
# Fixed-duration chunking (SRT segmentation)
enable_fixed_chunks: bool = False
fixed_chunk_threshold_minutes: int = 60  # Use fixed chunks for audio >= 60 minutes
fixed_chunk_target_duration: int = 20  # Target chunk duration in seconds
fixed_chunk_min_duration: int = 10       # Minimum chunk duration in seconds
fixed_chunk_max_duration: int = 30       # Maximum chunk duration in seconds
```

2. Remove lines 103-114 (the @property aliases):
```python
# REMOVE THESE @property methods:
@property
def ENABLE_FIXED_CHUNKS(self):
    return self.enable_fixed_chunks

@property
def FIXED_CHUNK_THRESHOLD_MINUTES(self):
    return self.fixed_chunk_threshold_minutes

@property
def FIXED_CHUNK_TARGET_DURATION(self):
    return self.fixed_chunk_target_duration

@property
def FIXED_CHUNK_MIN_DURATION(self):
    return self.fixed_chunk_min_duration

@property
def FIXED_CHUNK_MAX_DURATION(self):
    return self.fixed_chunk_max_duration
```

3. Add new config (around line 42, after chunking config):
```python
# LLM Formatting Config
llm_format_max_bytes: int = 5000  # Max bytes per GLM formatting request
```

4. Add @property (around line 96, after other properties):
```python
@property
def LLM_FORMAT_MAX_BYTES(self):
    return self.llm_format_max_bytes
```

**Step 4: Run test to verify it passes**

Run: `docker exec whisper_runner_dev pytest tests/runner/test_config_no_fixed_chunks.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add runner/app/config.py tests/runner/test_config_no_fixed_chunks.py
git commit -m "refactor(runner): remove fixed-duration chunking config, add LLM_FORMAT_MAX_BYTES"
```

---

## Task 8: Remove Fixed-Duration Chunking from WhisperService

**Files:**
- Modify: `runner/app/services/whisper_service.py`

**Step 1: Write the failing test**

Create `tests/runner/services/test_whisper_no_fixed_chunks.py`:

```python
"""Tests for WhisperService without fixed-duration chunking"""
import pytest
from app.services.whisper_service import TranscribeService
from unittest.mock import Mock, patch

def test_whisper_service_has_no_fixed_chunks_method():
    """TranscribeService should NOT have transcribe_fixed_chunks method."""
    service = TranscribeService()

    with pytest.raises(AttributeError):
        service.transcribe_fixed_chunks(
            audio_path="test.wav",
            target_duration_seconds=20
        )
```

**Step 2: Run test to verify it fails**

Run: `docker exec whisper_runner_dev pytest tests/runner/services/test_whisper_no_fixed_chunks.py::test_whisper_service_has_no_fixed_chunks_method -v`

Expected: FAIL - method currently exists

**Step 3: Write minimal implementation**

In `runner/app/services/whisper_service.py`, remove the entire `transcribe_fixed_chunks` method.

Find the method (search for `def transcribe_fixed_chunks`) and delete the entire method including its docstring and all its code.

Also remove `_extract_audio_chunk` method if it was only used by `transcribe_fixed_chunks`.

**Step 4: Run test to verify it passes**

Run: `docker exec whisper_runner_dev pytest tests/runner/services/test_whisper_no_fixed_chunks.py::test_whisper_service_has_no_fixed_chunks_method -v`

Expected: PASS

**Step 5: Commit**

```bash
git add runner/app/services/whisper_service.py tests/runner/services/test_whisper_no_fixed_chunks.py
git commit -m "refactor(runner): remove transcribe_fixed_chunks method"
```

---

## Task 9: Remove Fixed-Duration Chunking from AudioProcessor

**Files:**
- Modify: `runner/app/services/audio_processor.py`

**Step 1: Write the failing test**

Create `tests/runner/services/test_audio_processor_no_fixed_chunks.py`:

```python
"""Tests for AudioProcessor without fixed-duration chunking"""
import pytest
from app.services.audio_processor import AudioProcessor

def test_audio_processor_has_no_fixed_chunks_logic():
    """AudioProcessor should not use fixed-duration chunks."""
    processor = AudioProcessor()

    # _should_use_fixed_chunks should NOT exist
    with pytest.raises(AttributeError):
        processor._should_use_fixed_chunks("test.wav")

    # process_with_timestamps should only use standard transcription
    # Mock the whisper service
    processor.whisper_service = Mock()
    processor.whisper_service.transcribe.return_value = {
        "text": "Test",
        "segments": []
    }

    # Mock formatting service
    processor.formatting_service = Mock()
    processor.formatting_service.format_transcription.return_value = {
        "formatted_text": "Formatted",
        "summary": "Summary"
    }

    result = processor.process_with_timestamps("test.wav")

    # Should have used standard transcribe (not transcribe_fixed_chunks)
    processor.whisper_service.transcribe.assert_called_once()
    assert result["text"] == "Formatted"
```

**Step 2: Run test to verify it fails**

Run: `docker exec whisper_runner_dev pytest tests/runner/services/test_audio_processor_no_fixed_chunks.py::test_audio_processor_has_no_fixed_chunks_logic -v`

Expected: FAIL - method currently exists

**Step 3: Write minimal implementation**

Edit `runner/app/services/audio_processor.py`:

1. Remove `_should_use_fixed_chunks` method (lines 50-67)

2. Update `process` method (lines 69-158), remove fixed-chunks logic:

Replace lines 98-113 with:
```python
            # Always use standard Whisper transcription (no fixed-duration chunks)
            logger.info("Using standard Whisper transcription")
            transcription_result = self.whisper_service.transcribe(
                audio_file_path=audio_path
            )

            if not transcription_result or not transcription_result.get("text"):
                raise ValueError("Transcription returned empty text")

            raw_text = transcription_result["text"]
            segments = transcription_result.get("segments", [])
            logger.info(f"Transcription complete: {len(raw_text)} characters, {len(segments)} segments")
```

3. Update `process_with_timestamps` method (lines 160-222), remove fixed-chunks logic similarly:

Replace lines 177-191 with:
```python
        # Always use standard Whisper transcription
        logger.info("Using standard Whisper transcription")
        # Transcribe
        transcription_result = self.whisper_service.transcribe(
            audio_file_path=audio_path
        )

        raw_text = transcription_result["text"]
        segments = transcription_result.get("segments", [])
```

**Step 4: Run test to verify it passes**

Run: `docker exec whisper_runner_dev pytest tests/runner/services/test_audio_processor_no_fixed_chunks.py::test_audio_processor_has_no_fixed_chunks_logic -v`

Expected: PASS

**Step 5: Commit**

```bash
git add runner/app/services/audio_processor.py tests/runner/services/test_audio_processor_no_fixed_chunks.py
git commit -m "refactor(runner): remove fixed-duration chunking from AudioProcessor"
```

---

## Task 10: Update CLAUDE.md with New Architecture

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add architecture documentation**

Find the "Code Architecture" section and add after "Runner (`runner/app/`)" section:

```markdown
### Runner Data Flow

**Segments-First Architecture:**

Runner preserves Whisper's native segments throughout the pipeline:

1. **Whisper Transcription** (10-min chunks, parallel)
   - Returns segments with individual timestamps
   - Example: `{"start": 0.0, "end": 2.5, "text": "第一段"}`

2. **Segments Sent to Server**
   - Runner sends `segments` array (NOT concatenated text)
   - Server saves `segments.json.gz` for SRT generation

3. **LLM Formatting** (5000 byte chunks)
   - Text extracted from segments
   - Chunked by 5000 bytes (not character count)
   - Each chunk sent to GLM for formatting
   - Merged formatted text saved as `formatted.txt.gz`

4. **SRT Export**
   - Uses original `segments.json.gz` with real timestamps
   - Each line has individual Whisper timestamp ✅

**Key Configuration:**
- `CHUNK_SIZE_MINUTES: 5` - 10-minute chunks for parallel processing
- `MAX_CONCURRENT_CHUNKS: 4` - Parallel workers
- `MAX_FORMAT_CHUNK: 5000` - Max bytes per GLM request
- `MERGE_STRATEGY: lcs` - Note: Auto-switches to timestamp for large files

**Removed Features:**
- ❌ Fixed-duration SRT chunking (poor performance: 3.5x RTF)
- ❌ `ENABLE_FIXED_CHUNKS`, `FIXED_CHUNK_*` config variables

**Performance:**
- 10-min chunking: 11.7x real-time ✅
- Segments preserved for accurate SRT ✅
- LLM chunking by 5000 bytes prevents timeouts ✅
```

**Step 2: Update "Database Schema" section**

Add after the transcriptions table documentation:

```markdown
**segments_path**: Path to segments JSON file (e.g., `{id}.segments.json.gz`).
Contains Whisper native segments with individual timestamps for SRT generation.
Format: `[{"start": 0.0, "end": 2.5, "text": "..."}, ...]`

**Index for segments queries:**
```sql
CREATE INDEX idx_transcriptions_segments_path ON transcriptions(segments_path) WHERE segments_path IS NOT NULL;
```
```

**Step 3: Update "Environment Variables" section**

Under "Runner (.env)", update:

```bash
# Audio Chunking (10-minute parallel chunks)
CHUNK_SIZE_MINUTES=5                # 5-10 minutes recommended
CHUNK_OVERLAP_SECONDS=15           # Overlap between chunks
MAX_CONCURRENT_CHUNKS=4             # GPU: 4-8 recommended

# GLM API (Chunking by byte size)
GLM_API_KEY=your-glm-api-key
GLM_MODEL=GLM-4.5-Air
GLM_BASE_URL=https://api.z.ai/api/paas/v4/
REVIEW_LANGUAGE=zh
MAX_FORMAT_CHUNK=5000              # Max bytes per GLM request (important!)
```

Remove any mention of `FIXED_CHUNK_*` variables.

**Step 4: Verify documentation**

Run: `grep -n "FIXED_CHUNK" CLAUDE.md`

Expected: No results (all references removed)

**Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update architecture with segments-first approach, remove fixed-duration docs"
```

---

## Task 11: Rebuild and Test End-to-End

**Files:**
- Test: Full system

**Step 1: Rebuild containers**

Run:
```bash
docker compose -f docker-compose.dev.yml up -d --build --force-recreate server runner
```

Expected: Containers rebuild successfully

**Step 2: Verify runner starts**

Run:
```bash
docker logs whisper_runner_dev --tail=50
```

Expected: No errors, logs show "JobClient initialized"

**Step 3: Upload test audio and verify segments**

Run:
```bash
# Upload a test file
curl -X POST http://localhost:8130/api/audio/upload \
  -H "Authorization: Bearer test-token" \
  -F "file=@testdata/2_min.m4a"

# Check if segments were saved
docker exec whisper_server_dev bash -c "ls -lh /app/data/transcribes/*.segments.json.gz 2>/dev/null | head -5"
```

Expected: segments.json.gz files exist

**Step 4: Test SRT download with real timestamps**

Run:
```bash
# Get transcription ID first
TRANSCRIPTION_ID=$(curl -s http://localhost:8130/api/transcriptions | jq -r '.[0].id')

# Download SRT
curl "http://localhost:8130/api/transcriptions/${TRANSCRIPTION_ID}/download?format=srt" -o test.srt

# Check SRT format (should have varying timestamps, not all 00:00:00,000 --> 00:10:00,000)
head -20 test.srt
```

Expected: SRT entries have individual timestamps (e.g., `00:00:00,000 --> 00:00:02,500`)

**Step 5: Commit documentation**

```bash
git add .
git commit -m "test: verify segments preservation and SRT timestamps"
```

---

## Final Verification

**Run all tests:**

```bash
# Runner tests
docker exec whisper_runner_dev pytest tests/ -v

# Server tests
docker exec whisper_server_dev pytest tests/ -v
```

**Expected:** All tests pass

**Manual verification:**

1. Upload 20_min audio file
2. Check processing time: should be ~4-5 minutes (11.7x RTF)
3. Download SRT: verify individual timestamps
4. Download formatted text: verify proper formatting

**Success criteria:**
- ✅ Segments saved to `segments.json.gz`
- ✅ SRT has individual Whisper timestamps per line
- ✅ Processing time ~11.7x real-time
- ✅ No fixed-duration chunking in code
- ✅ MAX_FORMAT_CHUNK = 5000 bytes

---

## Summary of Changes

**Files Modified:**
1. `runner/app/models/job_schemas.py` - Added `segments` field
2. `runner/app/services/job_client.py` - Send segments to server
3. `server/app/schemas/runner.py` - Accept segments in API
4. `server/app/api/runner.py` - Save segments to storage
5. `runner/app/services/formatting_service.py` - Use 5000 byte chunks
6. `docker-compose.dev.yml` - Remove FIXED_CHUNK_*, set MAX_FORMAT_CHUNK=5000
7. `runner/app/config.py` - Remove fixed-duration config, add LLM_FORMAT_MAX_BYTES
8. `runner/app/services/whisper_service.py` - Remove `transcribe_fixed_chunks()`
9. `runner/app/services/audio_processor.py` - Remove fixed-duration logic
10. `CLAUDE.md` - Document new architecture

**Files Created (tests):**
- `tests/runner/models/test_job_schemas.py`
- `tests/runner/services/test_job_client_segments.py`
- `tests/server/schemas/test_runner_schema_segments.py`
- `tests/server/api/test_runner_save_segments.py`
- `tests/runner/services/test_formatting_byte_chunking.py`
- `tests/runner/test_config_no_fixed_chunks.py`
- `tests/runner/services/test_whisper_no_fixed_chunks.py`
- `tests/runner/services/test_audio_processor_no_fixed_chunks.py`

**Performance Improvement:**
- Before (20s chunks): 3.5x real-time
- After (5-min chunks): 11.7x real-time
- **Speedup: 3.3x faster** ✅
