#!/usr/bin/env python3
"""
Remote Server Test Upload Script

Directly uploads test audio files to remote production server by:
1. Copying file to remote server via SCP
2. Inserting database record via SSH
3. File will be picked up by local runner

Usage: python scripts/test_remote_upload.py <test_file>
"""

import sys
import os
import subprocess
from pathlib import Path
import uuid

# Remote server configuration
REMOTE_HOST = "root@192.3.249.169"
REMOTE_DIR = "/root/whisper_summarizer"
REMOTE_UPLOAD_DIR = "/app/data/uploads"

# Database configuration
DB_CONTAINER = "whisper_postgres_prd"
DB_NAME = "whisper_summarizer"
DB_USER = "postgres"


def upload_test_file(local_file: str):
    """Upload a test file to remote server and create database record."""
    local_path = Path(local_file)

    if not local_path.exists():
        print(f"Error: File not found: {local_file}")
        return None

    file_name = local_path.name
    file_size = local_path.stat().st_size
    file_ext = local_path.suffix

    print(f"{'='*60}")
    print(f"Test File Upload: {file_name}")
    print(f"{'='*60}")
    print(f"Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")

    # Generate unique transcription ID
    transcription_id = str(uuid.uuid4())
    remote_filename = f"{transcription_id}{file_ext}"
    remote_file_path = f"{REMOTE_UPLOAD_DIR}/{remote_filename}"

    print(f"Transcription ID: {transcription_id}")
    print(f"\nStep 1: Copying file to remote server...")

    # Copy file to remote server
    scp_cmd = [
        "scp",
        str(local_path),
        f"{REMOTE_HOST}:{REMOTE_DIR}/data/uploads/{remote_filename}"
    ]

    result = subprocess.run(scp_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error copying file: {result.stderr}")
        return None

    print(f"✓ File copied to: {remote_file_path}")

    print(f"\nStep 2: Creating database record...")

    # Create database record via SSH
    # Include all required fields with default values
    sql = f"""
    INSERT INTO transcriptions
    (id, file_name, file_path, status, stage, user_id, retry_count, pptx_status)
    VALUES ('{transcription_id}', '{file_name}', '{remote_file_path}',
            'pending', 'uploading', NULL, 0, 'not-started');
    """

    psql_cmd = f'''
    ssh {REMOTE_HOST} "cd {REMOTE_DIR} && docker exec {DB_CONTAINER} psql -U {DB_USER} -d {DB_NAME} -c \\"{sql}\\""
    '''

    result = subprocess.run(psql_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error creating database record: {result.stderr}")
        # Try to clean up the copied file
        subprocess.run(f"ssh {REMOTE_HOST} 'rm {REMOTE_DIR}/data/uploads/{remote_filename}'", shell=True)
        return None

    print(f"✓ Database record created")

    print(f"\n{'='*60}")
    print(f"Upload Complete!")
    print(f"{'='*60}")
    print(f"Transcription ID: {transcription_id}")
    print(f"File: {file_name}")
    print(f"Remote path: {remote_file_path}")
    print(f"Status: pending")
    print(f"\nLocal runner will pick up this job automatically.")
    print(f"Monitor with: docker logs -f whisper_runner")

    return transcription_id


def check_transcription_status(transcription_id: str):
    """Check the status of a transcription on remote server."""
    sql = f"""
    SELECT id, status, stage, runner_id, started_at, completed_at,
           processing_time_seconds, error_message
    FROM transcriptions
    WHERE id = '{transcription_id}';
    """

    psql_cmd = f'''
    ssh {REMOTE_HOST} "cd {REMOTE_DIR} && docker exec {DB_CONTAINER} psql -U {DB_USER} -d {DB_NAME} -c \\"{sql}\\""
    '''

    result = subprocess.run(psql_cmd, shell=True, capture_output=True, text=True)
    print("\nCurrent Status:")
    print(result.stdout)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_remote_upload.py <test_file>")
        print("\nTest files:")
        print("  testdata/2_min.m4a")
        print("  testdata/20_min.m4a")
        print("  testdata/60_min.m4a")
        print("  testdata/210_min.m4a")
        sys.exit(1)

    test_file = sys.argv[1]
    transcription_id = upload_test_file(test_file)

    if transcription_id:
        print(f"\nTo check status later:")
        print(f"  python scripts/test_remote_upload.py --status {transcription_id}")
        return 0
    else:
        print("\nUpload failed!")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        if len(sys.argv) > 2:
            check_transcription_status(sys.argv[2])
        else:
            print("Usage: python scripts/test_remote_upload.py --status <transcription_id>")
    else:
        sys.exit(main())
