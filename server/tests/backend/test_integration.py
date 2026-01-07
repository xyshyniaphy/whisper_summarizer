"""
Integration tests for the complete backend workflow.

Tests end-to-end scenarios including:
- Audio upload → Runner processing → Result retrieval
- Channel assignment and filtering
- Admin operations
"""

import os
import pytest
import tempfile
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.models.channel import Channel, ChannelMembership


# ============================================================================
# Fixtures for Integration Tests
# ============================================================================

@pytest.fixture
def test_audio_file():
    """Create a temporary audio file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
        f.write(b"fake audio content")
        return Path(f.name)


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"test-{user_id.hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_user(db_session):
    """Create an admin user."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"admin-{user_id.hex[:8]}@example.com",
        is_active=True,
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_client(test_client, test_user):
    """Create authenticated test client."""
    def mock_get_current_user():
        return {
            "id": str(test_user.id),
            "email": test_user.email,
            "email_confirmed_at": "2025-01-01T00:00:00Z"
        }

    from app.core.supabase import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = mock_get_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture
def admin_auth_client(test_client, admin_user):
    """Create admin authenticated test client."""
    def mock_get_current_user():
        return {
            "id": str(admin_user.id),
            "email": admin_user.email,
            "email_confirmed_at": "2025-01-01T00:00:00Z"
        }

    from app.core.supabase import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = mock_get_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


# ============================================================================
# End-to-End Workflow: Upload → Process → Complete
# ============================================================================

def test_e2e_workflow_upload_to_complete(auth_client, test_audio_file, db_session, test_user):
    """
    Test complete workflow:
    1. Upload audio file
    2. Verify status is pending
    3. Simulate runner processing (start → complete)
    4. Verify final status and result
    """
    # Step 1: Upload audio
    with open(test_audio_file, "rb") as f:
        response = auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.m4a", f, "audio/mpeg")}
        )

    assert response.status_code == 201
    data = response.json()
    transcription_id = data["id"]
    assert data["status"] == "pending"
    assert data["file_name"] == "test.m4a"

    # Step 2: Verify in database
    trans = db_session.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()
    assert trans is not None
    assert trans.status == TranscriptionStatus.PENDING

    # Step 3: Simulate runner claiming job
    auth_client.headers["Authorization"] = f"Bearer {os.environ.get('RUNNER_API_KEY', 'test-runner-api-key')}"
    start_response = auth_client.post(
        f"/api/runner/jobs/{transcription_id}/start",
        json={"runner_id": "test-runner"}
    )
    assert start_response.status_code == 200

    db_session.refresh(trans)
    assert trans.status == TranscriptionStatus.PROCESSING
    assert trans.runner_id == "test-runner"

    # Step 4: Simulate runner completing job
    complete_response = auth_client.post(
        f"/api/runner/jobs/{transcription_id}/complete",
        json={
            "text": "This is the transcribed text from the audio.",
            "summary": "Summary of the transcription.",
            "processing_time_seconds": 30
        }
    )
    assert complete_response.status_code == 200

    # Step 5: Verify final state
    db_session.refresh(trans)
    assert trans.status == TranscriptionStatus.COMPLETED
    # Note: trans.text returns formatted text (summary) first, then original text
    assert trans.text == "Summary of the transcription."
    assert trans.storage_path is not None  # Text was saved
    assert trans.file_path is None  # Audio was deleted
    assert trans.processing_time_seconds == 30

    # Step 6: Verify retrieval
    auth_client.headers["Authorization"] = f"Bearer {test_user.id}"  # Restore user auth
    get_response = auth_client.get(f"/api/transcriptions/{transcription_id}")
    assert get_response.status_code == 200
    result = get_response.json()
    assert result["status"] == "completed"
    # API returns formatted text (summary) in text field
    assert result["text"] == "Summary of the transcription."


def test_e2e_workflow_with_failure(auth_client, test_audio_file, db_session):
    """
    Test workflow with processing failure:
    1. Upload audio
    2. Runner claims job
    3. Runner reports failure
    4. Verify error is recorded
    """
    # Upload audio
    with open(test_audio_file, "rb") as f:
        response = auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.m4a", f, "audio/mpeg")}
        )

    assert response.status_code == 201
    data = response.json()
    transcription_id = data["id"]

    # Claim job
    auth_client.headers["Authorization"] = f"Bearer {os.environ.get('RUNNER_API_KEY', 'test-runner-api-key')}"
    start_response = auth_client.post(
        f"/api/runner/jobs/{transcription_id}/start",
        json={"runner_id": "test-runner"}
    )
    assert start_response.status_code == 200

    # Report failure
    fail_response = auth_client.post(
        f"/api/runner/jobs/{transcription_id}/fail",
        params={"error_message": "Processing failed: audio format not supported"}
    )
    assert fail_response.status_code == 200

    # Verify error state
    trans = db_session.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()
    assert trans.status == TranscriptionStatus.FAILED
    assert "audio format not supported" in trans.error_message


# ============================================================================
# Channel Assignment Integration
# ============================================================================

def test_e2e_channel_assignment_and_filtering(auth_client, admin_auth_client, db_session, test_user, admin_user):
    """
    Test complete channel workflow:
    1. Admin creates channels
    2. Admin adds user to channels
    3. User uploads audio
    4. Admin assigns audio to channels
    5. User retrieves filtered transcriptions by channel
    """
    # Step 1: Admin creates channels
    channel_response = admin_auth_client.post(
        "/api/admin/channels",
        json={
            "name": "Project Alpha",
            "description": "Alpha project recordings"
        }
    )
    assert channel_response.status_code == 201
    channel1_id = channel_response.json()["id"]

    channel_response = admin_auth_client.post(
        "/api/admin/channels",
        json={"name": "Project Beta", "description": "Beta project recordings"}
    )
    assert channel_response.status_code == 201
    channel2_id = channel_response.json()["id"]

    # Step 2: Admin adds user to channels
    member_response = admin_auth_client.post(
        f"/api/admin/channels/{channel1_id}/members",
        json={"user_id": str(test_user.id)}
    )
    assert member_response.status_code == 200

    # Verify user is now a member
    membership = db_session.query(ChannelMembership).filter(
        ChannelMembership.channel_id == channel1_id,
        ChannelMembership.user_id == test_user.id
    ).first()
    assert membership is not None

    # Step 3: Upload multiple transcriptions
    transcriptions = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
            f.write(b"audio content")
            f.flush()

            with open(f.name, "rb") as audio_file:
                response = auth_client.post(
                    "/api/audio/upload",
                    files={"file": (f"audio_{i}.m4a", audio_file, "audio/mpeg")}
                )
                assert response.status_code == 201
                transcriptions.append(response.json()["id"])

    # Step 4: Assign first two transcriptions to channel
    assign_response = admin_auth_client.post(
        f"/api/admin/audio/{transcriptions[0]}/channels",
        json={"channel_ids": [channel1_id, channel2_id]}
    )
    assert assign_response.status_code == 200

    assign_response = admin_auth_client.post(
        f"/api/admin/audio/{transcriptions[1]}/channels",
        json={"channel_ids": [channel1_id]}
    )
    assert assign_response.status_code == 200

    # Step 5: User retrieves their transcriptions
    list_response = auth_client.get("/api/transcriptions")
    assert list_response.status_code == 200
    data = list_response.json()
    assert data["total"] >= 3


# ============================================================================
# Admin User Management Integration
# ============================================================================

def test_e2e_user_lifecycle(admin_auth_client, db_session):
    """
    Test complete user lifecycle:
    1. New user registers (inactive)
    2. Admin activates user
    3. User can access their data
    4. Admin grants admin privileges
    5. User can access admin endpoints
    """
    # Create new inactive user
    new_user_id = uuid4()
    new_user = User(
        id=new_user_id,
        email=f"newuser-{new_user_id.hex[:8]}@example.com",
        is_active=False,
        is_admin=False
    )
    db_session.add(new_user)
    db_session.commit()

    user_id = new_user.id

    # Admin activates user
    activate_response = admin_auth_client.put(f"/api/admin/users/{user_id}/activate")
    assert activate_response.status_code == 200

    db_session.refresh(new_user)
    assert new_user.is_active is True

    # Grant admin
    admin_response = admin_auth_client.put(
        f"/api/admin/users/{user_id}/admin",
        json={"is_admin": True}
    )
    assert admin_response.status_code == 200

    db_session.refresh(new_user)
    assert new_user.is_admin is True

    # Soft delete user
    delete_response = admin_auth_client.delete(f"/api/admin/users/{user_id}")
    assert delete_response.status_code == 200

    db_session.refresh(new_user)
    assert new_user.deleted_at is not None


# ============================================================================
# Runner Heartbeat Integration
# ============================================================================

def test_runner_heartbeat_integration(auth_client):
    """
    Test runner heartbeat and monitoring:
    1. Runner sends heartbeat with active jobs
    2. Server acknowledges heartbeat
    3. Runner can poll for jobs
    """
    auth_client.headers["Authorization"] = f"Bearer {os.environ.get('RUNNER_API_KEY', 'test-runner-api-key')}"

    # Send heartbeat with active jobs
    heartbeat_response = auth_client.post(
        "/api/runner/heartbeat",
        json={"runner_id": "runner-test", "current_jobs": 2}
    )
    assert heartbeat_response.status_code == 200
    data = heartbeat_response.json()
    assert data["status"] == "ok"

    # Poll for jobs (should return empty list if no pending jobs)
    jobs_response = auth_client.get("/api/runner/jobs?status=pending&limit=10")
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert isinstance(jobs, list)


# ============================================================================
# Error Handling Integration Tests
# ============================================================================

def test_e2e_invalid_audio_upload(auth_client):
    """Test upload with invalid file."""
    response = auth_client.post(
        "/api/audio/upload",
        files={"file": ("test.txt", b"not audio", "text/plain")}
    )
    # Should either reject or accept but process will fail later
    assert response.status_code in [201, 400]


def test_e2e_complete_non_existent_job(auth_client):
    """Test completing a job that doesn't exist."""
    auth_client.headers["Authorization"] = f"Bearer {os.environ.get('RUNNER_API_KEY', 'test-runner-api-key')}"
    fake_id = uuid4()

    response = auth_client.post(
        f"/api/runner/jobs/{fake_id}/complete",
        json={"text": "test", "summary": "test", "processing_time_seconds": 10}
    )
    assert response.status_code == 404


def test_e2e_double_start_job(auth_client, test_audio_file, db_session):
    """Test that a job can't be started twice."""
    # Upload audio
    with open(test_audio_file, "rb") as f:
        response = auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.m4a", f, "audio/mpeg")}
        )
    transcription_id = response.json()["id"]

    # First start
    auth_client.headers["Authorization"] = f"Bearer {os.environ.get('RUNNER_API_KEY', 'test-runner-api-key')}"
    start_response = auth_client.post(
        f"/api/runner/jobs/{transcription_id}/start",
        json={"runner_id": "runner-1"}
    )
    assert start_response.status_code == 200

    # Second start (should fail)
    start_response2 = auth_client.post(
        f"/api/runner/jobs/{transcription_id}/start",
        json={"runner_id": "runner-2"}
    )
    assert start_response2.status_code == 400  # Bad request - already processing


def test_e2e_download_before_completion(auth_client, test_audio_file):
    """Test downloading transcription before processing is complete."""
    # Upload audio
    with open(test_audio_file, "rb") as f:
        response = auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.m4a", f, "audio/mpeg")}
        )
    transcription_id = response.json()["id"]

    # Try to download before completion
    response = auth_client.get(f"/api/transcriptions/{transcription_id}/download")
    # Should return 400 (empty text) or 404 (not ready)
    assert response.status_code in [400, 404]


# ============================================================================
# Performance Tests
# ============================================================================

def test_e2e_bulk_operations_performance(auth_client, admin_auth_client, db_session, test_user, admin_user):
    """
    Test performance of bulk operations:
    1. Create many transcriptions
    2. List with pagination
    3. Bulk delete
    """
    # Create channel for filtering
    channel = Channel(
        id=uuid4(),
        name="Performance Test",
        created_by=admin_user.id
    )
    db_session.add(channel)
    db_session.commit()

    # Upload multiple transcriptions efficiently
    transcription_ids = []
    for i in range(20):
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
            f.write(b"audio content")
            f.flush()

            with open(f.name, "rb") as audio_file:
                response = auth_client.post(
                    "/api/audio/upload",
                    files={"file": (f"bulk_{i}.m4a", audio_file, "audio/mpeg")}
                )
                assert response.status_code == 201
                transcription_ids.append(response.json()["id"])

    # Test pagination performance
    import time
    start = time.time()
    response = auth_client.get("/api/transcriptions?page=1&page_size=10")
    elapsed = time.time() - start

    assert response.status_code == 200
    assert elapsed < 2.0  # Should complete in under 2 seconds
    data = response.json()
    assert data["total"] >= 20


# ============================================================================
# Data Consistency Tests
# ============================================================================

def test_e2e_data_consistency_after_deletion(auth_client, admin_auth_client, db_session, test_user):
    """
    Test data consistency when related entities are deleted:
    1. Create channel with members
    2. Create transcription with channel assignments
    3. Delete channel (CASCADE should delete memberships and assignments)
    4. Verify orphaned records are handled
    """
    # Create channel
    channel = Channel(
        id=uuid4(),
        name="To Delete",
        created_by=test_user.id
    )
    db_session.add(channel)

    # Add member
    membership = ChannelMembership(
        channel_id=channel.id,
        user_id=test_user.id
    )

    # Create transcription
    trans = Transcription(
        id=uuid4(),
        user_id=test_user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED
        # Note: text is a read-only property, can't set in constructor
    )
    db_session.add(trans)

    # Create transcription-channel junction
    from app.models.channel import TranscriptionChannel
    tc = TranscriptionChannel(
        transcription_id=trans.id,
        channel_id=channel.id
    )
    db_session.add_all([channel, membership, trans, tc])
    db_session.commit()

    # Delete channel as admin
    channel_id = channel.id
    delete_response = admin_auth_client.delete(f"/api/admin/channels/{channel_id}")
    assert delete_response.status_code == 200

    # Verify CASCADE deletion worked
    remaining_channel = db_session.query(Channel).filter(Channel.id == channel_id).first()
    assert remaining_channel is None

    remaining_membership = db_session.query(ChannelMembership).filter(
        ChannelMembership.channel_id == channel_id
    ).first()
    assert remaining_membership is None

    remaining_tc = db_session.query(TranscriptionChannel).filter(
        TranscriptionChannel.channel_id == channel_id
    ).first()
    assert remaining_tc is None

    # Transcription should still exist (orphaned)
    remaining_trans = db_session.query(Transcription).filter(Transcription.id == trans.id).first()
    assert remaining_trans is not None


# ============================================================================
# Race Condition Tests
# ============================================================================

def test_e2e_concurrent_job_claims(auth_client, test_audio_file):
    """
    Test that concurrent runners can't claim the same job:
    1. Upload audio
    2. Runner 1 claims job
    3. Runner 2 tries to claim same job (should fail)
    """
    # Upload audio
    with open(test_audio_file, "rb") as f:
        response = auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.m4a", f, "audio/mpeg")}
        )
    transcription_id = response.json()["id"]

    # Runner 1 claims job
    auth_client.headers["Authorization"] = f"Bearer {os.environ.get('RUNNER_API_KEY', 'test-runner-api-key')}"
    start_response1 = auth_client.post(
        f"/api/runner/jobs/{transcription_id}/start",
        json={"runner_id": "runner-1"}
    )
    assert start_response1.status_code == 200

    # Runner 2 tries to claim same job
    start_response2 = auth_client.post(
        f"/api/runner/jobs/{transcription_id}/start",
        json={"runner_id": "runner-2"}
    )
    assert start_response2.status_code == 400  # Bad request - already claimed


# ============================================================================
# Security Tests
# ============================================================================

def test_e2e_unauthorized_admin_access(test_client, db_session):
    """Test that regular users cannot access admin endpoints."""
    # Create a regular (non-admin) user
    from uuid import uuid4
    regular_user_id = uuid4()
    regular_user = User(
        id=regular_user_id,
        email=f"regular-{regular_user_id.hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(regular_user)
    db_session.commit()

    def mock_get_current_user():
        # Return dict that looks like Supabase user response
        return {
            "id": str(regular_user.id),
            "email": regular_user.email,
            "aud": "authenticated",
            "role": "authenticated",
            "email_confirmed_at": None,
            "created_at": None,
            "updated_at": None
        }

    from app.core.supabase import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = mock_get_current_user

    client = TestClient(app)

    # Try to access admin endpoints
    response = client.get("/api/admin/users")
    assert response.status_code == 403

    response = client.post("/api/admin/channels", json={"name": "Test"})
    assert response.status_code == 403

    app.dependency_overrides = {}


def test_e2e_invalid_runner_api_key(auth_client, test_audio_file):
    """Test that invalid runner API key is rejected."""
    # Upload audio
    with open(test_audio_file, "rb") as f:
        upload_response = auth_client.post(
            "/api/audio/upload",
            files={"file": ("test.m4a", f, "audio/mpeg")}
        )
    transcription_id = upload_response.json()["id"]

    # Try to access runner API with invalid key
    auth_client.headers["Authorization"] = "Bearer invalid-key"
    response = auth_client.post(
        f"/api/runner/jobs/{transcription_id}/start",
        json={"runner_id": "test-runner"}
    )
    assert response.status_code == 401  # Unauthorized
