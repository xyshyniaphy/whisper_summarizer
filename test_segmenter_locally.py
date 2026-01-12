#!/usr/bin/env python3
"""
Local test script for audio segmenter
"""
import sys
import os

# Add runner app to path
sys.path.insert(0, '/home/lmr/ws/whisper_summarizer_srt_segmentation/runner')

from app.services.audio_segmenter import AudioSegmenter
from pydub import AudioSegment
import tempfile

def test_segmenter():
    """Quick test of the segmenter"""
    print("Creating test audio...")
    audio = AudioSegment.silent(duration=60000)  # 60 seconds

    print("Creating segmenter...")
    segmenter = AudioSegmenter(
        target_duration_seconds=20,
        min_duration_seconds=10,
        max_duration_seconds=30
    )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        audio.export(f.name, format="wav")
        temp_path = f.name

    try:
        print(f"Segmenting {temp_path}...")
        chunks = segmenter.segment(temp_path)

        print(f"\n✅ Created {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks):
            duration = (chunk["end"] - chunk["start"]) / 1000
            print(f"  Chunk {i+1}: {chunk['start_s']:.1f}s - {chunk['end_s']:.1f}s ({duration:.1f}s)")

        # Verify timeline continuity
        for i in range(len(chunks) - 1):
            assert chunks[i]["end"] == chunks[i+1]["start"], f"Gap between chunk {i} and {i+1}"

        print("\n✅ All assertions passed!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.unlink(temp_path)

if __name__ == "__main__":
    success = test_segmenter()
    sys.exit(0 if success else 1)
