"""
Audio Segmenter Tests

Tests for fixed-duration audio segmentation service.
"""

import pytest
from app.services.audio_segmenter import AudioSegmenter
from pydub import AudioSegment


@pytest.fixture
def sample_audio():
    """Create 60-second test audio with silence at 15s and 45s"""
    from pydub.generators import Sine

    # Create audio with tone segments separated by silence
    segments = []

    # Pattern: 20s tone + 5s silence + 20s tone + 5s silence + 10s tone
    for duration_ms, is_tone in [(20000, True), (5000, False), (20000, True), (5000, False), (10000, True)]:
        if is_tone:
            # Create tone segment
            tone = Sine(440).to_audio_segment(duration=duration_ms, volume=-10.0)
            segments.append(tone)
        else:
            # Silence
            segments.append(AudioSegment.silent(duration=duration_ms))

    audio = segments[0]
    for seg in segments[1:]:
        audio += seg

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


def test_segmenter_creates_fixed_chunks(sample_audio, segmenter_config, tmp_path):
    """Should create chunks close to target duration"""
    segmenter = AudioSegmenter(**segmenter_config)
    temp_file = tmp_path / "test_audio.wav"
    sample_audio.export(str(temp_file), format="wav")

    chunks = segmenter.segment(str(temp_file))
    # 60s audio with 20s target = ~3 chunks
    assert len(chunks) >= 2
    assert len(chunks) <= 4


def test_segmenter_respects_min_max_duration(sample_audio, segmenter_config, tmp_path):
    """Each chunk should be within min-max bounds"""
    segmenter = AudioSegmenter(**segmenter_config)
    temp_file = tmp_path / "test_audio.wav"
    sample_audio.export(str(temp_file), format="wav")

    chunks = segmenter.segment(str(temp_file))
    for chunk in chunks:
        duration = (chunk["end"] - chunk["start"]) / 1000  # Convert ms to s
        assert segmenter_config["min_duration_seconds"] <= duration <= segmenter_config["max_duration_seconds"]


def test_segmenter_preserves_timeline_continuity(sample_audio, segmenter_config, tmp_path):
    """Chunk timestamps should be continuous without gaps"""
    segmenter = AudioSegmenter(**segmenter_config)
    temp_file = tmp_path / "test_audio.wav"
    sample_audio.export(str(temp_file), format="wav")

    chunks = segmenter.segment(str(temp_file))
    for i in range(len(chunks) - 1):
        assert chunks[i]["end"] == chunks[i+1]["start"], f"Gap between chunk {i} and {i+1}"


def test_segmenter_handles_short_audio(tmp_path):
    """Audio shorter than min_duration should return single chunk"""
    segmenter = AudioSegmenter(
        target_duration_seconds=20,
        min_duration_seconds=10,
        max_duration_seconds=30
    )
    short_audio = AudioSegment.silent(duration=5000)  # 5 seconds
    temp_file = tmp_path / "short_audio.wav"
    short_audio.export(str(temp_file), format="wav")

    chunks = segmenter.segment(str(temp_file))
    assert len(chunks) == 1
    assert chunks[0]["start"] == 0
    assert chunks[0]["end"] == 5000


def test_segmenter_enforces_max_duration(tmp_path):
    """Very long audio without silence should be force-split at max_duration"""
    from pydub.generators import Sine

    # Create 90 seconds of continuous tone (no silence gaps)
    tone = Sine(440).to_audio_segment(duration=90000, volume=-10.0)

    segmenter = AudioSegmenter(
        target_duration_seconds=20,
        min_duration_seconds=10,
        max_duration_seconds=30
    )

    temp_file = tmp_path / "long_audio.wav"
    tone.export(str(temp_file), format="wav")

    chunks = segmenter.segment(str(temp_file))
    # No chunk should exceed max duration
    for chunk in chunks:
        duration = (chunk["end"] - chunk["start"]) / 1000
        assert duration <= 30, f"Chunk duration {duration}s exceeds max 30s"
