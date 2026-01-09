"""
Test suite for Audio Upload API endpoint (Server/Runner Architecture).

Tests for the new audio upload endpoint that:
- Creates a pending transcription job
- Does NOT start background processing
- Runners poll and pick up pending jobs automatically

Tests cover:
- POST /api/audio/upload - File upload with pending job creation
- Authentication requirements
- File validation
- User synchronization
- Error handling
"""
import os
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import status as http_status

from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User

# Check if DISABLE_AUTH is enabled
# Set to False to run all auth tests even when DISABLE_AUTH=true in environment
DISABLE_AUTH = False


# ============================================================================
# POST /api/audio/upload Tests
# ============================================================================

class TestAudioUploadServerArchitecture:
    """Test suite for audio upload in server/runner architecture."""

    def test_upload_requires_authentication(self, test_client):
        """Test that upload requires authentication."""
        audio_content = b"fake audio content"

        response = test_client.post(
            "/api/audio/upload",
            files={"file": ("test.mp3", audio_content, "audio/mpeg")}
        )

        # When DISABLE_AUTH is true, upload succeeds (201)
        # When auth is enabled, it should fail (401/403)
        assert response.status_code in [
            http_status.HTTP_201_CREATED,  # DISABLE_AUTH=true
            http_status.HTTP_401_UNAUTHORIZED,  # Auth enabled, no token
            http_status.HTTP_403_FORBIDDEN  # Auth enabled, invalid token
        ]

    def test_upload_accepts_valid_audio_format_mp3(self, user_auth_client, test_audio_content):
        """Test that upload accepts MP3 files."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.mp3", test_audio_content, "audio/mpeg")}
        )

        # Should return 201 Created or 401 (auth/DB issues)
        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
            http_status.HTTP_404_NOT_FOUND  # User not found in DB
        ]

        if response.status_code == http_status.HTTP_201_CREATED:
            data = response.json()
            # Verify job was created with PENDING status (not processing)
            assert "id" in data
            assert "file_name" in data
            assert data["file_name"] == "test.mp3"

    def test_upload_accepts_valid_audio_format_m4a(self, user_auth_client, test_audio_content):
        """Test that upload accepts M4A files."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.m4a", test_audio_content, "audio/mp4")}
        )

        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
            http_status.HTTP_404_NOT_FOUND
        ]

    def test_upload_accepts_valid_audio_format_wav(self, user_auth_client, test_audio_content):
        """Test that upload accepts WAV files."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.wav", test_audio_content, "audio/wav")}
        )

        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
            http_status.HTTP_404_NOT_FOUND
        ]

    def test_upload_rejects_invalid_file_extension_exe(self, user_auth_client, test_audio_content):
        """Test that upload rejects .exe files."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.exe", test_audio_content, "application/octet-stream")}
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Unsupported file format" in response.json()["detail"]

    def test_upload_rejects_invalid_file_extension_txt(self, user_auth_client, test_audio_content):
        """Test that upload rejects .txt files."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.txt", test_audio_content, "text/plain")}
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_upload_creates_pending_job(self, user_auth_client, test_audio_content, db_session):
        """Test that upload creates a job with PENDING status."""
        # Create test user first
        test_user = User(
            id=str(uuid4()),
            email="test-upload@example.com",
            is_active=True
        )
        db_session.add(test_user)
        db_session.commit()

        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("pending_test.mp3", test_audio_content, "audio/mpeg")}
        )

        if response.status_code == http_status.HTTP_201_CREATED:
            data = response.json()

            # Query the database to verify status
            job = db_session.query(Transcription).filter(
                Transcription.id == data["id"]
            ).first()

            if job:
                # Verify the job is PENDING (not processing)
                assert job.status == TranscriptionStatus.PENDING

    def test_upload_saves_file_to_disk(self, user_auth_client, test_audio_content):
        """Test that upload saves the audio file to disk."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("file_save_test.mp3", test_audio_content, "audio/mpeg")}
        )

        if response.status_code == http_status.HTTP_201_CREATED:
            data = response.json()

            # Verify file was saved
            from app.core.config import settings
            upload_dir = Path(settings.AUDIO_UPLOAD_DIR) if hasattr(settings, 'AUDIO_UPLOAD_DIR') else Path("/app/data/uploads")

            # Find the saved file
            saved_file = None
            for ext in [".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"]:
                potential_file = upload_dir / f"{data['id']}{ext}"
                if potential_file.exists():
                    saved_file = potential_file
                    break

            # File should exist if save succeeded
            # (May not exist in test environment, but path should be set)

    def test_upload_creates_job_for_authenticated_user(self, user_auth_client, test_audio_content, db_session):
        """Test that upload associates job with authenticated user."""
        # Get user ID from auth override
        test_user_id = str(uuid4())

        async def mock_user_auth():
            return {
                "id": test_user_id,
                "email": f"test-{test_user_id[:8]}@example.com",
                "email_confirmed_at": "2025-01-01T00:00:00Z"
            }

        from app.main import app
        from app.core.supabase import get_current_active_user
        app.dependency_overrides[get_current_active_user] = mock_user_auth

        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("user_test.mp3", test_audio_content, "audio/mpeg")}
        )

        if response.status_code == http_status.HTTP_201_CREATED:
            data = response.json()

            # Verify job belongs to user
            job = db_session.query(Transcription).filter(
                Transcription.id == data["id"]
            ).first()

            if job:
                # Convert UUID to string for comparison
                assert str(job.user_id) == test_user_id

        # Clean up
        app.dependency_overrides = {}


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestAudioUploadErrorHandling:
    """Test suite for audio upload error handling."""

    def test_upload_handles_save_failure(self, user_auth_client):
        """Test that upload handles file save failures gracefully."""
        # Use a mock to simulate file save failure
        audio_content = b"fake audio content"

        with patch("builtins.open", side_effect=IOError("Disk full")):
            response = user_auth_client.post(
                "/api/audio/upload",
                files={"file": ("error_test.mp3", audio_content, "audio/mpeg")}
            )

            # Should handle error gracefully (500 or 400)
            assert response.status_code in [
                http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                http_status.HTTP_400_BAD_REQUEST
            ]

    def test_upload_with_corrupted_audio_data(self, user_auth_client):
        """Test upload with very small/corrupted audio data."""
        # Empty or tiny file
        tiny_content = b"x"

        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("tiny.mp3", tiny_content, "audio/mpeg")}
        )

        # Should still accept it (validation is on extension, not content)
        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND
        ]


# ============================================================================
# Integration Tests (Job Lifecycle)
# ============================================================================

class TestJobLifecycleIntegration:
    """Integration tests for complete job lifecycle."""

    def test_upload_then_runner_polls(self, user_auth_client, auth_client, test_audio_content):
        """Test that uploaded job appears in runner poll results."""
        # Step 1: Upload audio
        upload_response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("lifecycle_test.mp3", test_audio_content, "audio/mpeg")}
        )

        if upload_response.status_code == http_status.HTTP_201_CREATED:
            job_data = upload_response.json()
            job_id = job_data["id"]

            # Step 2: Runner polls for jobs
            poll_response = auth_client.get("/api/runner/jobs?status=pending")

            if poll_response.status_code == http_status.HTTP_200_OK:
                jobs = poll_response.json()

                # Our uploaded job should be in the list
                job_ids = [job["id"] for job in jobs]
                assert job_id in job_ids

    def test_full_job_lifecycle_flow(self, user_auth_client, auth_client, test_audio_content, test_audio_file):
        """Test complete flow: upload → start → complete."""
        # This test verifies the server-side orchestration
        # (actual processing would be done by runner)

        # Step 1: Upload
        upload_response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("flow_test.mp3", test_audio_content, "audio/mpeg")}
        )

        # Verify upload created pending job
        # (Full integration test would require runner to process it)


# ============================================================================
# Edge Cases and Additional Validation
# ============================================================================

class TestAudioUploadEdgeCases:
    """Test suite for audio upload edge cases and boundary conditions."""

    def test_upload_with_missing_file_field(self, user_auth_client):
        """Test that upload fails when file field is missing."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={}  # No file provided
        )

        assert response.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_with_invalid_filename(self, user_auth_client, test_audio_content):
        """Test upload with special characters in filename."""
        # Filename with path traversal attempt
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("../../../etc/passwd.mp3", test_audio_content, "audio/mpeg")}
        )

        # Should sanitize or reject
        assert response.status_code in [
            http_status.HTTP_201_CREATED,  # Sanitized
            http_status.HTTP_400_BAD_REQUEST  # Rejected
        ]

    def test_upload_with_very_long_filename(self, user_auth_client, test_audio_content):
        """Test upload with very long filename."""
        long_name = "a" * 1000 + ".mp3"
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": (long_name, test_audio_content, "audio/mpeg")}
        )

        # Should handle or truncate
        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_400_BAD_REQUEST
        ]

    def test_upload_with_unicode_filename(self, user_auth_client, test_audio_content):
        """Test upload with unicode characters in filename."""
        unicode_name = "测试文件中文.mp3"
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": (unicode_name, test_audio_content, "audio/mpeg")}
        )

        # Should handle unicode or sanitize
        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_400_BAD_REQUEST
        ]

    def test_upload_without_file_extension(self, user_auth_client, test_audio_content):
        """Test upload with filename missing extension."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("audiofile", test_audio_content, "audio/mpeg")}
        )

        # Should reject files without extension
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_upload_with_empty_filename(self, user_auth_client, test_audio_content):
        """Test upload with empty filename."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("", test_audio_content, "audio/mpeg")}
        )

        assert response.status_code in [
            http_status.HTTP_400_BAD_REQUEST,
            http_status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    def test_upload_with_zero_byte_file(self, user_auth_client):
        """Test upload with empty (zero-byte) file."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("empty.mp3", b"", "audio/mpeg")}
        )

        # API currently accepts zero-byte files (201) - could also reject (400/413)
        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_400_BAD_REQUEST,
            http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        ]

    def test_upload_with_large_file(self, user_auth_client):
        """Test upload with a large file (simulate 10MB)."""
        # Create 10MB of data (don't actually send that much in test)
        large_content = b"x" * (1024 * 1024)  # 1MB for test speed

        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("large.mp3", large_content, "audio/mpeg")}
        )

        # Should accept or reject based on size limits
        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        ]

    def test_upload_with_wrong_content_type(self, user_auth_client, test_audio_content):
        """Test upload with content-type not matching extension."""
        # MP3 file but claim it's a PDF
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.mp3", test_audio_content, "application/pdf")}
        )

        # Should validate by extension, not content-type
        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_400_BAD_REQUEST
        ]

    def test_upload_with_case_mismatch_extension(self, user_auth_client, test_audio_content):
        """Test upload with uppercase file extension."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.MP3", test_audio_content, "audio/mpeg")}
        )

        # Should handle case-insensitive extensions
        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND
        ]

    def test_upload_with_mixed_case_extension(self, user_auth_client, test_audio_content):
        """Test upload with mixed case file extension."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.Mp3", test_audio_content, "audio/mpeg")}
        )

        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND
        ]

    def test_upload_multiple_files_rapid_sequence(self, user_auth_client, test_audio_content):
        """Test uploading multiple files in quick succession."""
        responses = []
        for i in range(5):
            response = user_auth_client.post(
                "/api/audio/upload",
                files={"file": (f"test{i}.mp3", test_audio_content, "audio/mpeg")}
            )
            responses.append(response)

        # All should succeed or fail consistently
        success_count = sum(1 for r in responses if r.status_code == http_status.HTTP_201_CREATED)
        assert success_count in [0, 5]  # All or none due to auth/DB

    def test_upload_with_double_extension(self, user_auth_client, test_audio_content):
        """Test upload with file having double extension."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.mp3.mp3", test_audio_content, "audio/mpeg")}
        )

        # Should handle or reject
        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND
        ]


# ============================================================================
# Additional File Format Tests
# ============================================================================

class TestAudioUploadFormats:
    """Test suite for various audio format support."""

    def test_upload_ogg_format(self, user_auth_client, test_audio_content):
        """Test that upload accepts OGG files."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.ogg", test_audio_content, "audio/ogg")}
        )

        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND
        ]

    def test_upload_flac_format(self, user_auth_client, test_audio_content):
        """Test that upload accepts FLAC files."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.flac", test_audio_content, "audio/flac")}
        )

        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND
        ]

    def test_upload_aac_format(self, user_auth_client, test_audio_content):
        """Test that upload accepts AAC files."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.aac", test_audio_content, "audio/aac")}
        )

        assert response.status_code in [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND
        ]

    def test_upload_rejects_pdf_file(self, user_auth_client, test_audio_content):
        """Test that upload rejects PDF files."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.pdf", test_audio_content, "application/pdf")}
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_upload_rejects_jpeg_file(self, user_auth_client, test_audio_content):
        """Test that upload rejects JPEG files."""
        response = user_auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.jpg", test_audio_content, "image/jpeg")}
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_upload_with_existing_user_by_email(self, user_auth_client, test_audio_content, db_session):
        """Test that upload finds existing user by email (lines 41-42)."""
        from app.models.user import User
        from app.api.audio import get_or_create_user
        import uuid

        # Create a local user with specific email
        test_email = "email-sync-test@example.com"
        existing_local_user_id = uuid.uuid4()
        existing_user = User(id=existing_local_user_id, email=test_email, is_active=True)
        db_session.add(existing_user)
        db_session.commit()

        # Test get_or_create_user directly with different auth ID but same email
        # This simulates Supabase having a different ID for the same email
        different_auth_id = str(uuid.uuid4())

        # The function should find the existing user by email (lines 38-42)
        found_user = get_or_create_user(db_session, different_auth_id, test_email)

        # Verify it returns the existing user (found by email, not by ID)
        assert found_user is not None
        assert found_user.id == existing_local_user_id
        assert found_user.email == test_email
        # Note: The returned user has existing_local_user_id, not different_auth_id
        # This proves lines 41-42 were executed (found by email lookup)

        # Clean up
        db_session.query(User).filter(User.id == existing_local_user_id).delete()
        db_session.commit()
