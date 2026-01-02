#!/usr/bin/env python3
"""Test script for 60-minute audio upload and transcription."""
import time
import requests
from pathlib import Path

# API endpoints (use port 3000 with Vite proxy)
BASE_URL = "http://localhost:3000"
UPLOAD_URL = f"{BASE_URL}/api/audio/upload"
STATUS_URL = f"{BASE_URL}/api/transcriptions"

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


def main():
    """Test 60-minute audio file."""
    print("=" * 60)
    print("60-Minute Audio Transcription Test")
    print("=" * 60)

    file_name = "60_min.m4a"
    full_path = TESTDATA_DIR / file_name

    if not full_path.exists():
        print(f"ERROR: File not found: {full_path}")
        return False

    file_size = full_path.stat().st_size / (1024 * 1024)  # MB
    print(f"File: {file_name}")
    print(f"File size: {file_size:.2f} MB")

    overall_start = time.time()

    # Upload
    print(f"\n{'='*60}")
    print(f"Uploading: {file_name}")
    print(f"{'='*60}")

    upload_start = time.time()
    transcription_id = None

    try:
        with open(full_path, "rb") as f:
            files = {"file": (file_name, f, "audio/mp4")}
            response = requests.post(UPLOAD_URL, files=files, timeout=300)

        upload_time = time.time() - upload_start
        print(f"Upload time: {format_duration(upload_time)}")

        if response.status_code in (200, 201):
            data = response.json()
            transcription_id = data.get("id")
            print(f"✓ Upload successful! Transcription ID: {transcription_id}")
        else:
            print(f"ERROR: Upload failed with status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

    except Exception as e:
        print(f"ERROR: Upload exception: {e}")
        return False

    # Wait for completion
    print(f"\nWaiting for transcription to complete...")
    print(f"Monitoring with logs: docker compose logs -f backend\n")

    start_time = time.time()
    last_stage = None
    check_interval = 5  # seconds
    timeout_seconds = 7200  # 2 hours

    while True:
        elapsed = time.time() - start_time
        overall_elapsed = time.time() - overall_start

        if elapsed > timeout_seconds:
            print(f"\nERROR: Timeout after {format_duration(timeout_seconds)}")
            break

        try:
            response = requests.get(f"{STATUS_URL}/{transcription_id}", timeout=30)
            if response.status_code in (200, 201):
                status = response.json()

                stage = status.get("stage", "unknown")

                # Print stage changes
                if stage != last_stage:
                    print(f"[{format_duration(overall_elapsed)}] Stage: {stage}")
                    last_stage = stage

                # Check completion
                if stage == "completed":
                    total_time = time.time() - overall_start
                    print(f"\n{'='*60}")
                    print(f"✓ Transcription completed!")
                    print(f"{'='*60}")
                    print(f"Total time: {format_duration(total_time)}")

                    # Print transcription details
                    text_length = len(status.get("original_text", ""))
                    duration = status.get("duration_seconds")
                    language = status.get("language", "unknown")

                    if duration:
                        print(f"  Audio duration: {format_duration(duration)}")
                        speedup = duration / total_time if total_time > 0 else 0
                        print(f"  Processing speedup: {speedup:.1f}x real-time")

                    print(f"  Text length: {text_length} characters")
                    print(f"  Language: {language}")

                    # Check for summary
                    if "summaries" in status and status["summaries"]:
                        summary = status["summaries"][0]
                        summary_text = summary.get("summary_text", "")
                        print(f"  Summary: {len(summary_text)} characters")

                    return True

                elif stage == "failed":
                    total_time = time.time() - overall_start
                    error = status.get("error_message", "Unknown error")
                    print(f"\n{'='*60}")
                    print(f"✗ Transcription failed!")
                    print(f"{'='*60}")
                    print(f"Total time: {format_duration(total_time)}")
                    print(f"Error: {error}")
                    return False

        except Exception as e:
            print(f"ERROR: Failed to get status: {e}")

        # Progress indicator
        dots = int((elapsed % check_interval) / check_interval * 3)
        print(f"\r[{format_duration(overall_elapsed)}] Stage: {last_stage or 'waiting'} {'.' * dots}{' ' * (3-dots)}", end="", flush=True)

        time.sleep(check_interval)

    return False


if __name__ == "__main__":
    main()
