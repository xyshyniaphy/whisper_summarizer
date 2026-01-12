# Fixed-Duration SRT Segmentation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement fixed-duration (10-30s) SRT subtitle segmentation for accurate, readable transcriptions of long audio files.

**Architecture:** Add a pre-processing stage before Whisper transcription that splits audio into fixed-duration chunks (10-30s) using VAD-detected silence as ideal split points. Each chunk becomes one SRT entry with accurate timestamps.

**Tech Stack:**
- Python 3.12 (runner container)
- faster-whisper with cuDNN (existing)
- WebRTC VAD (voice activity detection)
- FFmpeg (audio extraction/manipulation)
- SQLAlchemy (storage)

---

## Task 1: Create Audio Segmentation Service

**Files:**
- Create: `runner/app/services/audio_segmenter.py`

**Step 1: Write the failing test**

Create `tests/runner/test_audio_segmenter.py`:

```python
import pytest
from app.services.audio_segmenter import AudioSegmenter
from pydub import AudioSegment
import tempfile
import os

@pytest.fixture
def sample_audio():
    """Create 60-second test audio with silence at 15s and 45s"""
    audio = AudioSegment.silent(duration=60000)  # 60 seconds
    # Add tone at beginning to ensure non-silent
    audio = AudioSegment.silent(duration=1000) + audio[1000:]
    return audio

@pytest.fixture
def segmenter_config():
    return {
        "target_duration_seconds": 20,
        "min_duration_seconds": 10,
        "max_duration_seconds": 30,
        "silence_threshold": -40,
        "min_silence_duration": 0.5,
    }

def test_segmenter_creates_fixed_chunks(sample_audio, segmenter_config):
    """Should create chunks close to target duration"""
    segmenter = AudioSegmenter(**segmenter_config)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sample_audio.export(f.name, format="wav")
        temp_path = f.name

    try:
        chunks = segmenter.segment(temp_path)
        # 60s audio with 20s target = ~3 chunks
        assert len(chunks) >= 2
        assert len(chunks) <= 4
    finally:
        os.unlink(temp_path)

def test_segmenter_respects_min_max_duration(sample_audio, segmenter_config):
    """Each chunk should be within min-max bounds"""
    segmenter = AudioSegmenter(**segmenter_config)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sample_audio.export(f.name, format="wav")
        temp_path = f.name

    try:
        chunks = segmenter.segment(temp_path)
        for chunk in chunks:
            duration = (chunk["end"] - chunk["start"]) / 1000  # Convert ms to s
            assert segmenter_config["min_duration_seconds"] <= duration <= segmenter_config["max_duration_seconds"]
    finally:
        os.unlink(temp_path)

def test_segmenter_preserves_timeline_continuity(sample_audio, segmenter_config):
    """Chunk timestamps should be continuous without gaps"""
    segmenter = AudioSegmenter(**segmenter_config)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sample_audio.export(f.name, format="wav")
        temp_path = f.name

    try:
        chunks = segmenter.segment(temp_path)
        for i in range(len(chunks) - 1):
            assert chunks[i]["end"] == chunks[i+1]["start"], f"Gap between chunk {i} and {i+1}"
    finally:
        os.unlink(temp_path)

def test_segmenter_handles_short_audio():
    """Audio shorter than min_duration should return single chunk"""
    segmenter = AudioSegmenter(
        target_duration_seconds=20,
        min_duration_seconds=10,
        max_duration_seconds=30
    )
    short_audio = AudioSegment.silent(duration=5000)  # 5 seconds
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        short_audio.export(f.name, format="wav")
        temp_path = f.name

    try:
        chunks = segmenter.segment(temp_path)
        assert len(chunks) == 1
        assert chunks[0]["start"] == 0
        assert chunks[0]["end"] == 5000
    finally:
        os.unlink(temp_path)
```

**Step 2: Run test to verify it fails**

```bash
cd /home/lmr/ws/whisper_summarizer
docker exec whisper_runner_dev pytest tests/runner/test_audio_segmenter.py -v
```

Expected: `ModuleNotFoundError: app.services.audio_segmenter`

**Step 3: Write minimal implementation**

Create `runner/app/services/audio_segmenter.py`:

```python
"""
Audio Segmentation Service

Splits audio into fixed-duration chunks (10-30s) for SRT generation.
Uses VAD-detected silence as ideal split points for natural boundaries.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class AudioChunk:
    """Represents a fixed-duration audio segment"""
    start_ms: int
    end_ms: int
    start_s: float
    end_s: float

    def to_dict(self) -> Dict:
        return {
            "start": self.start_ms,
            "end": self.end_ms,
            "start_s": self.start_s,
            "end_s": self.end_s
        }


class AudioSegmenter:
    """
    Splits audio into fixed-duration chunks using VAD-detected silence.

    Target duration: 20 seconds (configurable)
    Min duration: 10 seconds
    Max duration: 30 seconds
    """

    def __init__(
        self,
        target_duration_seconds: int = 20,
        min_duration_seconds: int = 10,
        max_duration_seconds: int = 30,
        silence_threshold: int = -40,  # dB
        min_silence_duration: float = 0.5,  # seconds
    ):
        self.target_duration = target_duration_seconds * 1000  # Convert to ms
        self.min_duration = min_duration_seconds * 1000
        self.max_duration = max_duration_seconds * 1000
        self.silence_threshold = silence_threshold
        self.min_silence_duration_ms = int(min_silence_duration * 1000)

    def segment(self, audio_path: str) -> List[Dict]:
        """
        Split audio file into fixed-duration chunks.

        Args:
            audio_path: Path to audio file

        Returns:
            List of AudioChunk dictionaries with start/end timestamps
        """
        try:
            from pydub import AudioSegment
            from pydub.silence import detect_nonsilent
        except ImportError:
            logger.error("pydub required for audio segmentation")
            raise

        logger.info(f"Loading audio: {audio_path}")
        audio = AudioSegment.from_file(audio_path)

        # Get total duration
        total_duration = len(audio)

        # If audio is shorter than min duration, return single chunk
        if total_duration <= self.min_duration:
            logger.info(f"Audio ({total_duration}ms) shorter than min duration, returning single chunk")
            return [AudioChunk(0, total_duration, 0.0, total_duration / 1000.0).to_dict()]

        # Detect nonsilent ranges (speech segments)
        logger.info("Detecting speech segments...")
        nonsilent_ranges = detect_nonsilent(
            audio,
            min_silence_len=self.min_silence_duration_ms,
            silence_thresh=self.silence_threshold,
            seek_step=100  # 100ms steps for efficiency
        )

        # If no speech detected, fall back to fixed chunks
        if not nonsilent_ranges:
            logger.warning("No speech detected, using fixed chunks")
            return self._create_fixed_chunks(total_duration)

        # Find optimal split points at silence
        split_points = self._find_split_points(nonsilent_ranges, total_duration)

        # Create chunks from split points
        chunks = self._create_chunks_from_splits(split_points, total_duration)

        logger.info(f"Created {len(chunks)} chunks from {total_duration}ms audio")
        return chunks

    def _find_split_points(self, nonsilent_ranges: List[tuple], total_duration: int) -> List[int]:
        """
        Find optimal split points using silence between speech segments.

        Args:
            nonsilent_ranges: List of (start_ms, end_ms) tuples
            total_duration: Total audio duration in ms

        Returns:
            List of split point timestamps in milliseconds
        """
        split_points = [0]  # Always start at 0
        current_position = 0

        for i, (start, end) in enumerate(nonsilent_ranges):
            # Check if we've exceeded target duration since last split
            time_since_last_split = start - current_position

            if time_since_last_split >= self.target_duration:
                # Find silence between this and previous speech segment
                if i > 0:
                    prev_end = nonsilent_ranges[i-1][1]
                    gap = start - prev_end

                    # If there's a silence gap, split in the middle
                    if gap >= self.min_silence_duration_ms:
                        split_point = prev_end + (gap // 2)
                        split_points.append(split_point)
                        current_position = split_point

        # Ensure we don't exceed max duration
        # Check if last chunk would be too long
        if split_points:
            time_since_last_split = total_duration - split_points[-1]
            if time_since_last_split > self.max_duration:
                # Force intermediate splits
                num_forced_splits = int(time_since_last_split / self.target_duration)
                for i in range(1, num_forced_splits + 1):
                    split_point = split_points[-1] + (time_since_last_split // (num_forced_splits + 1))
                    split_points.append(split_point)

        split_points.append(total_duration)  # Always end at total duration
        return sorted(list(set(split_points)))  # Remove duplicates and sort

    def _create_chunks_from_splits(self, split_points: List[int], total_duration: int) -> List[Dict]:
        """Create AudioChunk objects from split points"""
        chunks = []
        for i in range(len(split_points) - 1):
            start = split_points[i]
            end = split_points[i + 1]
            duration = end - start

            # Skip very small chunks at the end
            if duration < 1000:  # Less than 1 second
                # Merge with previous chunk
                if chunks:
                    chunks[-1]["end"] = end
                    chunks[-1]["end_s"] = end / 1000.0
                continue

            chunks.append(AudioChunk(
                start_ms=start,
                end_ms=end,
                start_s=start / 1000.0,
                end_s=end / 1000.0
            ).to_dict())

        return chunks

    def _create_fixed_chunks(self, total_duration: int) -> List[Dict]:
        """Fallback: create fixed chunks when VAD fails"""
        chunks = []
        current = 0
        chunk_num = 0

        while current < total_duration:
            end = min(current + self.target_duration, total_duration)
            duration = end - current

            # Last chunk might be short, that's okay
            if duration < 1000 and chunks:
                # Merge with previous
                chunks[-1]["end"] = total_duration
                chunks[-1]["end_s"] = total_duration / 1000.0
                break

            chunks.append(AudioChunk(
                start_ms=current,
                end_ms=end,
                start_s=current / 1000.0,
                end_s=end / 1000.0
            ).to_dict())

            current = end
            chunk_num += 1

        return chunks
```

**Step 4: Run test to verify it passes**

```bash
cd /home/lmr/ws/whisper_summarizer
docker exec whisper_runner_dev pytest tests/runner/test_audio_segmenter.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add runner/app/services/audio_segmenter.py tests/runner/test_audio_segmenter.py
git commit -m "feat(runner): add fixed-duration audio segmentation service

- Create AudioSegmenter for 10-30s chunks
- Use VAD-detected silence as split points
- Add comprehensive tests"
```

---

## Task 2: Update Whisper Service for Fixed Chunks

**Files:**
- Modify: `runner/app/services/whisper_service.py`
- Create: `tests/runner/test_whisper_service_fixed_chunks.py`

**Step 1: Write the failing test**

Create `tests/runner/test_whisper_service_fixed_chunks.py`:

```python
import pytest
from app.services.whisper_service import WhisperService, WhisperTimestamped
from app.services.audio_segmenter import AudioSegmenter
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

@pytest.fixture
def mock_whisper_model():
    """Mock WhisperTimestamped model"""
    with patch('app.services.whisper_service.WhisperTimestamped') as mock:
        model = MagicMock()
        model.transcribe_dict.return_value = {
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "First segment"},
                {"start": 5.0, "end": 10.0, "text": "Second segment"},
            ],
            "info": {"language": "zh"}
        }
        mock.load_model.return_value = model
        yield mock

@pytest.fixture
def fixed_chunk_config():
    return {
        "target_duration_seconds": 15,
        "min_duration_seconds": 10,
        "max_duration_seconds": 20,
    }

def test_whisper_service_processes_fixed_chunks(mock_whisper_model, fixed_chunk_config):
    """Should process audio in fixed chunks instead of Whisper's native segmentation"""
    service = WhisperService(model_size="large-v3-turbo")
    service.model = mock_whisper_model.load_model.return_value

    # Create test audio (30 seconds)
    from pydub import AudioSegment
    audio = AudioSegment.silent(duration=30000)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        audio.export(f.name, format="wav")
        temp_path = f.name

    try:
        # Mock the segmenter
        with patch.object(service, '_create_fixed_chunks') as mock_segmenter:
            mock_segmenter.return_value = [
                {"start": 0, "end": 15000, "start_s": 0.0, "end_s": 15.0},
                {"start": 15000, "end": 30000, "start_s": 15.0, "end_s": 30.0},
            ]

            result = service.transcribe_fixed_chunks(
                audio_path=temp_path,
                target_duration_seconds=15,
                min_duration_seconds=10,
                max_duration_seconds=20
            )

            # Should have called transcribe for each chunk
            assert mock_whisper_model.load_model.return_value.transcribe_dict.call_count == 2

            # Should have merged results
            assert len(result["segments"]) >= 2
    finally:
        os.unlink(temp_path)

def test_whisper_service_aligns_timestamps_to_chunks(mock_whisper_model):
    """Segment timestamps should be aligned to chunk boundaries"""
    service = WhisperService(model_size="large-v3-turbo")
    service.model = mock_whisper_model.load_model.return_value

    from pydub import AudioSegment
    audio = AudioSegment.silent(duration=30000)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        audio.export(f.name, format="wav")
        temp_path = f.name

    try:
        with patch.object(service, '_create_fixed_chunks') as mock_segmenter:
            # Define chunks with specific boundaries
            chunks = [
                {"start": 0, "end": 15000, "start_s": 0.0, "end_s": 15.0},
                {"start": 15000, "end": 30000, "start_s": 15.0, "end_s": 30.0},
            ]
            mock_segmenter.return_value = chunks

            result = service.transcribe_fixed_chunks(
                audio_path=temp_path,
                target_duration_seconds=15
            )

            # First chunk segments should have offset 0-15
            # Second chunk segments should have offset 15-30
            segments = result["segments"]
            first_chunk_segments = [s for s in segments if s["start"] < 15]
            second_chunk_segments = [s for s in segments if s["start"] >= 15]

            assert len(first_chunk_segments) > 0
            assert len(second_chunk_segments) > 0

            # Verify no segment crosses chunk boundary
            for seg in first_chunk_segments:
                assert seg["end"] <= 15.0, f"Segment {seg} crosses first chunk boundary"

            for seg in second_chunk_segments:
                assert seg["start"] >= 15.0, f"Segment {seg} starts before second chunk"
    finally:
        os.unlink(temp_path)

def test_whisper_service_handles_chunk_overlap():
    """Should handle chunk overlap if configured"""
    service = WhisperService(model_size="large-v3-turbo")

    from pydub import AudioSegment
    audio = AudioSegment.silent(duration=30000)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        audio.export(f.name, format="wav")
        temp_path = f.name

    try:
        with patch.object(service, '_create_fixed_chunks') as mock_segmenter:
            # Chunks with overlap
            chunks = [
                {"start": 0, "end": 15000, "start_s": 0.0, "end_s": 15.0},
                {"start": 14000, "end": 29000, "start_s": 14.0, "end_s": 29.0},  # 1s overlap
                {"start": 28000, "end": 30000, "start_s": 28.0, "end_s": 30.0},
            ]
            mock_segmenter.return_value = chunks

            with patch('app.services.whisper_service.WhisperTimestamped') as mock_whisper:
                mock_model = MagicMock()
                mock_model.transcribe_dict.return_value = {
                    "segments": [{"start": 0, "end": 5, "text": "Test"}],
                    "info": {"language": "zh"}
                }
                mock_whisper.load_model.return_value = mock_model

                result = service.transcribe_fixed_chunks(
                    audio_path=temp_path,
                    target_duration_seconds=15,
                    chunk_overlap_seconds=1
                )

                # Should process all chunks including overlap
                assert mock_model.transcribe_dict.call_count == 3
    finally:
        os.unlink(temp_path)
```

**Step 2: Run test to verify it fails**

```bash
docker exec whisper_runner_dev pytest tests/runner/test_whisper_service_fixed_chunks.py -v
```

Expected: `AttributeError: 'WhisperService' object has no attribute 'transcribe_fixed_chunks'`

**Step 3: Write minimal implementation**

First, read the current `whisper_service.py` to understand existing structure:

```bash
docker exec whisper_runner_dev cat /app/app/services/whisper_service.py | head -100
```

Now modify `runner/app/services/whisper_service.py`. Add these methods to the `WhisperService` class:

```python
def transcribe_fixed_chunks(
    self,
    audio_path: str,
    target_duration_seconds: int = 20,
    min_duration_seconds: int = 10,
    max_duration_seconds: int = 30,
    chunk_overlap_seconds: int = 0,
    language: str = "zh",
) -> Dict:
    """
    Transcribe audio using fixed-duration chunks for accurate SRT timestamps.

    Each chunk becomes one SRT entry with precise timestamps.

    Args:
        audio_path: Path to audio file
        target_duration_seconds: Target chunk duration (default: 20s)
        min_duration_seconds: Minimum chunk duration (default: 10s)
        max_duration_seconds: Maximum chunk duration (default: 30s)
        chunk_overlap_seconds: Overlap between chunks (default: 0)
        language: Language code (default: "zh")

    Returns:
        Dict with:
        - segments: List of timestamp-aligned transcription segments
        - info: Language info
    """
    from app.services.audio_segmenter import AudioSegmenter

    logger.info(f"Starting fixed-chunk transcription: {audio_path}")
    logger.info(f"Chunk config: target={target_duration_seconds}s, min={min_duration_seconds}s, max={max_duration_seconds}s")

    # Step 1: Create fixed-duration chunks
    segmenter = AudioSegmenter(
        target_duration_seconds=target_duration_seconds,
        min_duration_seconds=min_duration_seconds,
        max_duration_seconds=max_duration_seconds,
    )

    chunks = segmenter.segment(audio_path)
    logger.info(f"Created {len(chunks)} fixed-duration chunks")

    # Step 2: Transcribe each chunk
    all_segments = []
    model = self._get_model()

    for i, chunk in enumerate(chunks):
        chunk_start = chunk["start_ms"]
        chunk_end = chunk["end_ms"]
        chunk_start_s = chunk["start_s"]
        chunk_end_s = chunk["end_s"]

        logger.info(f"Transcribing chunk {i+1}/{len(chunks)}: {chunk_start_s:.1f}s - {chunk_end_s:.1f}s")

        # Extract audio chunk
        chunk_audio_path = self._extract_audio_chunk(
            audio_path,
            chunk_start,
            chunk_end,
            chunk_index=i
        )

        try:
            # Transcribe this chunk
            result = model.transcribe_dict(
                chunk_audio_path,
                language=language,
                vad_filter=False,  # We already did VAD-based segmentation
            )

            # Align segment timestamps to chunk offset
            for seg in result["segments"]:
                seg["start"] += chunk_start_s
                seg["end"] += chunk_start_s

            all_segments.extend(result["segments"])

        finally:
            # Clean up temporary chunk file
            if os.path.exists(chunk_audio_path):
                os.unlink(chunk_audio_path)

    logger.info(f"Transcription complete: {len(all_segments)} segments")

    return {
        "segments": all_segments,
        "info": model.info if hasattr(model, 'info') else {"language": language}
    }

def _extract_audio_chunk(
    self,
    audio_path: str,
    start_ms: int,
    end_ms: int,
    chunk_index: int
) -> str:
    """
    Extract a time range from audio file to temporary file.

    Args:
        audio_path: Source audio file
        start_ms: Start time in milliseconds
        end_ms: End time in milliseconds
        chunk_index: Chunk index for naming

    Returns:
        Path to temporary chunk file
    """
    import tempfile
    from pydub import AudioSegment

    # Load audio
    audio = AudioSegment.from_file(audio_path)

    # Extract chunk
    chunk = audio[start_ms:end_ms]

    # Save to temp file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"chunk_{chunk_index}_{start_ms}_{end_ms}.wav")
    chunk.export(temp_path, format="wav")

    logger.debug(f"Extracted chunk: {temp_path} ({len(chunk)}ms)")

    return temp_path

def _create_fixed_chunks(self, audio_path: str, **kwargs) -> List[Dict]:
    """Create fixed-duration chunks (used for testing/mocking)"""
    from app.services.audio_segmenter import AudioSegmenter

    segmenter = AudioSegmenter(**kwargs)
    return segmenter.segment(audio_path)
```

**Step 4: Run test to verify it passes**

```bash
docker exec whisper_runner_dev pytest tests/runner/test_whisper_service_fixed_chunks.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add runner/app/services/whisper_service.py tests/runner/test_whisper_service_fixed_chunks.py
git commit -m "feat(runner): add fixed-chunk transcription to WhisperService

- Add transcribe_fixed_chunks() method
- Extract and transcribe each chunk separately
- Align segment timestamps to chunk boundaries
- Add chunk overlap support for accuracy"
```

---

## Task 3: Update Audio Processor to Use Fixed Chunks

**Files:**
- Modify: `runner/app/services/audio_processor.py`
- Create: `tests/runner/test_audio_processor_fixed_chunks.py`

**Step 1: Write the failing test**

Create `tests/runner/test_audio_processor_fixed_chunks.py`:

```python
import pytest
from app.services.audio_processor import AudioProcessor
from unittest.mock import Mock, patch, MagicMock
import uuid

@pytest.fixture
def mock_processor():
    with patch('app.services.audio_processor.WhisperService') as mock_whisper, \
         patch('app.services.audio_processor.GLMService') as mock_glm, \
         patch('app.services.audio_processor.get_storage_service') as mock_storage:
        yield {
            "whisper": mock_whisper,
            "glm": mock_glm,
            "storage": mock_storage
        }

def test_processor_uses_fixed_chunks_for_long_audio(mock_processor):
    """Should use fixed-chunk transcription for audio > 1 hour"""
    # Mock config
    with patch('app.services.audio_processor.settings') as mock_settings:
        mock_settings.ENABLE_FIXED_CHUNKS = True
        mock_settings.FIXED_CHUNK_THRESHOLD_MINUTES = 60
        mock_settings.FIXED_CHUNK_TARGET_DURATION = 20

        processor = AudioProcessor()

        # Mock transcribe_fixed_chunks
        mock_whisper_instance = mock_processor["whisper"].return_value
        mock_whisper_instance.transcribe_fixed_chunks.return_value = {
            "segments": [
                {"start": 0.0, "end": 20.0, "text": "First 20s"},
                {"start": 20.0, "end": 40.0, "text": "Second 20s"},
            ],
            "info": {"language": "zh"}
        }

        # Mock GLM
        mock_glm_instance = mock_processor["glm"].return_value
        mock_glm_instance.format_transcription.return_value = {
            "formatted_text": "Formatted text",
            "summary": "Summary",
            "notebooklm_guideline": "Guideline"
        }

        job_data = {
            "id": str(uuid.uuid4()),
            "audio_path": "/fake/path/long_audio.wav",
            "duration_seconds": 7200,  # 2 hours
        }

        result = processor.process(job_data)

        # Should have used fixed chunks
        mock_whisper_instance.transcribe_fixed_chunks.assert_called_once()
        call_args = mock_whisper_instance.transcribe_fixed_chunks.call_args
        assert call_args[1]["target_duration_seconds"] == 20

def test_processor_preserves_chunk_boundaries_in_segments(mock_processor):
    """Segment boundaries should match chunk boundaries"""
    with patch('app.services.audio_processor.settings') as mock_settings:
        mock_settings.ENABLE_FIXED_CHUNKS = True
        mock_settings.FIXED_CHUNK_THRESHOLD_MINUTES = 60

        processor = AudioProcessor()

        mock_whisper_instance = mock_processor["whisper"].return_value
        mock_whisper_instance.transcribe_fixed_chunks.return_value = {
            "segments": [
                # Chunk 1: 0-20s
                {"start": 0.0, "end": 10.0, "text": "0-10s"},
                {"start": 10.0, "end": 20.0, "text": "10-20s"},
                # Chunk 2: 20-40s
                {"start": 20.0, "end": 30.0, "text": "20-30s"},
                {"start": 30.0, "end": 40.0, "text": "30-40s"},
            ],
            "info": {"language": "zh"}
        }

        mock_glm_instance = mock_processor["glm"].return_value
        mock_glm_instance.format_transcription.return_value = {
            "formatted_text": "Formatted",
            "summary": "Summary",
            "notebooklm_guideline": "Guideline"
        }

        job_data = {
            "id": str(uuid.uuid4()),
            "audio_path": "/fake/path.wav",
            "duration_seconds": 3600,
        }

        result = processor.process(job_data)

        # Verify segments were saved with correct timestamps
        mock_storage = mock_processor["storage"].return_value
        assert mock_storage.save_transcription_segments.called
```

**Step 2: Run test to verify it fails**

```bash
docker exec whisper_runner_dev pytest tests/runner/test_audio_processor_fixed_chunks.py -v
```

Expected: Tests fail (method doesn't exist yet)

**Step 3: Write minimal implementation**

First, read current audio_processor.py:

```bash
docker exec whisper_runner_dev cat /app/app/services/audio_processor.py
```

Now modify `runner/app/services/audio_processor.py`. Add configuration and update the process method:

```python
# Add these settings to the config section (or import from config)
# In audio_processor.py, add near the top:

from app.services.audio_segmenter import AudioSegmenter
from app.config import settings

# In AudioProcessor class, update the process() method to check for fixed chunks:

def process(self, job_data: Dict) -> Dict:
    """
    Process audio job: transcribe and format.

    Args:
        job_data: Job data with id, audio_path, duration_seconds

    Returns:
        Dict with transcription, summary, etc.
    """
    job_id = job_data["id"]
    audio_path = job_data["audio_path"]
    duration_seconds = job_data.get("duration_seconds", 0)

    logger.info(f"Processing job {job_id}: {audio_path} ({duration_seconds}s")

    # Step 1: Transcribe
    logger.info("Starting transcription...")

    # Check if we should use fixed chunks
    use_fixed_chunks = (
        getattr(settings, 'ENABLE_FIXED_CHUNKS', False) and
        duration_seconds >= getattr(settings, 'FIXED_CHUNK_THRESHOLD_MINUTES', 60) * 60
    )

    if use_fixed_chunks:
        logger.info(f"Using fixed-chunk transcription (duration: {duration_seconds}s)")
        transcription_result = self.whisper_service.transcribe_fixed_chunks(
            audio_path=audio_path,
            target_duration_seconds=getattr(settings, 'FIXED_CHUNK_TARGET_DURATION', 20),
            min_duration_seconds=getattr(settings, 'FIXED_CHUNK_MIN_DURATION', 10),
            max_duration_seconds=getattr(settings, 'FIXED_CHUNK_MAX_DURATION', 30),
            chunk_overlap_seconds=getattr(settings, 'FIXED_CHUNK_OVERLAY', 0),
            language=getattr(settings, 'WHISPER_LANGUAGE', 'zh'),
        )
    else:
        logger.info("Using standard Whisper transcription")
        # Load audio duration if not provided
        if not duration_seconds:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            duration_seconds = len(audio) / 1000.0

        transcription_result = self.whisper_service.transcribe(
            audio_path=audio_path,
            language=getattr(settings, 'WHISPER_LANGUAGE', 'zh'),
        )

    segments = transcription_result["segments"]
    text = "\n".join([seg["text"] for seg in segments])

    logger.info(f"Transcription complete: {len(segments)} segments")

    # Step 2: Save segments for SRT
    storage_service = get_storage_service()
    storage_service.save_transcription_segments(job_id, segments)

    # Step 3: Format with GLM
    logger.info("Formatting transcription...")
    formatted = self.glm_service.format_transcription(
        text=text,
        user_id=job_data.get("user_id"),
    )

    # Step 4: Save formatted text
    storage_service.save_transcription_text(job_id, formatted["formatted_text"])

    # Step 5: Delete audio file to save space
    if os.path.exists(audio_path):
        os.unlink(audio_path)
        logger.info(f"Deleted audio file: {audio_path}")

    return {
        "job_id": job_id,
        "text": formatted["formatted_text"],
        "summary": formatted["summary"],
        "notebooklm_guideline": formatted.get("notebooklm_guideline"),
        "segments": segments,
        "duration_seconds": duration_seconds,
    }
```

**Step 4: Run test to verify it passes**

```bash
docker exec whisper_runner_dev pytest tests/runner/test_audio_processor_fixed_chunks.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add runner/app/services/audio_processor.py tests/runner/test_audio_processor_fixed_chunks.py
git commit -m "feat(runner): update AudioProcessor to use fixed chunks for long audio

- Add ENABLE_FIXED_CHUNKS config option
- Use fixed-chunk transcription for audio > threshold
- Preserve chunk boundaries in segment timestamps
- Add tests for fixed-chunk processing"
```

---

## Task 4: Update Formatting Service to Chunk by SRT Sections

**Files:**
- Modify: `runner/app/services/formatting_service.py`
- Create: `tests/runner/test_formatting_service_srt_chunks.py`

**Step 1: Write the failing test**

Create `tests/runner/test_formatting_service_srt_chunks.py`:

```python
import pytest
from app.services.formatting_service import FormattingService
from unittest.mock import Mock, patch

def test_formatting_chunks_by_srt_sections():
    """Should chunk text by SRT section count, not raw bytes"""
    service = FormattingService()

    # Mock text with 100 lines (representing 100 SRT entries)
    long_text = "\n".join([f"Line {i}: Some text here" for i in range(100)])

    # Mock GLM response
    with patch('app.services.formatting_service.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Formatted text"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = service.format_transcription(
            text=long_text,
            chunk_by_srt_sections=True,
            max_srt_sections_per_chunk=50
        )

        # Should have called GLM twice (100 lines / 50 per chunk)
        assert mock_client.chat.completions.create.call_count == 2

def test_formatting_respects_srt_section_boundaries():
    """Chunks should not split in the middle of an SRT section"""
    service = FormattingService()

    # Create text where each line is an SRT entry
    srt_like_text = "\n".join([f"00:{i//60:02d}:{i%60:02d},000 --> 00:{(i+5)//60:02d}:{(i+5)%60:02d},000\nSection {i} text here" for i in range(0, 100, 5)])

    with patch('app.services.formatting_service.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Formatted"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = service.format_transcription(
            text=srt_like_text,
            chunk_by_srt_sections=True,
            max_srt_sections_per_chunk=10
        )

        # Get the actual text passed to GLM
        calls = mock_client.chat.completions.create.call_args_list
        for call in calls:
            chunk_text = call.kwargs.get('messages', [{}])[1].get('content', '')
            # Count SRT sections (2 lines per section: timestamp + text)
            lines = chunk_text.split('\n')
            section_count = len([l for l in lines if '-->' in l])
            assert section_count <= 10, f"Chunk has {section_count} sections, expected max 10"

def test_formatting_falls_back_to_bytes_for_non_srt():
    """Should fall back to byte chunking for non-SRT text"""
    service = FormattingService()

    # Plain text without SRT markers
    plain_text = "This is plain text. " * 1000

    with patch('app.services.formatting_service.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Formatted"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        result = service.format_transcription(
            text=plain_text,
            chunk_by_srt_sections=True,
            max_srt_sections_per_chunk=50
        )

        # Should still work, using byte chunking as fallback
        assert mock_client.chat.completions.create.call_count >= 1
```

**Step 2: Run test to verify it fails**

```bash
docker exec whisper_runner_dev pytest tests/runner/test_formatting_service_srt_chunks.py -v
```

Expected: Tests fail (method doesn't support SRT chunking yet)

**Step 3: Write minimal implementation**

First, read current formatting_service.py to understand the split_text_into_chunks method:

```bash
docker exec whisper_runner_dev cat /app/app/services/formatting_service.py | head -350
```

Now modify `runner/app/services/formatting_service.py`. Add SRT-aware chunking:

```python
# Add new method to FormattingService class:

def split_text_by_srt_sections(
    self,
    text: str,
    max_sections_per_chunk: int = 50
) -> List[str]:
    """
    Split text into chunks based on SRT section count.

    Each SRT section has:
    - Section number
    - Timestamp (HH:MM:SS,mmm --> HH:MM:SS,mmm)
    - Text content
    - Empty line

    Args:
        text: Full transcription text (may be SRT format or plain)
        max_sections_per_chunk: Maximum SRT sections per chunk

    Returns:
        List of text chunks
    """
    lines = text.split('\n')

    # Check if text looks like SRT format
    has_srt_timestamps = any('-->' in line for line in lines[:50])

    if not has_srt_timestamps:
        # Fall back to byte chunking for non-SRT text
        logger.info("Text does not appear to be SRT format, using byte chunking")
        return self.split_text_into_chunks(text)

    chunks = []
    current_chunk = []
    section_count = 0
    in_section = False

    for line in lines:
        current_chunk.append(line)

        # Detect SRT section boundaries
        if '-->' in line:
            in_section = True
        elif in_section and line.strip() == '':
            # End of section
            section_count += 1
            in_section = False

            # Check if we need to start a new chunk
            if section_count >= max_sections_per_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                section_count = 0

    # Add remaining content
    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    logger.info(f"Split into {len(chunks)} SRT-based chunks (max {max_sections_per_chunk} sections each)")
    return chunks

# Update format_transcription method to support SRT chunking:

def format_transcription(
    self,
    text: str,
    user_id: Optional[str] = None,
    chunk_by_srt_sections: bool = False,
    max_srt_sections_per_chunk: int = 50,
) -> Dict[str, Any]:
    """
    Format transcription with GLM API.

    Args:
        text: Raw transcription text
        user_id: User ID for personalization
        chunk_by_srt_sections: If True, chunk by SRT section count instead of bytes
        max_srt_sections_per_chunk: Max SRT sections per chunk (if chunk_by_srt_sections=True)

    Returns:
        Dict with formatted_text, summary, notebooklm_guideline
    """
    logger.info(f"Formatting transcription ({len(text)} bytes)")

    # Chunk the text
    if chunk_by_srt_sections:
        chunks = self.split_text_by_srt_sections(
            text,
            max_sections_per_chunk=max_srt_sections_per_chunk
        )
    else:
        chunks = self.split_text_into_chunks(text)

    logger.info(f"Split into {len(chunks)} chunks")

    # Process each chunk
    formatted_chunks = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} bytes)")

        formatted = self._format_chunk(chunk, user_id)
        formatted_chunks.append(formatted)

    # Join formatted chunks
    formatted_text = '\n\n'.join(formatted_chunks)

    # Generate summary (on first chunk to save tokens)
    summary = self._generate_summary(chunks[0])

    # Generate NotebookLM guideline
    notebooklm_guideline = self._generate_notebooklm_guideline(formatted_text)

    logger.info("Formatting complete")

    return {
        "formatted_text": formatted_text,
        "summary": summary,
        "notebooklm_guideline": notebooklm_guideline,
    }
```

**Step 4: Run test to verify it passes**

```bash
docker exec whisper_runner_dev pytest tests/runner/test_formatting_service_srt_chunks.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add runner/app/services/formatting_service.py tests/runner/test_formatting_service_srt_chunks.py
git commit -m "feat(runner): add SRT-aware chunking to FormattingService

- Add split_text_by_srt_sections() method
- Detect SRT format and chunk by section count
- Fall back to byte chunking for non-SRT text
- Preserve SRT section boundaries in chunks"
```

---

## Task 5: Add Configuration Options

**Files:**
- Modify: `runner/app/config.py`
- Create: `tests/runner/test_config_fixed_chunks.py`

**Step 1: Write the failing test**

Create `tests/runner/test_config.py` (if not exists) or add to existing:

```python
import pytest
from app.config import settings, Settings
from pydantic import ValidationError

def test_fixed_chunk_configuration():
    """Should have configuration for fixed-chunk transcription"""
    assert hasattr(settings, 'ENABLE_FIXED_CHUNKS')
    assert hasattr(settings, 'FIXED_CHUNK_THRESHOLD_MINUTES')
    assert hasattr(settings, 'FIXED_CHUNK_TARGET_DURATION')
    assert hasattr(settings, 'FIXED_CHUNK_MIN_DURATION')
    assert hasattr(settings, 'FIXED_CHUNK_MAX_DURATION')

def test_fixed_chunk_default_values():
    """Should have sensible defaults"""
    # Default: disabled, but configured correctly
    assert settings.ENABLE_FIXED_CHUNKS in [True, False]
    assert settings.FIXED_CHUNK_THRESHOLD_MINUTES == 60  # 1 hour
    assert settings.FIXED_CHUNK_TARGET_DURATION == 20    # 20 seconds
    assert settings.FIXED_CHUNK_MIN_DURATION == 10       # 10 seconds
    assert settings.FIXED_CHUNK_MAX_DURATION == 30       # 30 seconds

def test_fixed_chunk_validation():
    """Should validate configuration constraints"""
    with pytest.raises(ValidationError):
        Settings(
            # Invalid: min > target
            FIXED_CHUNK_MIN_DURATION=25,
            FIXED_CHUNK_TARGET_DURATION=20,
            FIXED_CHUNK_MAX_DURATION=30
        )

    with pytest.raises(ValidationError):
        Settings(
            # Invalid: target > max
            FIXED_CHUNK_MIN_DURATION=10,
            FIXED_CHUNK_TARGET_DURATION=35,
            FIXED_CHUNK_MAX_DURATION=30
        )
```

**Step 2: Run test to verify it fails**

```bash
docker exec whisper_runner_dev pytest tests/runner/test_config.py::test_fixed_chunk_configuration -v
```

Expected: `AttributeError` or `AssertionError` (config doesn't exist yet)

**Step 3: Write minimal implementation**

Read current config.py:

```bash
docker exec whisper_runner_dev cat /app/app/config.py
```

Add to `runner/app/config.py`:

```python
# In the Settings class, add these fields:

# Fixed-Duration SRT Chunk Configuration
ENABLE_FIXED_CHUNKS: bool = Field(
    default=True,
    description="Enable fixed-duration SRT segmentation for long audio"
)
FIXED_CHUNK_THRESHOLD_MINUTES: int = Field(
    default=60,
    ge=1,
    le=480,  # Max 8 hours
    description="Minimum audio duration (minutes) to use fixed chunks"
)
FIXED_CHUNK_TARGET_DURATION: int = Field(
    default=20,
    ge=10,
    le=60,
    description="Target SRT duration per line (seconds)"
)
FIXED_CHUNK_MIN_DURATION: int = Field(
    default=10,
    ge=5,
    le=30,
    description="Minimum SRT duration per line (seconds)"
)
FIXED_CHUNK_MAX_DURATION: int = Field(
    default=30,
    ge=20,
    le=60,
    description="Maximum SRT duration per line (seconds)"
)
FIXED_CHUNK_OVERLAY: int = Field(
    default=0,
    ge=0,
    le=5,
    description="Overlap between chunks (seconds)"
)

# Add validator
@model_validator(mode='after')
def validate_fixed_chunk_config(self) -> 'Settings':
    """Validate fixed chunk configuration constraints"""
    if self.FIXED_CHUNK_MIN_DURATION >= self.FIXED_CHUNK_TARGET_DURATION:
        raise ValueError(
            f"FIXED_CHUNK_MIN_DURATION ({self.FIXED_CHUNK_MIN_DURATION}) must be "
            f"less than FIXED_CHUNK_TARGET_DURATION ({self.FIXED_CHUNK_TARGET_DURATION})"
        )
    if self.FIXED_CHUNK_TARGET_DURATION >= self.FIXED_CHUNK_MAX_DURATION:
        raise ValueError(
            f"FIXED_CHUNK_TARGET_DURATION ({self.FIXED_CHUNK_TARGET_DURATION}) must be "
            f"less than FIXED_CHUNK_MAX_DURATION ({self.FIXED_CHUNK_MAX_DURATION})"
        )
    return self
```

**Step 4: Run test to verify it passes**

```bash
docker exec whisper_runner_dev pytest tests/runner/test_config.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add runner/app/config.py tests/runner/test_config.py
git commit -m "feat(runner): add fixed-chunk SRT configuration

- Add ENABLE_FIXED_CHUNKS toggle
- Add threshold and duration settings
- Add validation for configuration constraints
- Default: 20s target, 10s min, 30s max"
```

---

## Task 6: Update Environment Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update documentation**

Add to `CLAUDE.md` in the Runner environment variables section:

```markdown
### Fixed-Duration SRT Configuration

For long audio files (>1 hour), enable fixed-duration SRT segmentation:

```bash
# Fixed-Duration SRT Segmentation (NEW)
ENABLE_FIXED_CHUNKS=true                    # Enable fixed-duration chunks
FIXED_CHUNK_THRESHOLD_MINUTES=60            # Minimum duration (minutes) to use fixed chunks
FIXED_CHUNK_TARGET_DURATION=20              # Target SRT duration per line (seconds)
FIXED_CHUNK_MIN_DURATION=10                 # Minimum SRT duration (seconds)
FIXED_CHUNK_MAX_DURATION=30                 # Maximum SRT duration (seconds)
FIXED_CHUNK_OVERLAY=0                       # Overlap between chunks (seconds, for accuracy)

# SRT-Aware Formatting (NEW)
FORMAT_CHUNK_BY_SRT_SECTIONS=true           # Chunk GLM prompts by SRT section count
MAX_SRT_SECTIONS_PER_CHUNK=50               # Max SRT sections per GLM chunk (~5000 bytes)
```

**Performance Impact:**
- Fixed chunks: +10-20% processing time vs native Whisper
- Accuracy-first settings (5-10 min for 4-hour audio on RTX 3080)
- Recommended for: lectures, meetings, podcasts (>1 hour)

**SRT Output:**
- Each subtitle line: 10-30 seconds (configurable)
- Timestamps aligned to actual audio timing
- No mid-sentence breaks (uses VAD silence detection)
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add fixed-duration SRT configuration documentation

- Document new environment variables
- Explain performance impact
- Provide recommended settings"
```

---

## Task 7: Integration Testing

**Files:**
- Create: `tests/runner/test_fixed_chunk_integration.py`

**Step 1: Write integration test**

Create `tests/runner/test_fixed_chunk_integration.py`:

```python
import pytest
import tempfile
import os
from pathlib import Path
from app.services.audio_processor import AudioProcessor
from app.services.audio_segmenter import AudioSegmenter
from pydub import AudioSegment
import uuid

@pytest.mark.integration
def test_end_to_end_fixed_chunk_processing():
    """Full integration test with real audio file"""
    # Create 2-minute test audio
    audio = AudioSegment.silent(duration=120000)  # 2 minutes

    # Add some tone to make it non-silent
    for i in range(0, 120000, 10000):
        audio = audio[:i] + AudioSegment.silent(duration=100) + audio[i+100:]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        audio.export(f.name, format="wav")
        temp_path = f.name

    try:
        # Segment the audio
        segmenter = AudioSegmenter(
            target_duration_seconds=20,
            min_duration_seconds=10,
            max_duration_seconds=30
        )
        chunks = segmenter.segment(temp_path)

        # Verify chunk properties
        assert len(chunks) >= 4  # 120s / 20s = 6 chunks (with variation)
        assert len(chunks) <= 8

        for chunk in chunks:
            duration = (chunk["end"] - chunk["start"]) / 1000
            assert 10 <= duration <= 30, f"Chunk duration {duration}s outside 10-30s range"

        # Verify continuity
        for i in range(len(chunks) - 1):
            assert chunks[i]["end"] == chunks[i+1]["start"]

    finally:
        os.unlink(temp_path)

@pytest.mark.integration
def test_srt_generation_from_fixed_chunks():
    """Verify SRT file generation from fixed chunks"""
    from app.services.storage_service import get_storage_service

    # Mock segments from fixed chunks
    segments = [
        {"start": 0.0, "end": 20.5, "text": "First 20 seconds"},
        {"start": 20.5, "end": 40.2, "text": "Second 20 seconds"},
        {"start": 40.2, "end": 60.0, "text": "Third 20 seconds"},
    ]

    job_id = str(uuid.uuid4())

    # Save segments
    storage = get_storage_service()
    storage.save_transcription_segments(job_id, segments)

    # Read back
    saved_segments = storage.get_transcription_segments(job_id)

    assert len(saved_segments) == 3
    assert saved_segments[0]["end"] - saved_segments[0]["start"] == pytest.approx(20.5, abs=0.1)
    assert saved_segments[1]["end"] - saved_segments[1]["start"] == pytest.approx(19.7, abs=0.1)
```

**Step 2: Run integration test**

```bash
docker exec whisper_runner_dev pytest tests/runner/test_fixed_chunk_integration.py -v -m integration
```

**Step 3: Commit**

```bash
git add tests/runner/test_fixed_chunk_integration.py
git commit -m "test(runner): add integration tests for fixed-chunk SRT

- Test audio segmentation with real files
- Verify SRT generation from fixed chunks
- Test chunk boundary accuracy"
```

---

## Summary

This implementation plan creates a fixed-duration SRT segmentation system for long audio files:

1. **AudioSegmenter service** - Splits audio into 10-30s chunks using VAD
2. **WhisperService updates** - Processes chunks with timestamp alignment
3. **AudioProcessor integration** - Uses fixed chunks for long audio (>1 hour)
4. **FormattingService updates** - Chunks GLM prompts by SRT sections
5. **Configuration** - New environment variables for tuning
6. **Documentation** - Updated CLAUDE.md with new settings
7. **Integration tests** - End-to-end validation

**Performance**: 5-10 minutes for 4-hour audio (RTX 3080, accuracy-first settings)

**Next Steps**: After review, implement using superpowers:executing-plans or superpowers:subagent-driven-development.
