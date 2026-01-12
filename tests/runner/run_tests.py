#!/usr/bin/env python3
"""
Test runner for audio segmenter (without pytest dependency)
"""
import sys
import os

# Add runner app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'runner'))

from app.services.audio_segmenter import AudioSegmenter
from pydub import AudioSegment
import tempfile


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, test_name):
        self.passed += 1
        print(f"✅ {test_name}")

    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, error))
        print(f"❌ {test_name}")
        print(f"   {error}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.errors:
            print(f"\nFailed Tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print(f"{'='*50}")
        return self.failed == 0


def test_segmenter_creates_fixed_chunks():
    """Should create chunks close to target duration"""
    try:
        audio = AudioSegment.silent(duration=60000)  # 60 seconds
        segmenter = AudioSegmenter(
            target_duration_seconds=20,
            min_duration_seconds=10,
            max_duration_seconds=30,
            silence_threshold=-40,
            min_silence_duration=0.5,
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio.export(f.name, format="wav")
            temp_path = f.name

        try:
            chunks = segmenter.segment(temp_path)
            # 60s audio with 20s target = ~3 chunks
            assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"
            assert len(chunks) <= 4, f"Expected at most 4 chunks, got {len(chunks)}"
            return True, None
        finally:
            os.unlink(temp_path)
    except Exception as e:
        return False, str(e)


def test_segmenter_respects_min_max_duration():
    """Each chunk should be within min-max bounds"""
    try:
        audio = AudioSegment.silent(duration=60000)  # 60 seconds
        segmenter = AudioSegmenter(
            target_duration_seconds=20,
            min_duration_seconds=10,
            max_duration_seconds=30,
            silence_threshold=-40,
            min_silence_duration=0.5,
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio.export(f.name, format="wav")
            temp_path = f.name

        try:
            chunks = segmenter.segment(temp_path)
            for i, chunk in enumerate(chunks):
                duration = (chunk["end"] - chunk["start"]) / 1000  # Convert ms to s
                assert 10 <= duration <= 30, f"Chunk {i} duration {duration}s not in range [10, 30]"
            return True, None
        finally:
            os.unlink(temp_path)
    except Exception as e:
        return False, str(e)


def test_segmenter_preserves_timeline_continuity():
    """Chunk timestamps should be continuous without gaps"""
    try:
        audio = AudioSegment.silent(duration=60000)  # 60 seconds
        segmenter = AudioSegmenter(
            target_duration_seconds=20,
            min_duration_seconds=10,
            max_duration_seconds=30,
            silence_threshold=-40,
            min_silence_duration=0.5,
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio.export(f.name, format="wav")
            temp_path = f.name

        try:
            chunks = segmenter.segment(temp_path)
            for i in range(len(chunks) - 1):
                assert chunks[i]["end"] == chunks[i+1]["start"], f"Gap between chunk {i} and {i+1}"
            return True, None
        finally:
            os.unlink(temp_path)
    except Exception as e:
        return False, str(e)


def test_segmenter_handles_short_audio():
    """Audio shorter than min_duration should return single chunk"""
    try:
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
            assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"
            assert chunks[0]["start"] == 0, f"Expected start=0, got {chunks[0]['start']}"
            assert chunks[0]["end"] == 5000, f"Expected end=5000, got {chunks[0]['end']}"
            return True, None
        finally:
            os.unlink(temp_path)
    except Exception as e:
        return False, str(e)


if __name__ == "__main__":
    results = TestResults()

    print("Running Audio Segmenter Tests...\n")

    passed, error = test_segmenter_creates_fixed_chunks()
    if passed:
        results.add_pass("test_segmenter_creates_fixed_chunks")
    else:
        results.add_fail("test_segmenter_creates_fixed_chunks", error)

    passed, error = test_segmenter_respects_min_max_duration()
    if passed:
        results.add_pass("test_segmenter_respects_min_max_duration")
    else:
        results.add_fail("test_segmenter_respects_min_max_duration", error)

    passed, error = test_segmenter_preserves_timeline_continuity()
    if passed:
        results.add_pass("test_segmenter_preserves_timeline_continuity")
    else:
        results.add_fail("test_segmenter_preserves_timeline_continuity", error)

    passed, error = test_segmenter_handles_short_audio()
    if passed:
        results.add_pass("test_segmenter_handles_short_audio")
    else:
        results.add_fail("test_segmenter_handles_short_audio", error)

    success = results.summary()
    sys.exit(0 if success else 1)
