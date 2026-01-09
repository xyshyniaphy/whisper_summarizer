"""
Tests for Shared Transcription API endpoints.

Tests public access to shared transcriptions (no authentication required).
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime, timedelta, timezone

from app.models.user import User
from app.models.transcription import Transcription, TranscriptionStatus
from app.models.share_link import ShareLink
from app.models.summary import Summary


# ============================================================================
# Get Shared Transcription (GET /api/shared/{share_token})
# ============================================================================

def test_get_shared_transcription_success(test_client, db_session):
    """Test accessing a valid shared transcription."""
    # Create user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174000"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription
    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(trans)
    db_session.commit()

    # Create text file
    from app.services.storage_service import get_storage_service
    storage = get_storage_service()
    storage.save_transcription_text(trans.id, "Test transcription text")

    # Create share link
    share_link = ShareLink(
        id=uuid4(),
        transcription_id=trans.id,
        share_token="test_token_123",
        expires_at=None
    )
    db_session.add(share_link)
    db_session.commit()

    # Access shared transcription
    response = test_client.get(f"/api/shared/{share_link.share_token}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(trans.id)
    assert data["file_name"] == "test.m4a"
    assert data["text"] == "Test transcription text"


def test_get_shared_transcription_not_found(test_client, db_session):
    """Test accessing a non-existent share token."""
    response = test_client.get("/api/shared/invalid_token_999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_get_shared_transcription_expired(test_client, db_session):
    """Test accessing an expired share link."""
    # Create user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174000"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription
    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(trans)
    db_session.commit()

    # Create expired share link
    expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
    share_link = ShareLink(
        id=uuid4(),
        transcription_id=trans.id,
        share_token="expired_token_123",
        expires_at=expired_time
    )
    db_session.add(share_link)
    db_session.commit()

    # Try to access expired link
    response = test_client.get(f"/api/shared/{share_link.share_token}")
    assert response.status_code == 410  # Gone
    data = response.json()
    assert "detail" in data


def test_get_shared_transcription_increments_access_count(test_client, db_session):
    """Test that accessing shared transcription increments access count."""
    # Create user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174000"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription
    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(trans)
    db_session.commit()

    # Create share link
    share_link = ShareLink(
        id=uuid4(),
        transcription_id=trans.id,
        share_token="count_token_123",
        expires_at=None,
        access_count=5
    )
    db_session.add(share_link)
    db_session.commit()

    # Access shared transcription
    response = test_client.get(f"/api/shared/{share_link.share_token}")
    assert response.status_code == 200

    # Verify access count incremented
    db_session.refresh(share_link)
    assert share_link.access_count == 6


def test_get_shared_transcription_with_summary(test_client, db_session):
    """Test accessing shared transcription that has a summary."""
    # Create user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174000"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription
    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(trans)
    db_session.commit()

    # Create summary
    summary = Summary(
        id=uuid4(),
        transcription_id=trans.id,
        summary_text="Test summary text",
        model_name="glm-4"
    )
    db_session.add(summary)
    db_session.commit()

    # Create text file
    from app.services.storage_service import get_storage_service
    storage = get_storage_service()
    storage.save_transcription_text(trans.id, "Test transcription text")

    # Create share link
    share_link = ShareLink(
        id=uuid4(),
        transcription_id=trans.id,
        share_token="summary_token_123",
        expires_at=None
    )
    db_session.add(share_link)
    db_session.commit()

    # Access shared transcription
    response = test_client.get(f"/api/shared/{share_link.share_token}")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "Test summary text"


def test_get_shared_transcription_without_text_file(test_client, db_session):
    """Test accessing shared transcription when text file doesn't exist."""
    # Create user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174000"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription without text file
    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.PENDING
    )
    db_session.add(trans)
    db_session.commit()

    # Create share link
    share_link = ShareLink(
        id=uuid4(),
        transcription_id=trans.id,
        share_token="no_text_token_123",
        expires_at=None
    )
    db_session.add(share_link)
    db_session.commit()

    # Try to access shared transcription
    response = test_client.get(f"/api/shared/{share_link.share_token}")
    # Should still return 200 with empty text
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == ""


def test_get_shared_transcription_returns_404_when_transcription_deleted(test_client, db_session):
    """Test that accessing shared link returns 404 when transcription is deleted (line 51)."""
    from app.models.user import User
    from app.models.share_link import ShareLink
    import uuid
    from sqlalchemy import text

    # Create a user
    user = User(
        id=uuid.uuid4(),
        email=f"shared-deleted-{uuid.uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription
    trans = Transcription(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.PENDING
    )
    db_session.add(trans)
    db_session.commit()

    # Create share link
    share_link = ShareLink(
        id=uuid.uuid4(),
        transcription_id=trans.id,
        share_token="deleted_trans_token_123",
        expires_at=None
    )
    db_session.add(share_link)
    db_session.commit()

    # Store the share token before deleting
    share_token = share_link.share_token

    # Delete ONLY the transcription row using raw SQL to bypass cascade
    # This allows us to test the case where share_link exists but transcription doesn't
    db_session.execute(text("DELETE FROM transcriptions WHERE id = :trans_id"), {"trans_id": str(trans.id)})
    db_session.commit()

    # Try to access shared transcription - share link exists but transcription doesn't
    # This should hit line 51 in shared.py where transcription is None
    response = test_client.get(f"/api/shared/{share_token}")
    assert response.status_code == 404
