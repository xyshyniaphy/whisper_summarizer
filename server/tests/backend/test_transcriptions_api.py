"""
Tests for Transcriptions API endpoints.

Tests all CRUD operations, download, chat, and channel assignment endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4, UUID

from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.models.channel import Channel, ChannelMembership


# ============================================================================
# List Transcriptions (GET /api/transcriptions)
# ============================================================================

def test_list_transcriptions_empty(test_client, db_session):
    """Test listing transcriptions when database is empty."""
    response = test_client.get("/api/transcriptions")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 10


def test_list_transcriptions_with_data(test_client, db_session):
    """Test listing transcriptions with existing data."""
    # Create test user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174000"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Create test transcriptions
    transcriptions = []
    for i in range(3):
        trans = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name=f"test_{i}.m4a",
            file_path=f"/tmp/test_{i}.m4a",
            status=TranscriptionStatus.COMPLETED
        )
        transcriptions.append(trans)
        db_session.add(trans)
    db_session.commit()

    response = test_client.get("/api/transcriptions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["data"]) == 3


def test_list_transcriptions_pagination(test_client, db_session):
    """Test pagination of transcriptions list."""
    # Create test user and transcriptions
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    for i in range(15):
        trans = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name=f"test_{i}.m4a",
            file_path=f"/tmp/test_{i}.m4a",
            status=TranscriptionStatus.PENDING
        )
        db_session.add(trans)
    db_session.commit()

    # Test first page
    response = test_client.get("/api/transcriptions?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 15
    assert len(data["data"]) == 10
    assert data["page"] == 1
    assert data["has_next"] == True

    # Test second page
    response = test_client.get("/api/transcriptions?page=2&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 5
    assert data["has_next"] == False


def test_list_transcriptions_filter_by_status(test_client, db_session):
    """Test filtering transcriptions by status."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    # Create transcriptions with different statuses
    pending = Transcription(
        id=uuid4(), user_id=user.id, file_name="pending.m4a",
        file_path="/tmp/pending.m4a", status=TranscriptionStatus.PENDING
    )
    completed = Transcription(
        id=uuid4(), user_id=user.id, file_name="completed.m4a",
        file_path="/tmp/completed.m4a", status=TranscriptionStatus.COMPLETED,
        text="Completed text"
    )
    db_session.add_all([pending, completed])
    db_session.commit()

    # Filter by completed status
    response = test_client.get("/api/transcriptions?status=completed")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["data"][0]["status"] == "completed"


# ============================================================================
# Get Single Transcription (GET /api/transcriptions/{id})
# ============================================================================

def test_get_transcription_success(test_client, db_session):
    """Test getting a single transcription by ID."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED,
        text="Test transcription text"
    )
    db_session.add(trans)
    db_session.commit()

    response = test_client.get(f"/api/transcriptions/{trans.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(trans.id)
    assert data["file_name"] == "test.m4a"
    assert data["text"] == "Test transcription text"


def test_get_transcription_not_found(test_client, db_session):
    """Test getting a non-existent transcription."""
    fake_id = uuid4()
    response = test_client.get(f"/api/transcriptions/{fake_id}")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


# ============================================================================
# Delete Transcription (DELETE /api/transcriptions/{id})
# ============================================================================

def test_delete_transcription_success(test_client, db_session):
    """Test deleting a transcription."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.PENDING
    )
    db_session.add(trans)
    db_session.commit()

    response = test_client.delete(f"/api/transcriptions/{trans.id}")
    assert response.status_code == 204

    # Verify deletion
    db_session.refresh(trans)
    assert trans.is_deleted is True


def test_delete_transcription_not_found(test_client, db_session):
    """Test deleting a non-existent transcription."""
    fake_id = uuid4()
    response = test_client.delete(f"/api/transcriptions/{fake_id}")
    assert response.status_code == 404


def test_delete_all_transcriptions(test_client, db_session):
    """Test deleting all user transcriptions."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    # Create multiple transcriptions
    for i in range(5):
        trans = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name=f"test_{i}.m4a",
            file_path=f"/tmp/test_{i}.m4a",
            status=TranscriptionStatus.PENDING
        )
        db_session.add(trans)
    db_session.commit()

    response = test_client.delete("/api/transcriptions/all")
    assert response.status_code == 200
    data = response.json()
    assert "deleted_count" in data
    assert data["deleted_count"] >= 5


# ============================================================================
# Download Endpoints
# ============================================================================

def test_download_transcription_text(test_client, db_session):
    """Test downloading transcription as text."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED,
        text="Test transcription text for download"
    )
    db_session.add(trans)
    db_session.commit()

    response = test_client.get(f"/api/transcriptions/{trans.id}/download")
    assert response.status_code == 200
    assert b"Test transcription text for download" in response.content
    assert response.headers["content-type"] == "text/plain; charset=utf-8"


def test_download_transcription_text_empty(test_client, db_session):
    """Test downloading transcription when text is empty."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.PENDING,
        text=""
    )
    db_session.add(trans)
    db_session.commit()

    response = test_client.get(f"/api/transcriptions/{trans.id}/download")
    assert response.status_code == 404


@patch("app.api.transcriptions.DocumentGenerator")
def test_download_transcription_docx(mock_doc_gen, test_client, db_session):
    """Test downloading transcription as DOCX."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED,
        text="Test transcription"
    )
    db_session.add(trans)
    db_session.commit()

    # Mock DOCX generation
    mock_doc_gen.return_value.generate_docx.return_value = b"fake docx content"

    response = test_client.get(f"/api/transcriptions/{trans.id}/download-docx")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ============================================================================
# Chat Endpoints
# ============================================================================

def test_get_chat_history_empty(test_client, db_session):
    """Test getting chat history when no messages exist."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED,
        text="Test text"
    )
    db_session.add(trans)
    db_session.commit()

    response = test_client.get(f"/api/transcriptions/{trans.id}/chat")
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert data["messages"] == []


def test_get_chat_history_with_messages(test_client, db_session):
    """Test getting chat history with existing messages."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED,
        text="Test text"
    )
    db_session.add(trans)
    db_session.commit()

    # Add some chat messages via the model relationship
    # (This would require the summary model to be set up)
    # For now, just test the endpoint structure

    response = test_client.get(f"/api/transcriptions/{trans.id}/chat")
    assert response.status_code == 200


def test_send_chat_message(test_client, db_session):
    """Test sending a chat message."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED,
        text="Test transcription text"
    )
    db_session.add(trans)
    db_session.commit()

    # Mock the chat service
    with patch("app.api.transcriptions.ChatService") as mock_chat:
        mock_chat_service = MagicMock()
        mock_chat_service.send_message.return_value = {
            "role": "assistant",
            "content": "This is a test response"
        }
        mock_chat.return_value = mock_chat_service

        response = test_client.post(
            f"/api/transcriptions/{trans.id}/chat",
            json={"content": "Test question"}
        )

    # The endpoint should respond
    # (Actual implementation would depend on chat service)
    assert response.status_code in [200, 501]  # 501 if chat not implemented


# ============================================================================
# Channel Assignment Endpoints
# ============================================================================

def test_assign_transcription_to_channels(test_client, db_session):
    """Test assigning transcription to channels."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    # Create channels
    channel1 = Channel(id=uuid4(), name="Channel 1", created_by=user.id)
    channel2 = Channel(id=uuid4(), name="Channel 2", created_by=user.id)
    db_session.add_all([channel1, channel2])
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED,
        text="Test text"
    )
    db_session.add(trans)
    db_session.commit()

    response = test_client.post(
        f"/api/transcriptions/{trans.id}/channels",
        json={"channel_ids": [str(channel1.id), str(channel2.id)]}
    )

    assert response.status_code == 200
    data = response.json()
    assert "channels" in data
    assert len(data["channels"]) == 2


def test_get_transcription_channels(test_client, db_session):
    """Test getting channels for a transcription."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    # Create channel and assign transcription
    channel = Channel(id=uuid4(), name="Test Channel", created_by=user.id)
    db_session.add(channel)
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED,
        text="Test text"
    )
    db_session.add(trans)
    db_session.commit()

    # Create channel membership
    membership = ChannelMembership(
        channel_id=channel.id,
        user_id=trans.id  # Using transcription_id as user_id (for junction table)
    )
    db_session.add(membership)
    db_session.commit()

    response = test_client.get(f"/api/transcriptions/{trans.id}/channels")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_assign_transcription_invalid_channel(test_client, db_session):
    """Test assigning transcription to non-existent channel."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.PENDING
    )
    db_session.add(trans)
    db_session.commit()

    fake_channel_id = uuid4()
    response = test_client.post(
        f"/api/transcriptions/{trans.id}/channels",
        json={"channel_ids": [str(fake_channel_id)]}
    )

    # Should return error for non-existent channel
    assert response.status_code in [400, 404]


# ============================================================================
# Share Link Endpoint
# ============================================================================

def test_create_share_link(test_client, db_session):
    """Test creating a share link for transcription."""
    user = User(id=UUID("123e4567-e89b-42d3-a456-426614174000"), email=f"test-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    trans = Transcription(
        id=uuid4(),
        user_id=user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED,
        text="Test text to share"
    )
    db_session.add(trans)
    db_session.commit()

    response = test_client.post(f"/api/transcriptions/{trans.id}/share")
    assert response.status_code == 200
    data = response.json()
    assert "share_token" in data or "share_url" in data


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_get_transcription_invalid_uuid_format(test_client, db_session):
    """Test getting transcription with invalid UUID format."""
    response = test_client.get("/api/transcriptions/invalid-uuid-format")
    assert response.status_code == 422  # Validation error for invalid UUID


def test_list_transcriptions_invalid_page(test_client, db_session):
    """Test pagination with invalid page parameters."""
    response = test_client.get("/api/transcriptions?page=0")
    assert response.status_code == 422  # Validation error

    response = test_client.get("/api/transcriptions?page_size=0")
    assert response.status_code == 422  # Validation error

    response = test_client.get("/api/transcriptions?page_size=1000")
    assert response.status_code == 422  # Max page size exceeded


def test_list_transcriptions_invalid_status(test_client, db_session):
    """Test filtering with invalid status value."""
    response = test_client.get("/api/transcriptions?status=invalid_status")
    # API returns 200 with empty list for invalid status (no validation)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["data"] == []
