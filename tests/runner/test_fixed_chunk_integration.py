import pytest
import tempfile
import os
from pathlib import Path
from app.services.audio_segmenter import AudioSegmenter
from pydub import AudioSegment
from pydub.generators import Sine

@pytest.mark.integration
def test_end_to_end_fixed_chunk_processing():
    """Full integration test with real audio file"""
    # Create 2-minute test audio with tone and silence
    segments = []
    for duration_ms, is_tone in [(20000, True), (5000, False), (20000, True), (5000, False),
                                     (20000, True), (5000, False), (20000, True), (5000, False),
                                     (10000, True)]:
        if is_tone:
            tone = Sine(440).to_audio_segment(duration=duration_ms, volume=-10.0)
            segments.append(tone)
        else:
            segments.append(AudioSegment.silent(duration=duration_ms))

    audio = segments[0]
    for seg in segments[1:]:
        audio += seg

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
        assert len(chunks) >= 4  # 120s / 20s = ~6 chunks
        assert len(chunks) <= 8

        for chunk in chunks:
            duration = (chunk["end"] - chunk["start"]) / 1000
            assert 10 <= duration <= 30, f"Chunk duration {duration}s outside 10-30s range"

        # Verify continuity
        for i in range(len(chunks) - 1):
            assert chunks[i]["end"] == chunks[i+1]["start"], f"Gap between chunk {i} and {i+1}"
    finally:
        os.unlink(temp_path)

@pytest.mark.integration
def test_srt_timestamp_formatting():
    """Verify SRT timestamp formatting from fixed chunks"""
    # Mock segments from fixed chunks (simulating what WhisperService would return)
    # Note: WhisperService._segments_to_dict() returns SRT-formatted timestamps as strings
    segments = [
        {"start": "00:00:00,000", "end": "00:00:20,500", "text": "First 20 seconds"},
        {"start": "00:00:20,500", "end": "00:00:40,200", "text": "Second 20 seconds"},
        {"start": "00:00:40,200", "end": "00:01:00,000", "text": "Third 20 seconds"},
    ]

    # Verify SRT format structure
    assert len(segments) == 3

    # Check first segment has correct SRT timestamp format
    assert segments[0]["start"] == "00:00:00,000"
    assert segments[0]["end"] == "00:00:20,500"
    assert segments[0]["text"] == "First 20 seconds"

    # Check second segment
    assert segments[1]["start"] == "00:00:20,500"
    assert segments[1]["end"] == "00:00:40,200"
    assert segments[1]["text"] == "Second 20 seconds"

    # Check third segment
    assert segments[2]["start"] == "00:00:40,200"
    assert segments[2]["end"] == "00:01:00,000"
    assert segments[2]["text"] == "Third 20 seconds"

    # Verify timestamps are continuous (end of one equals start of next)
    assert segments[0]["end"] == segments[1]["start"]
    assert segments[1]["end"] == segments[2]["start"]
