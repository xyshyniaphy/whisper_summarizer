#!/usr/bin/env python3
"""Test script for audio upload API with different file sizes."""
import asyncio
import time
import requests
import json
from pathlib import Path

# API endpoints (use port 3000 with Vite proxy)
BASE_URL = "http://localhost:3000"
UPLOAD_URL = f"{BASE_URL}/api/audio/upload"
STATUS_URL = f"{BASE_URL}/api/transcriptions"

# Test files
TEST_FILES = [
    ("2_min.m4a", "2 minutes"),
    ("20_min.m4a", "20 minutes"),
    ("60_min.m4a", "60 minutes"),
    ("210_min.m4a", "210 minutes"),
]

TESTDATA_DIR = Path("/home/lmr/ws/whisper_summarizer/testdata")


def format_duration(seconds):
    """Format seconds to readable duration."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def upload_audio(file_path: str) -> str | None:
    """Upload audio file and return transcription ID."""
    print(f"\n{'='*60}")
    print(f"Uploading: {file_path}")
    print(f"{'='*60}")

    full_path = TESTDATA_DIR / file_path
    if not full_path.exists():
        print(f"ERROR: File not found: {full_path}")
        return None

    file_size = full_path.stat().st_size / (1024 * 1024)  # MB
    print(f"File size: {file_size:.2f} MB")

    start_time = time.time()

    try:
        with open(full_path, "rb") as f:
            files = {"file": (file_path, f, "audio/mp4")}
            response = requests.post(UPLOAD_URL, files=files, timeout=300)

        upload_time = time.time() - start_time
        print(f"Upload time: {format_duration(upload_time)}")

        if response.status_code in (200, 201):
            data = response.json()
            transcription_id = data.get("id")
            print(f"✓ Upload successful! Transcription ID: {transcription_id}")
            return transcription_id
        else:
            print(f"ERROR: Upload failed with status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None

    except Exception as e:
        print(f"ERROR: Upload exception: {e}")
        return None


def get_transcription_status(transcription_id: str) -> dict | None:
    """Get transcription status."""
    try:
        response = requests.get(f"{STATUS_URL}/{transcription_id}", timeout=30)
        if response.status_code in (200, 201):
            return response.json()
        return None
    except Exception as e:
        print(f"ERROR: Failed to get status: {e}")
        return None


def wait_for_completion(transcription_id: str, timeout_seconds: int = 7200):
    """Wait for transcription to complete."""
    print(f"\nWaiting for transcription to complete...")
    print(f"Timeout: {format_duration(timeout_seconds)}")

    start_time = time.time()
    last_stage = None
    check_interval = 5  # seconds

    while True:
        elapsed = time.time() - start_time

        if elapsed > timeout_seconds:
            print(f"\nERROR: Timeout after {format_duration(timeout_seconds)}")
            break

        status = get_transcription_status(transcription_id)
        if not status:
            print(f"ERROR: Failed to get status")
            time.sleep(check_interval)
            continue

        stage = status.get("stage", "unknown")

        # Print stage changes
        if stage != last_stage:
            print(f"[{format_duration(elapsed)}] Stage: {stage}")
            last_stage = stage

        # Check completion
        if stage == "completed":
            total_time = time.time() - start_time
            print(f"\n✓ Transcription completed!")
            print(f"Total time: {format_duration(total_time)}")

            # Print transcription details
            text_length = len(status.get("original_text", ""))
            duration = status.get("duration_seconds")
            language = status.get("language", "unknown")

            if duration:
                print(f"  Audio duration: {format_duration(duration)}")
            print(f"  Text length: {text_length} characters")
            print(f"  Language: {language}")

            if duration and duration > 0:
                speedup = duration / total_time if total_time > 0 else 0
                print(f"  Speedup: {speedup:.1f}x real-time")

            return True

        elif stage == "failed":
            total_time = time.time() - start_time
            error = status.get("error_message", "Unknown error")
            print(f"\n✗ Transcription failed!")
            print(f"Total time: {format_duration(total_time)}")
            print(f"Error: {error}")
            return False

        # Progress indicator
        dots = int((elapsed % check_interval) / check_interval * 3)
        print(f"\r[{format_duration(elapsed)}] {'.' * dots}{' ' * (3-dots)}", end="", flush=True)

        time.sleep(check_interval)

    return False


def test_file(file_name: str, description: str):
    """Test a single audio file."""
    print(f"\n\n{'#'*60}")
    print(f"# Testing: {description} ({file_name})")
    print(f"{'#'*60}")

    overall_start = time.time()

    # Upload
    transcription_id = upload_audio(file_name)
    if not transcription_id:
        print(f"\n✗ Test FAILED: Could not upload file")
        return False

    # Wait for completion
    success = wait_for_completion(transcription_id)

    overall_time = time.time() - overall_start
    print(f"\nOverall time: {format_duration(overall_time)}")

    if success:
        print(f"✓ Test PASSED")
    else:
        print(f"✗ Test FAILED")

    return success


def main():
    """Run all tests."""
    print("=" * 60)
    print("Audio Upload API Test")
    print("=" * 60)

    results = {}

    for file_name, description in TEST_FILES:
        results[description] = test_file(file_name, description)

    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for description, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{description:20s}: {status}")

    all_passed = all(results.values())
    print(f"\n{'='*60}")
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
