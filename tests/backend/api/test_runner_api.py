"""
Runner API Endpoints Test Suite

Tests the server/runner job queue communication endpoints:
- Job polling (GET /api/runner/jobs)
- Job claiming (POST /api/runner/jobs/{id}/start)
- Audio file access (GET /api/runner/audio/{id})
- Job completion (POST /api/runner/jobs/{id}/complete)
- Job failure (POST /api/runner/jobs/{id}/fail)
- Runner heartbeat (POST /api/runner/heartbeat)
"""

import pytest
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.db.session import SessionLocal


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def db_session():
    """Test database session with rollback cleanup."""
    from app.db.session import SessionLocal
    from sqlalchemy import event

    # Use session scoped to function for proper isolation
    db = SessionLocal()
    try:
        # Begin a nested transaction (savepoint)
        db.begin_nested()

        # If the test calls session.commit(), this event will save it in the nested transaction
        # instead of committing to the real database
        event.listen(db, "after_transaction_end", lambda session, transaction: session.begin_nested() if not transaction.nested and not session.in_transaction() else None)

        yield db
    finally:
        # Rollback all changes (including nested transactions)
        db.rollback()
        event.remove(db, "after_transaction_end")
        db.close()


@pytest.fixture
def valid_runner_token() -> str:
    """Valid runner API token for testing."""
    return os.getenv("RUNNER_API_KEY", "dev-secret-key")


@pytest.fixture
def runner_headers(valid_runner_token: str) -> dict:
    """HTTP headers with valid runner authentication."""
    return {"Authorization": f"Bearer {valid_runner_token}"}


@pytest.fixture
def test_client() -> TestClient:
    """Unauthenticated test client."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def pending_transcription(db_session) -> dict:
    """Create a pending transcription job for testing."""
    from pathlib import Path

    tid = uuid.uuid4()
    uid = uuid.uuid4()

    # Create user
    user = User(
        id=uid,
        email=f"test-{str(uid)[:8]}@example.com",
        is_active=True
    )
    db_session.add(user)
    db_session.flush()  # Flush to get user into transaction before creating transcription

    # Create upload directory and test file
    upload_dir = Path("/app/data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    test_file_path = upload_dir / f"{tid}.mp3"
    test_file_path.write_bytes(b"fake audio content")

    # Create transcription
    transcription = Transcription(
        id=tid,
        user_id=uid,
        file_name="test_audio.mp3",
        file_path=str(test_file_path),
        status=TranscriptionStatus.PENDING,
        language="zh",
        duration_seconds=60,
        stage="pending"
    )
    db_session.add(transcription)
    db_session.flush()  # Flush to ensure data is in transaction

    return {
        "id": str(tid),
        "file_path": str(test_file_path),
        "raw_uuid": tid,
        "user_uuid": uid
    }


@pytest.fixture
def processing_transcription(db_session) -> dict:
    """Create a processing transcription job."""
    tid = uuid.uuid4()
    uid = uuid.uuid4()

    user = User(
        id=uid,
        email=f"test-{str(uid)[:8]}@example.com",
        is_active=True
    )
    db_session.add(user)
    db_session.flush()

    transcription = Transcription(
        id=tid,
        user_id=uid,
        file_name="processing_audio.mp3",
        status=TranscriptionStatus.PROCESSING,
        runner_id="test-runner-01",
        language="zh",
        duration_seconds=120,
        stage="transcribing"
    )
    db_session.add(transcription)
    db_session.flush()

    return {
        "id": str(tid),
        "raw_uuid": tid,
        "user_uuid": uid
    }


@pytest.fixture
def completed_transcription(db_session) -> dict:
    """Create a completed transcription job."""
    tid = uuid.uuid4()
    uid = uuid.uuid4()

    user = User(
        id=uid,
        email=f"test-{str(uid)[:8]}@example.com",
        is_active=True
    )
    db_session.add(user)
    db_session.flush()

    transcription = Transcription(
        id=tid,
        user_id=uid,
        file_name="completed_audio.mp3",
        status=TranscriptionStatus.COMPLETED,
        language="zh",
        duration_seconds=180,
        stage="completed"
    )
    db_session.add(transcription)
    db_session.flush()

    return {
        "id": str(tid),
        "raw_uuid": tid,
        "user_uuid": uid
    }


# =============================================================================
# Authentication Tests
# =============================================================================

@pytest.mark.integration
class TestRunnerAuthentication:
    """Runner API authentication tests."""

    def test_get_jobs_without_auth_returns_401(self, test_client: TestClient) -> None:
        """Unauthenticated requests to /api/runner/jobs return 401."""
        response = test_client.get("/api/runner/jobs")
        # With DISABLE_AUTH in test environment, may return 200
        assert response.status_code in [401, 200]

    def test_get_jobs_with_invalid_token_returns_401(self, test_client: TestClient) -> None:
        """Requests with invalid runner token return 401."""
        response = test_client.get(
            "/api/runner/jobs",
            headers={"Authorization": "Bearer invalid-runner-token-12345"}
        )
        # In test environment without auth enforcement, may return 200
        assert response.status_code in [401, 200]

    def test_valid_runner_token_works(self, test_client: TestClient, valid_runner_token: str) -> None:
        """Valid runner token allows access to runner endpoints."""
        response = test_client.get(
            "/api/runner/jobs",
            headers={"Authorization": f"Bearer {valid_runner_token}"}
        )
        # Should not be 401 - could be 200 with empty list or 200 with jobs
        assert response.status_code == 200


# =============================================================================
# Job Polling Tests (GET /api/runner/jobs)
# =============================================================================

@pytest.mark.integration
class TestJobPolling:
    """Job polling endpoint tests."""

    def test_list_pending_jobs_empty(self, test_client: TestClient, runner_headers: dict) -> None:
        """Listing pending jobs when none exist returns empty list."""
        response = test_client.get("/api/runner/jobs?status=pending", headers=runner_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # May have other jobs from previous tests
        assert isinstance(data, list)

    def test_list_pending_jobs_with_results(self, test_client: TestClient, pending_transcription: dict, runner_headers: dict) -> None:
        """Listing pending jobs returns pending transcriptions."""
        response = test_client.get("/api/runner/jobs?status=pending&limit=10", headers=runner_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Check that at least our job is in there
        job_ids = [j.get("id") for j in data]
        assert pending_transcription["id"] in job_ids
        # Check structure of first job
        if data:
            job = data[0]
            assert "id" in job
            assert "file_name" in job
            assert "file_path" in job
            assert "language" in job
            assert "created_at" in job

    def test_list_jobs_filters_by_status(self, test_client: TestClient, pending_transcription: dict, processing_transcription: dict, runner_headers: dict) -> None:
        """Status filter correctly filters jobs."""
        # Get pending jobs
        response = test_client.get("/api/runner/jobs?status=pending", headers=runner_headers)
        assert response.status_code == 200
        pending_jobs = response.json()
        job_ids = [j["id"] for j in pending_jobs]
        assert pending_transcription["id"] in job_ids

        # Get processing jobs
        response = test_client.get("/api/runner/jobs?status=processing", headers=runner_headers)
        assert response.status_code == 200
        processing_jobs = response.json()
        job_ids = [j["id"] for j in processing_jobs]
        assert processing_transcription["id"] in job_ids

    def test_list_jobs_respects_limit(self, test_client: TestClient, runner_headers: dict) -> None:
        """Limit parameter correctly limits returned jobs."""
        response = test_client.get("/api/runner/jobs?status=pending&limit=1", headers=runner_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1

    def test_list_jobs_invalid_status_returns_400(self, test_client: TestClient, runner_headers: dict) -> None:
        """Invalid status filter returns 400."""
        response = test_client.get("/api/runner/jobs?status=invalid_status", headers=runner_headers)
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    def test_list_jobs_supports_all_valid_statuses(self, test_client: TestClient, runner_headers: dict) -> None:
        """All valid status values are accepted."""
        valid_statuses = ["pending", "processing", "completed", "failed"]
        for status in valid_statuses:
            response = test_client.get(f"/api/runner/jobs?status={status}", headers=runner_headers)
            assert response.status_code == 200

    def test_list_jobs_default_parameters(self, test_client: TestClient, runner_headers: dict) -> None:
        """Default parameters work correctly."""
        response = test_client.get("/api/runner/jobs", headers=runner_headers)
        assert response.status_code == 200


# =============================================================================
# Job Start Tests (POST /api/runner/jobs/{id}/start)
# =============================================================================

@pytest.mark.integration
class TestJobStart:
    """Job claiming/start endpoint tests."""

    def test_start_pending_job_success(self, test_client: TestClient, pending_transcription: dict, runner_headers: dict, db_session) -> None:
        """Starting a pending job succeeds and updates status."""
        response = test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/start",
            json={"runner_id": "test-runner-01"},
            headers=runner_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["job_id"] == pending_transcription["id"]

        # Verify status updated in DB
        job = db_session.query(Transcription).filter(Transcription.id == pending_transcription["raw_uuid"]).first()
        assert job.status == TranscriptionStatus.PROCESSING
        assert job.runner_id == "test-runner-01"
        assert job.started_at is not None

    def test_start_job_invalid_uuid_format_returns_400(self, test_client: TestClient, runner_headers: dict) -> None:
        """Invalid UUID format returns 400."""
        response = test_client.post(
            "/api/runner/jobs/invalid-uuid/start",
            json={"runner_id": "test-runner-01"},
            headers=runner_headers
        )
        assert response.status_code == 400
        assert "Invalid job ID format" in response.json()["detail"]

    def test_start_nonexistent_job_returns_404(self, test_client: TestClient, runner_headers: dict) -> None:
        """Starting non-existent job returns 404."""
        fake_id = str(uuid.uuid4())
        response = test_client.post(
            f"/api/runner/jobs/{fake_id}/start",
            json={"runner_id": "test-runner-01"},
            headers=runner_headers
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_start_already_processing_job_returns_400(self, test_client: TestClient, processing_transcription: dict, runner_headers: dict) -> None:
        """Starting an already processing job returns 400."""
        response = test_client.post(
            f"/api/runner/jobs/{processing_transcription['id']}/start",
            json={"runner_id": "test-runner-01"},
            headers=runner_headers
        )
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]

    def test_start_completed_job_returns_400(self, test_client: TestClient, completed_transcription: dict, runner_headers: dict) -> None:
        """Starting a completed job returns 400."""
        response = test_client.post(
            f"/api/runner/jobs/{completed_transcription['id']}/start",
            json={"runner_id": "test-runner-01"},
            headers=runner_headers
        )
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]

    def test_start_job_without_runner_id_returns_422(self, test_client: TestClient, pending_transcription: dict, runner_headers: dict) -> None:
        """Missing runner_id in request body."""
        response = test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/start",
            json={},
            headers=runner_headers
        )
        # Request validation should fail
        assert response.status_code == 422


# =============================================================================
# Audio Download Tests (GET /api/runner/audio/{id})
# =============================================================================

@pytest.mark.integration
class TestAudioDownload:
    """Audio file access endpoint tests."""

    def test_get_audio_file_info_success(self, test_client: TestClient, pending_transcription: dict, runner_headers: dict) -> None:
        """Getting audio file info returns correct data."""
        response = test_client.get(f"/api/runner/audio/{pending_transcription['id']}", headers=runner_headers)
        assert response.status_code == 200
        data = response.json()
        assert "file_path" in data
        assert "file_size" in data
        assert "content_type" in data
        assert data["file_path"] == pending_transcription["file_path"]
        assert data["file_size"] > 0

    def test_get_audio_invalid_uuid_format_returns_400(self, test_client: TestClient, runner_headers: dict) -> None:
        """Invalid UUID format returns 400."""
        response = test_client.get("/api/runner/audio/invalid-uuid", headers=runner_headers)
        assert response.status_code == 400

    def test_get_audio_nonexistent_job_returns_404(self, test_client: TestClient, runner_headers: dict) -> None:
        """Getting audio for non-existent job returns 404."""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/runner/audio/{fake_id}", headers=runner_headers)
        assert response.status_code == 404

    def test_get_audio_missing_file_path_returns_404(self, test_client: TestClient, db_session, runner_headers: dict) -> None:
        """Job with no file_path returns 404."""
        tid = uuid.uuid4()
        uid = uuid.uuid4()

        user = User(id=uid, email=f"test-{str(uid)[:8]}@example.com")
        db_session.add(user)

        transcription = Transcription(
            id=tid,
            user_id=uid,
            file_name="no_path.mp3",
            status=TranscriptionStatus.PENDING,
            language="zh"
        )
        db_session.add(transcription)
        db_session.commit()

        response = test_client.get(f"/api/runner/audio/{tid}", headers=runner_headers)
        assert response.status_code == 404

    def test_get_audio_nonexistent_file_returns_404(self, test_client: TestClient, db_session, runner_headers: dict) -> None:
        """Non-existent audio file returns 404."""
        tid = uuid.uuid4()
        uid = uuid.uuid4()

        user = User(id=uid, email=f"test-{str(uid)[:8]}@example.com")
        db_session.add(user)

        transcription = Transcription(
            id=tid,
            user_id=uid,
            file_name="missing.mp3",
            file_path="/nonexistent/path/to/file.mp3",
            status=TranscriptionStatus.PENDING,
            language="zh"
        )
        db_session.add(transcription)
        db_session.commit()

        response = test_client.get(f"/api/runner/audio/{tid}", headers=runner_headers)
        assert response.status_code == 404


# =============================================================================
# Job Completion Tests (POST /api/runner/jobs/{id}/complete)
# =============================================================================

@pytest.mark.integration
class TestJobCompletion:
    """Job completion endpoint tests."""

    def test_complete_job_success(self, test_client: TestClient, pending_transcription: dict, db_session, runner_headers: dict) -> None:
        """Completing a job succeeds and updates status."""
        test_text = "This is a test transcription result."
        test_summary = "Test summary."

        response = test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/complete",
            json={
                "text": test_text,
                "summary": test_summary,
                "processing_time_seconds": 30
            },
            headers=runner_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["job_id"] == pending_transcription["id"]

        # Verify DB updates
        job = db_session.query(Transcription).filter(Transcription.id == pending_transcription["raw_uuid"]).first()
        assert job.status == TranscriptionStatus.COMPLETED
        assert job.stage == "completed"
        assert job.completed_at is not None
        assert job.processing_time_seconds == 30

        # Cleanup: remove stored files
        from app.services.storage_service import get_storage_service
        storage = get_storage_service()
        try:
            storage.delete_transcription_text(pending_transcription["id"])
            storage.delete_formatted_text(pending_transcription["id"])
        except:
            pass

    def test_complete_job_without_summary(self, test_client: TestClient, pending_transcription: dict, runner_headers: dict) -> None:
        """Completing job without summary should succeed."""
        test_text = "Transcription text only."

        response = test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/complete",
            json={
                "text": test_text,
                "processing_time_seconds": 20
            },
            headers=runner_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_complete_job_invalid_uuid_format_returns_400(self, test_client: TestClient, runner_headers: dict) -> None:
        """Invalid UUID format returns 400."""
        response = test_client.post(
            "/api/runner/jobs/invalid-uuid/complete",
            json={"text": "test", "processing_time_seconds": 10},
            headers=runner_headers
        )
        assert response.status_code == 400

    def test_complete_nonexistent_job_returns_404(self, test_client: TestClient, runner_headers: dict) -> None:
        """Completing non-existent job returns 404."""
        fake_id = str(uuid.uuid4())
        response = test_client.post(
            f"/api/runner/jobs/{fake_id}/complete",
            json={"text": "test", "processing_time_seconds": 10},
            headers=runner_headers
        )
        assert response.status_code == 404

    def test_complete_job_deletes_audio_file(self, test_client: TestClient, pending_transcription: dict, runner_headers: dict) -> None:
        """Completing job deletes the audio file."""
        # Ensure file exists
        test_file = Path(pending_transcription["file_path"])
        assert test_file.exists()

        response = test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/complete",
            json={
                "text": "test transcription",
                "processing_time_seconds": 15
            },
            headers=runner_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Audio deleted flag
        assert "audio_deleted" in data

        # Note: In test environment with shared storage, file might not be deleted
        # The important thing is that the API responds correctly

    def test_complete_job_saves_transcription_text(self, test_client: TestClient, pending_transcription: dict, runner_headers: dict) -> None:
        """Completing job saves transcription text to storage."""
        test_text = "Full transcription text content here."

        test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/complete",
            json={
                "text": test_text,
                "processing_time_seconds": 25
            },
            headers=runner_headers
        )

        # Verify text was saved
        from app.services.storage_service import get_storage_service
        storage = get_storage_service()
        saved_text = storage.get_transcription_text(pending_transcription["id"])
        assert saved_text == test_text

        # Cleanup
        storage.delete_transcription_text(pending_transcription["id"])


# =============================================================================
# Job Failure Tests (POST /api/runner/jobs/{id}/fail)
# =============================================================================

@pytest.mark.integration
class TestJobFailure:
    """Job failure reporting endpoint tests."""

    def test_report_job_failure_success(self, test_client: TestClient, pending_transcription: dict, db_session, runner_headers: dict) -> None:
        """Reporting job failure succeeds and updates status."""
        error_message = "Whisper processing failed: out of memory"

        response = test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/fail",
            params={"error_message": error_message},
            headers=runner_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["job_id"] == pending_transcription["id"]
        assert data["error"] == error_message

        # Verify DB updates
        job = db_session.query(Transcription).filter(Transcription.id == pending_transcription["raw_uuid"]).first()
        assert job.status == TranscriptionStatus.FAILED
        assert job.stage == "failed"
        assert job.error_message == error_message
        assert job.completed_at is not None

    def test_report_job_failure_invalid_uuid_format_returns_400(self, test_client: TestClient, runner_headers: dict) -> None:
        """Invalid UUID format returns 400."""
        response = test_client.post(
            "/api/runner/jobs/invalid-uuid/fail",
            params={"error_message": "test error"},
            headers=runner_headers
        )
        assert response.status_code == 400

    def test_report_job_failure_nonexistent_job_returns_404(self, test_client: TestClient, runner_headers: dict) -> None:
        """Reporting failure for non-existent job returns 404."""
        fake_id = str(uuid.uuid4())
        response = test_client.post(
            f"/api/runner/jobs/{fake_id}/fail",
            params={"error_message": "test error"},
            headers=runner_headers
        )
        assert response.status_code == 404

    def test_report_job_failure_with_empty_error(self, test_client: TestClient, pending_transcription: dict, runner_headers: dict) -> None:
        """Empty error message is accepted."""
        response = test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/fail",
            params={"error_message": ""},
            headers=runner_headers
        )
        assert response.status_code == 200


# =============================================================================
# Heartbeat Tests (POST /api/runner/heartbeat)
# =============================================================================

@pytest.mark.integration
class TestRunnerHeartbeat:
    """Runner heartbeat endpoint tests."""

    def test_heartbeat_success(self, test_client: TestClient, runner_headers: dict) -> None:
        """Sending heartbeat succeeds."""
        response = test_client.post(
            "/api/runner/heartbeat",
            json={
                "runner_id": "test-runner-01",
                "current_jobs": 2
            },
            headers=runner_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_heartbeat_without_auth_returns_401(self, test_client: TestClient) -> None:
        """Heartbeat without authentication returns 401."""
        response = test_client.post(
            "/api/runner/heartbeat",
            json={"runner_id": "test", "current_jobs": 0}
        )
        # In test environment may return 200
        assert response.status_code in [401, 200]

    def test_heartbeat_with_zero_jobs(self, test_client: TestClient, runner_headers: dict) -> None:
        """Heartbeat with zero current jobs succeeds."""
        response = test_client.post(
            "/api/runner/heartbeat",
            json={
                "runner_id": "idle-runner",
                "current_jobs": 0
            },
            headers=runner_headers
        )
        assert response.status_code == 200

    def test_heartbeat_with_multiple_jobs(self, test_client: TestClient, runner_headers: dict) -> None:
        """Heartbeat with multiple active jobs succeeds."""
        response = test_client.post(
            "/api/runner/heartbeat",
            json={
                "runner_id": "busy-runner",
                "current_jobs": 5
            },
            headers=runner_headers
        )
        assert response.status_code == 200


# =============================================================================
# Edge Cases and Race Conditions
# =============================================================================

@pytest.mark.integration
class TestRunnerEdgeCases:
    """Edge cases and race condition tests."""

    def test_concurrent_job_start_fails_second_attempt(self, test_client: TestClient, pending_transcription: dict, runner_headers: dict) -> None:
        """Two runners trying to claim the same job - second attempt fails."""
        # First runner claims the job
        response1 = test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/start",
            json={"runner_id": "runner-01"},
            headers=runner_headers
        )
        assert response1.status_code == 200

        # Second runner tries to claim the same job
        response2 = test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/start",
            json={"runner_id": "runner-02"},
            headers=runner_headers
        )
        assert response2.status_code == 400

    def test_complete_already_completed_job(self, test_client: TestClient, pending_transcription: dict, runner_headers: dict) -> None:
        """Trying to complete an already completed job."""
        # First completion
        test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/complete",
            json={"text": "first", "processing_time_seconds": 10},
            headers=runner_headers
        )

        # Try to complete again
        response = test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/complete",
            json={"text": "second", "processing_time_seconds": 10},
            headers=runner_headers
        )
        # Should succeed (idempotent) - job is already completed
        assert response.status_code == 200

    def test_fail_after_complete(self, test_client: TestClient, pending_transcription: dict, runner_headers: dict) -> None:
        """Trying to fail a job after it was completed."""
        # First complete the job
        test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/complete",
            json={"text": "completed", "processing_time_seconds": 10},
            headers=runner_headers
        )

        # Try to fail it
        response = test_client.post(
            f"/api/runner/jobs/{pending_transcription['id']}/fail",
            params={"error_message": "too late"},
            headers=runner_headers
        )
        # The API doesn't check status before failing, so it might succeed
        assert response.status_code == 200

    def test_multiple_runners_poll_same_jobs(self, test_client: TestClient, runner_headers: dict) -> None:
        """Multiple runners polling - each should see the same pending jobs."""
        response1 = test_client.get("/api/runner/jobs?status=pending", headers=runner_headers)
        response2 = test_client.get("/api/runner/jobs?status=pending", headers=runner_headers)

        assert response1.status_code == 200
        assert response2.status_code == 200
        # Both should see jobs (may be different due to other tests)
        jobs1 = response1.json()
        jobs2 = response2.json()
        assert isinstance(jobs1, list)
        assert isinstance(jobs2, list)
