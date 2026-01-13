"""
Tests for Shared Transcription API endpoints (segments).

Tests public access to shared transcription segments for audio player navigation.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4, UUID
from datetime import datetime, timezone

from app.models.share_link import ShareLink
from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.services.storage_service import get_storage_service


def test_get_shared_segments_success(test_client: TestClient, db_session: Session):
    """Test successful segments retrieval for shared transcription."""
    # Create user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174001"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription
    transcription = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test_audio.m4a",
        file_path="/tmp/test_audio.m4a",
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(transcription)
    db_session.commit()

    # Create share link
    share_link = ShareLink(
        id=uuid4(),
        transcription_id=transcription.id,
        share_token="test_segments_token_123",
        expires_at=None
    )
    db_session.add(share_link)
    db_session.commit()

    # Setup: Create segments file
    storage_service = get_storage_service()
    segments = [
        {"start": 0.0, "end": 2.5, "text": "First segment"},
        {"start": 2.5, "end": 5.0, "text": "Second segment"},
    ]
    storage_service.save_transcription_segments(str(transcription.id), segments)

    # Test
    response = test_client.get(f"/api/shared/{share_link.share_token}/segments")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["start"] == 0.0
    assert data[0]["text"] == "First segment"


def test_get_shared_segments_not_found(test_client: TestClient, db_session: Session):
    """Test segments request when no segments file exists."""
    # Create user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174002"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription
    transcription = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test_audio2.m4a",
        file_path="/tmp/test_audio2.m4a",
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(transcription)
    db_session.commit()

    # Create share link
    share_link = ShareLink(
        id=uuid4(),
        transcription_id=transcription.id,
        share_token="test_no_segments_token",
        expires_at=None
    )
    db_session.add(share_link)
    db_session.commit()

    # Don't create segments file - should return empty array
    response = test_client.get(f"/api/shared/{share_link.share_token}/segments")

    assert response.status_code == 200
    assert response.json() == []


def test_get_shared_segments_invalid_token(test_client: TestClient):
    """Test segments request with invalid share token."""
    response = test_client.get("/api/shared/invalid-token-xyz/segments")

    assert response.status_code == 404


def test_get_shared_segments_expired_token(test_client: TestClient, db_session: Session):
    """Test segments request with expired share token."""
    from datetime import timedelta

    # Create user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174003"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription
    transcription = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test_audio3.m4a",
        file_path="/tmp/test_audio3.m4a",
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(transcription)
    db_session.commit()

    # Create expired share link
    expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
    share_link = ShareLink(
        id=uuid4(),
        transcription_id=transcription.id,
        share_token="expired_segments_token",
        expires_at=expired_time
    )
    db_session.add(share_link)
    db_session.commit()

    response = test_client.get(f"/api/shared/{share_link.share_token}/segments")

    assert response.status_code == 410  # Gone


def test_get_shared_audio_success(test_client: TestClient, db_session: Session, tmp_path):
    """Test successful audio streaming without Range header."""
    # Create user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174004"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription
    transcription = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test_audio.m4a",
        file_path="",  # Will be set below
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(transcription)
    db_session.commit()

    # Create share link
    share_link = ShareLink(
        id=uuid4(),
        transcription_id=transcription.id,
        share_token="test_audio_token_123",
        expires_at=None
    )
    db_session.add(share_link)
    db_session.commit()

    # Setup: Create a test audio file
    audio_path = tmp_path / "test_audio.m4a"
    audio_path.write_bytes(b"MOCK_AUDIO_DATA")

    # Mock transcription.file_path to point to our test file
    transcription.file_path = str(audio_path)
    db_session.commit()

    # Test full file request
    response = test_client.get(f"/api/shared/{share_link.share_token}/audio")

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mp4"
    # Headers are case-insensitive in HTTP, but Starlette returns them as-is
    assert "accept-ranges" in [k.lower() for k in response.headers.keys()]
    assert response.content == b"MOCK_AUDIO_DATA"


def test_get_shared_audio_range_request(test_client: TestClient, db_session: Session, tmp_path):
    """Test audio streaming with Range header (partial content)."""
    # Create user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174005"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription
    transcription = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test_audio_range.m4a",
        file_path="",
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(transcription)
    db_session.commit()

    # Create share link
    share_link = ShareLink(
        id=uuid4(),
        transcription_id=transcription.id,
        share_token="test_audio_range_token",
        expires_at=None
    )
    db_session.add(share_link)
    db_session.commit()

    # Setup: Create a larger test audio file
    audio_path = tmp_path / "test_audio_range.m4a"
    audio_data = b"0123456789" * 1000  # 10KB
    audio_path.write_bytes(audio_data)

    transcription.file_path = str(audio_path)
    db_session.commit()

    # Test Range request
    response = test_client.get(
        f"/api/shared/{share_link.share_token}/audio",
        headers={"Range": "bytes=0-1023"}
    )

    assert response.status_code == 206  # Partial Content
    # Check content-range header exists (case-insensitive)
    header_keys = {k.lower(): v for k, v in response.headers.items()}
    assert "content-range" in header_keys
    assert header_keys["content-range"].startswith("bytes 0-1023/")
    assert len(response.content) == 1024


def test_get_shared_audio_file_not_found(test_client: TestClient, db_session: Session):
    """Test audio request when file doesn't exist."""
    # Create user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174006"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create transcription
    transcription = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test_audio_missing.m4a",
        file_path="/nonexistent/path/audio.m4a",
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(transcription)
    db_session.commit()

    # Create share link
    share_link = ShareLink(
        id=uuid4(),
        transcription_id=transcription.id,
        share_token="test_audio_missing_token",
        expires_at=None
    )
    db_session.add(share_link)
    db_session.commit()

    response = test_client.get(f"/api/shared/{share_link.share_token}/audio")

    assert response.status_code == 404
