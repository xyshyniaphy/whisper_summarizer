#!/usr/bin/env python3
"""Test script for audio upload API with different file sizes - Production mode (port 80)."""
import asyncio
import time
import requests
import json
from pathlib import Path
from typing import Dict, Any

# API endpoints (production - port 80)
BASE_URL = "http://localhost"
UPLOAD_URL = f"{BASE_URL}/api/audio/upload"
STATUS_URL = f"{BASE_URL}/api/transcriptions"

# Test files - test sequentially
TEST_FILES = [
    ("2_min.m4a", "2 minutes", False, 1),      # NO chunking, 1 chunk expected
    ("20_min.m4a", "20 minutes", True, 2),     # chunking, ~2 chunks expected
    ("60_min.m4a", "60 minutes", True, 6),     # chunking, ~6 chunks expected
    ("210_min.m4a", "210 minutes", True, 21),  # chunking, ~21 chunks expected
]

TESTDATA_DIR = Path("/home/lmr/ws/whisper_summarizer/testdata")

# Test results storage
RESULTS: Dict[str, Any] = {}


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
            file_name = data.get("file_name")
            status = data.get("status")
            stage = data.get("stage")

            print(f"✓ Upload successful!")
            print(f"  Transcription ID: {transcription_id}")
            print(f"  File name: {file_name}")
            print(f"  Status: {status}")
            print(f"  Stage: {stage}")
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
    stages_seen = []

    while True:
        elapsed = time.time() - start_time

        if elapsed > timeout_seconds:
            print(f"\nERROR: Timeout after {format_duration(timeout_seconds)}")
            return False, {"error": "timeout", "elapsed": elapsed}

        status = get_transcription_status(transcription_id)
        if not status:
            print(f"ERROR: Failed to get status")
            time.sleep(check_interval)
            continue

        stage = status.get("stage", "unknown")

        # Track stage transitions
        if stage != last_stage:
            print(f"[{format_duration(elapsed)}] Stage: {stage}")
            if stage not in stages_seen:
                stages_seen.append(stage)
            last_stage = stage

        # Check completion
        if stage == "completed":
            total_time = time.time() - start_time
            print(f"\n✓ Transcription completed!")
            print(f"Total time: {format_duration(total_time)}")

            # Collect transcription details
            result = {
                "success": True,
                "total_time": total_time,
                "stages": stages_seen,
                "duration_seconds": status.get("duration_seconds"),
                "language": status.get("language"),
                "text_length": len(status.get("text") or ""),
                "original_text_length": len(status.get("original_text") or ""),
                "storage_path": status.get("storage_path"),
                "error_message": status.get("error_message"),
                "completed_at": status.get("completed_at"),
            }

            # Print details
            duration = result["duration_seconds"]
            if duration:
                print(f"  Audio duration: {format_duration(duration)}")
            print(f"  Text length: {result['text_length']} characters")
            print(f"  Language: {result['language']}")
            print(f"  Storage path: {result['storage_path']}")

            if duration and duration > 0:
                speedup = duration / total_time if total_time > 0 else 0
                print(f"  Speedup: {speedup:.1f}x real-time")

            return True, result

        elif stage == "failed":
            total_time = time.time() - start_time
            error = status.get("error_message", "Unknown error")
            print(f"\n✗ Transcription failed!")
            print(f"Total time: {format_duration(total_time)}")
            print(f"Error: {error}")
            return False, {"error": error, "elapsed": total_time}

        # Progress indicator
        dots = int((elapsed % check_interval) / check_interval * 3)
        print(f"\r[{format_duration(elapsed)}] {'.' * dots}{' ' * (3-dots)}", end="", flush=True)

        time.sleep(check_interval)


def verify_storage_files(transcription_id: str) -> dict:
    """Verify all storage files exist for the transcription."""
    storage_files = {
        "txt.gz": False,
        "segments.json.gz": False,
        "original.json.gz": False,
        "formatted.txt.gz": False,
    }

    file_base = f"/app/data/transcribes/{transcription_id}"

    for suffix in storage_files.keys():
        file_path = f"{file_base}.{suffix}"
        try:
            result = subprocess.run(
                ["docker", "exec", "whisper_backend", "test", "-f", file_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            storage_files[suffix] = result.returncode == 0
        except Exception as e:
            print(f"Warning: Could not check {file_path}: {e}")
            storage_files[suffix] = False

    return storage_files


def test_file(file_name: str, description: str, expect_chunking: bool, expected_chunks: int):
    """Test a single audio file."""
    print(f"\n\n{'#'*60}")
    print(f"# Testing: {description} ({file_name})")
    print(f"# Expected chunking: {expect_chunking}")
    print(f"# Expected chunks: {expected_chunks}")
    print(f"{'#'*60}")

    overall_start = time.time()

    # Upload
    transcription_id = upload_audio(file_name)
    if not transcription_id:
        print(f"\n✗ Test FAILED: Could not upload file")
        return {
            "file": file_name,
            "description": description,
            "success": False,
            "error": "upload_failed"
        }

    # Wait for completion
    success, result = wait_for_completion(transcription_id)

    overall_time = time.time() - overall_start
    result["overall_time"] = overall_time

    print(f"\nOverall time: {format_duration(overall_time)}")

    # Verify storage files (via docker exec)
    print("\nVerifying storage files...")
    storage_files = {}
    file_base = f"/app/data/transcribes/{transcription_id}"

    import subprocess
    for suffix in ["txt.gz", "segments.json.gz", "original.json.gz", "formatted.txt.gz"]:
        file_path = f"{file_base}.{suffix}"
        try:
            check_result = subprocess.run(
                ["docker", "exec", "whisper_backend", "test", "-f", file_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            storage_files[suffix] = check_result.returncode == 0
            status = "✓" if storage_files[suffix] else "✗"
            print(f"  {status} {transcription_id}.{suffix}")
        except Exception as e:
            storage_files[suffix] = False
            print(f"  ✗ {transcription_id}.{suffix} (check failed)")

    result["storage_files"] = storage_files

    if success:
        print(f"✓ Test PASSED")
    else:
        print(f"✗ Test FAILED")

    result["success"] = success
    return result


def main():
    """Run all tests sequentially."""
    print("=" * 60)
    print("Audio Upload API Test - Production Mode")
    print("=" * 60)
    print(f"BASE_URL: {BASE_URL}")
    print(f"Tests will run SEQUENTIALLY (not in parallel)")
    print("=" * 60)

    results = []

    for file_name, description, expect_chunking, expected_chunks in TEST_FILES:
        result = test_file(file_name, description, expect_chunking, expected_chunks)
        results.append(result)

        # Add delay between tests
        if file_name != TEST_FILES[-1][0]:
            print("\n" + "="*60)
            print("Waiting 10 seconds before next test...")
            print("="*60)
            time.sleep(10)

    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for r in results:
        desc = r.get("description", "unknown")
        success = r.get("success", False)
        status = "✓ PASSED" if success else "✗ FAILED"
        time_str = format_duration(r.get("overall_time", 0))

        print(f"\n{desc:20s}: {status}")
        print(f"  Time: {time_str}")

        if success:
            duration = r.get("duration_seconds")
            if duration:
                print(f"  Audio: {format_duration(duration)}")
            print(f"  Text: {r.get('text_length', 0)} chars")
            print(f"  Language: {r.get('language', 'unknown')}")

            # Storage files
            storage = r.get("storage_files", {})
            files_present = sum(1 for v in storage.values() if v)
            print(f"  Storage: {files_present}/4 files")

    # Overall result
    all_passed = all(r.get("success", False) for r in results)
    passed_count = sum(1 for r in results if r.get("success", False))

    print(f"\n{'='*60}")
    print(f"Result: {passed_count}/{len(results)} tests passed")
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print(f"{'='*60}")

    # Save results to JSON
    results_file = TESTDATA_DIR / "test_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
