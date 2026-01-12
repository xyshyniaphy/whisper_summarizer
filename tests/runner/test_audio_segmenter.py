"""
Audio Segmenter Tests

Tests for fixed-duration audio segmentation service.
"""

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
