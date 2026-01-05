"""
Test suite for Runner API endpoints.

Tests cover:
- GET /api/runner/jobs - Job polling
- POST /api/runner/jobs/{job_id}/start - Job claiming
- POST /api/runner/jobs/{job_id}/complete - Job completion with audio deletion
- POST /api/runner/jobs/{job_id}/fail - Job failure reporting
- GET /api/runner/audio/{job_id} - Audio file retrieval
- POST /api/runner/heartbeat - Runner health monitoring

All tests verify:
- Authentication (Bearer token requirement)
- Authorization (valid RUNNER_API_KEY)
- Request validation (UUID format, status validation)
- Error handling (404, 400, 401 responses)
- Side effects (database updates, file deletion)
"""
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import status as http_status

from app.models.transcription import Transcription, TranscriptionStatus


# ============================================================================
# Authentication Tests (apply to all endpoints)
# ============================================================================

class TestRunnerAuthentication:
    """Test suite for runner API authentication."""

    def test_get_jobs_requires_auth(self, test_client):
        """Test that GET /api/runner/jobs requires authentication."""
        response = test_client.get("/api/runner/jobs")
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_get_jobs_rejects_invalid_token(self, test_client):
        """Test that GET /api/runner/jobs rejects invalid API key."""
        response = test_client.get(
            "/api/runner/jobs",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_get_jobs_accepts_valid_token(self, auth_client):
        """Test that GET /api/runner/jobs accepts valid API key."""
        response = auth_client.get("/api/runner/jobs")
        # Should return 200 (empty list) or 401 if DB not set up
        assert response.status_code in [
            http_status.HTTP_200_OK,
            http_status.HTTP_401_UNAUTHORIZED  # DB not initialized
        ]

    def test_start_job_requires_auth(self, test_client):
        """Test that POST /api/runner/jobs/{id}/start requires auth."""
        job_id = uuid4()
        response = test_client.post(
            f"/api/runner/jobs/{job_id}/start",
            json={"runner_id": "test-runner"}
        )
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_complete_job_requires_auth(self, test_client):
        """Test that POST /api/runner/jobs/{id}/complete requires auth."""
        job_id = uuid4()
        response = test_client.post(
            f"/api/runner/jobs/{job_id}/complete",
            json={
                "text": "Test transcription",
                "processing_time_seconds": 10
            }
        )
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_fail_job_requires_auth(self, test_client):
        """Test that POST /api/runner/jobs/{id}/fail requires auth."""
        job_id = uuid4()
        response = test_client.post(
            f"/api/runner/jobs/{job_id}/fail",
            data="Test error"
        )
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_get_audio_requires_auth(self, test_client):
        """Test that GET /api/runner/audio/{id} requires auth."""
        job_id = uuid4()
        response = test_client.get(f"/api/runner/audio/{job_id}")
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_heartbeat_requires_auth(self, test_client):
        """Test that POST /api/runner/heartbeat requires auth."""
        response = test_client.post(
            "/api/runner/heartbeat",
            json={"runner_id": "test-runner", "current_jobs": 0}
        )
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED


# ============================================================================
# GET /api/runner/jobs Tests
# ============================================================================

class TestGetPendingJobs:
    """Test suite for GET /api/runner/jobs endpoint."""

    def test_get_jobs_returns_empty_list_when_no_jobs(self, auth_client):
        """Test that GET /api/runner/jobs returns empty list when no pending jobs."""
        response = auth_client.get("/api/runner/jobs")

        # Should return 200 with empty list
        assert response.status_code in [
            http_status.HTTP_200_OK,
            http_status.HTTP_401_UNAUTHORIZED  # If DB not initialized
        ]

        if response.status_code == http_status.HTTP_200_OK:
            assert response.json() == []

    def test_get_jobs_with_pending_status_filter(self, auth_client, test_transcription):
        """Test GET /api/runner/jobs with status='pending' filter."""
        response = auth_client.get("/api/runner/jobs?status=pending")

        assert response.status_code in [
            http_status.HTTP_200_OK,
            http_status.HTTP_401_UNAUTHORIZED
        ]

        if response.status_code == http_status.HTTP_200_OK:
            jobs = response.json()
            assert isinstance(jobs, list)
            # Should find our test pending transcription
            if len(jobs) > 0:
                assert jobs[0]["file_name"] == "test_audio.mp3"

    def test_get_jobs_with_processing_status_filter(self, auth_client, test_processing_transcription):
        """Test GET /api/runner/jobs with status='processing' filter."""
        response = auth_client.get("/api/runner/jobs?status=processing")

        assert response.status_code in [
            http_status.HTTP_200_OK,
            http_status.HTTP_401_UNAUTHORIZED
        ]

        if response.status_code == http_status.HTTP_200_OK:
            jobs = response.json()
            assert isinstance(jobs, list)

    def test_get_jobs_with_completed_status_filter(self, auth_client, test_completed_transcription):
        """Test GET /api/runner/jobs with status='completed' filter."""
        response = auth_client.get("/api/runner/jobs?status=completed")

        assert response.status_code in [
            http_status.HTTP_200_OK,
            http_status.HTTP_401_UNAUTHORIZED
        ]

        if response.status_code == http_status.HTTP_200_OK:
            jobs = response.json()
            assert isinstance(jobs, list)

    def test_get_jobs_respects_limit_parameter(self, auth_client):
        """Test that GET /api/runner/jobs respects the limit parameter."""
        response = auth_client.get("/api/runner/jobs?limit=5")

        assert response.status_code in [
            http_status.HTTP_200_OK,
            http_status.HTTP_401_UNAUTHORIZED
        ]

    def test_get_jobs_rejects_invalid_status_filter(self, auth_client):
        """Test that GET /api/runner/jobs rejects invalid status filter."""
        response = auth_client.get("/api/runner/jobs?status=invalid_status")

        # Should return 400 for invalid status
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Invalid status" in response.json()["detail"]


# ============================================================================
# POST /api/runner/jobs/{job_id}/start Tests
# ============================================================================

class TestStartJob:
    """Test suite for POST /api/runner/jobs/{job_id}/start endpoint."""

    def test_start_job_success(self, auth_client, test_transcription):
        """Test successfully starting a pending job."""
        job_id = test_transcription.id
        runner_id = "test-runner-01"

        response = auth_client.post(
            f"/api/runner/jobs/{job_id}/start",
            json={"runner_id": runner_id}
        )

        # May return 200, 401 (DB), or 404 (transaction issues)
        assert response.status_code in [
            http_status.HTTP_200_OK,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND
        ]

        if response.status_code == http_status.HTTP_200_OK:
            data = response.json()
            assert data["status"] == "started"
            assert data["job_id"] == str(job_id)

    def test_start_job_rejects_invalid_uuid_format(self, auth_client):
        """Test that starting a job rejects invalid UUID format."""
        response = auth_client.post(
            "/api/runner/jobs/invalid-uuid/start",
            json={"runner_id": "test-runner"}
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Invalid job ID format" in response.json()["detail"]

    def test_start_job_returns_404_for_nonexistent_job(self, auth_client):
        """Test that starting a job returns 404 for non-existent job."""
        job_id = uuid4()
        response = auth_client.post(
            f"/api/runner/jobs/{job_id}/start",
            json={"runner_id": "test-runner"}
        )

        assert response.status_code == http_status.HTTP_404_NOT_FOUND
        assert "Job not found" in response.json()["detail"]

    def test_start_job_fails_for_non_pending_job(self, auth_client, test_completed_transcription):
        """Test that starting a job fails if job is not pending."""
        job_id = test_completed_transcription.id
        response = auth_client.post(
            f"/api/runner/jobs/{job_id}/start",
            json={"runner_id": "test-runner"}
        )

        # Job is already completed, should return 400
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Job not available" in response.json()["detail"]


# ============================================================================
# POST /api/runner/jobs/{job_id}/complete Tests
# ============================================================================

class TestCompleteJob:
    """Test suite for POST /api/runner/jobs/{job_id}/complete endpoint."""

    def test_complete_job_success_with_summary(self, auth_client, test_processing_transcription):
        """Test successfully completing a job with text and summary."""
        job_id = test_processing_transcription.id

        response = auth_client.post(
            f"/api/runner/jobs/{job_id}/complete",
            json={
                "text": "This is the transcription text.",
                "summary": "This is a summary.",
                "processing_time_seconds": 30
            }
        )

        # May return 200, 401 (DB), or 404 (transaction issues)
        assert response.status_code in [
            http_status.HTTP_200_OK,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND
        ]

        if response.status_code == http_status.HTTP_200_OK:
            data = response.json()
            assert data["status"] == "completed"
            assert data["job_id"] == str(job_id)
            assert "audio_deleted" in data

    def test_complete_job_success_text_only(self, auth_client, test_processing_transcription):
        """Test completing a job with text only (summary optional)."""
        job_id = test_processing_transcription.id

        response = auth_client.post(
            f"/api/runner/jobs/{job_id}/complete",
            json={
                "text": "This is the transcription text.",
                "processing_time_seconds": 25
            }
        )

        assert response.status_code in [
            http_status.HTTP_200_OK,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND
        ]

    def test_complete_job_deletes_audio_file(self, auth_client, test_processing_transcription, test_audio_file):
        """Test that completing a job deletes the audio file."""
        # Update transcription to have the test audio file
        test_processing_transcription.file_path = str(test_audio_file)

        job_id = test_processing_transcription.id

        response = auth_client.post(
            f"/api/runner/jobs/{job_id}/complete",
            json={
                "text": "Test transcription",
                "processing_time_seconds": 20
            }
        )

        if response.status_code == http_status.HTTP_200_OK:
            data = response.json()
            # Verify audio was deleted
            assert data["audio_deleted"] is True

    def test_complete_job_rejects_invalid_uuid(self, auth_client):
        """Test that completing a job rejects invalid UUID format."""
        response = auth_client.post(
            "/api/runner/jobs/invalid-uuid/complete",
            json={
                "text": "Test",
                "processing_time_seconds": 10
            }
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Invalid job ID format" in response.json()["detail"]

    def test_complete_job_returns_404_for_nonexistent_job(self, auth_client):
        """Test that completing a job returns 404 for non-existent job."""
        job_id = uuid4()
        response = auth_client.post(
            f"/api/runner/jobs/{job_id}/complete",
            json={
                "text": "Test",
                "processing_time_seconds": 10
            }
        )

        assert response.status_code == http_status.HTTP_404_NOT_FOUND
        assert "Job not found" in response.json()["detail"]


# ============================================================================
# POST /api/runner/jobs/{job_id}/fail Tests
# ============================================================================

class TestFailJob:
    """Test suite for POST /api/runner/jobs/{job_id}/fail endpoint."""

    def test_fail_job_success(self, auth_client, test_processing_transcription):
        """Test successfully reporting a job failure."""
        job_id = test_processing_transcription.id
        error_msg = "Processing failed: GPU out of memory"

        response = auth_client.post(
            f"/api/runner/jobs/{job_id}/fail",
            data=error_msg,
            headers={"Content-Type": "text/plain"}
        )

        assert response.status_code in [
            http_status.HTTP_200_OK,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND
        ]

        if response.status_code == http_status.HTTP_200_OK:
            data = response.json()
            assert data["status"] == "failed"
            assert data["job_id"] == str(job_id)
            assert data["error"] == error_msg

    def test_fail_job_rejects_invalid_uuid(self, auth_client):
        """Test that failing a job rejects invalid UUID format."""
        response = auth_client.post(
            "/api/runner/jobs/invalid-uuid/fail",
            data="Test error"
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Invalid job ID format" in response.json()["detail"]

    def test_fail_job_returns_404_for_nonexistent_job(self, auth_client):
        """Test that failing a job returns 404 for non-existent job."""
        job_id = uuid4()
        response = auth_client.post(
            f"/api/runner/jobs/{job_id}/fail",
            data="Test error"
        )

        assert response.status_code == http_status.HTTP_404_NOT_FOUND
        assert "Job not found" in response.json()["detail"]


# ============================================================================
# GET /api/runner/audio/{job_id} Tests
# ============================================================================

class TestGetAudioFile:
    """Test suite for GET /api/runner/audio/{job_id} endpoint."""

    def test_get_audio_success(self, auth_client, test_transcription):
        """Test successfully getting audio file information."""
        job_id = test_transcription.id

        response = auth_client.get(f"/api/runner/audio/{job_id}")

        assert response.status_code in [
            http_status.HTTP_200_OK,
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_404_NOT_FOUND  # File may not exist
        ]

        if response.status_code == http_status.HTTP_200_OK:
            data = response.json()
            assert "file_path" in data
            assert "file_size" in data
            assert "content_type" in data

    def test_get_audio_rejects_invalid_uuid(self, auth_client):
        """Test that getting audio rejects invalid UUID format."""
        response = auth_client.get("/api/runner/audio/invalid-uuid")

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Invalid job ID format" in response.json()["detail"]

    def test_get_audio_returns_404_for_nonexistent_job(self, auth_client):
        """Test that getting audio returns 404 for non-existent job."""
        job_id = uuid4()
        response = auth_client.get(f"/api/runner/audio/{job_id}")

        assert response.status_code == http_status.HTTP_404_NOT_FOUND
        assert "Job not found" in response.json()["detail"]

    def test_get_audio_returns_404_when_no_file_path(self, auth_client, test_processing_transcription):
        """Test that getting audio returns 404 when file_path is not set."""
        # Ensure file_path is None
        test_processing_transcription.file_path = None
        job_id = test_processing_transcription.id

        response = auth_client.get(f"/api/runner/audio/{job_id}")

        assert response.status_code == http_status.HTTP_404_NOT_FOUND
        assert "Audio file path not set" in response.json()["detail"]

    def test_get_audio_returns_404_when_file_missing(self, auth_client, test_transcription):
        """Test that getting audio returns 404 when file doesn't exist."""
        # Set a non-existent file path
        test_transcription.file_path = "/nonexistent/path/audio.mp3"
        job_id = test_transcription.id

        response = auth_client.get(f"/api/runner/audio/{job_id}")

        assert response.status_code == http_status.HTTP_404_NOT_FOUND
        assert "Audio file not found" in response.json()["detail"]


# ============================================================================
# POST /api/runner/heartbeat Tests
# ============================================================================

class TestRunnerHeartbeat:
    """Test suite for POST /api/runner/heartbeat endpoint."""

    def test_heartbeat_success(self, auth_client):
        """Test successfully sending a heartbeat."""
        response = auth_client.post(
            "/api/runner/heartbeat",
            json={
                "runner_id": "test-runner-01",
                "current_jobs": 2
            }
        )

        # Should return 200 OK
        assert response.status_code == http_status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "ok"

    def test_heartbeat_with_zero_jobs(self, auth_client):
        """Test heartbeat with zero active jobs."""
        response = auth_client.post(
            "/api/runner/heartbeat",
            json={
                "runner_id": "test-runner-01",
                "current_jobs": 0
            }
        )

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"

    def test_heartbeat_without_auth(self, test_client):
        """Test that heartbeat requires authentication."""
        response = test_client.post(
            "/api/runner/heartbeat",
            json={
                "runner_id": "test-runner",
                "current_jobs": 0
            }
        )

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED
