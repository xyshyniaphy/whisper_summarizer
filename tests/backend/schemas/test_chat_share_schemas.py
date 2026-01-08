"""
Schema Validation Tests - Chat and Share

Tests Pydantic schemas for chat and share functionality.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime, timedelta
from uuid import UUID
from app.schemas.chat import (
    ChatMessageBase,
    ChatMessageCreate,
    ChatMessageInDBBase,
    ChatMessage,
    ChatHistoryResponse,
)
from app.schemas.share import (
    ShareLinkBase,
    ShareLinkCreate,
    ShareLinkInDBBase,
    ShareLink,
    SharedTranscriptionResponse,
)


class TestChatSchemas:
    """Test chat-related schemas"""

    def test_chat_message_base_valid(self):
        """Valid ChatMessageBase"""
        data = {
            "role": "user",
            "content": "Hello, this is a message"
        }
        message = ChatMessageBase(**data)
        assert message.role == "user"
        assert message.content == "Hello, this is a message"

    def test_chat_message_base_assistant_role(self):
        """Valid ChatMessageBase with assistant role"""
        data = {
            "role": "assistant",
            "content": "Assistant response"
        }
        message = ChatMessageBase(**data)
        assert message.role == "assistant"

    def test_chat_message_create_valid(self):
        """Valid ChatMessageCreate"""
        data = {
            "transcription_id": "550e8400-e29b-41d4-a716-446655440000",
            "role": "user",
            "content": "Hello"
        }
        message = ChatMessageCreate(**data)
        assert isinstance(message.transcription_id, UUID)
        assert message.role == "user"

    def test_chat_message_create_invalid_uuid(self):
        """Invalid ChatMessageCreate with bad UUID"""
        data = {
            "transcription_id": "not-a-uuid",
            "role": "user",
            "content": "Hello"
        }
        with pytest.raises(ValidationError):
            ChatMessageCreate(**data)

    def test_chat_message_in_db_base_valid(self):
        """Valid ChatMessageInDBBase"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "user_id": "750e8400-e29b-41d4-a716-446655440002",
            "role": "user",
            "content": "Hello",
            "created_at": "2024-01-01T00:00:00Z"
        }
        message = ChatMessageInDBBase(**data)
        assert isinstance(message.id, UUID)
        assert isinstance(message.transcription_id, UUID)

    def test_chat_message_valid(self):
        """Valid ChatMessage"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "user_id": "750e8400-e29b-41d4-a716-446655440002",
            "role": "user",
            "content": "Hello",
            "created_at": "2024-01-01T00:00:00Z"
        }
        message = ChatMessage(**data)
        assert message.role == "user"
        assert message.content == "Hello"

    def test_chat_history_response_valid(self):
        """Valid ChatHistoryResponse"""
        data = {
            "messages": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
                    "user_id": "750e8400-e29b-41d4-a716-446655440002",
                    "role": "user",
                    "content": "Hello",
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ]
        }
        response = ChatHistoryResponse(**data)
        assert len(response.messages) == 1

    def test_chat_history_response_empty(self):
        """Valid ChatHistoryResponse with empty messages"""
        data = {"messages": []}
        response = ChatHistoryResponse(**data)
        assert response.messages == []


class TestShareLinkSchemas:
    """Test share link schemas"""

    def test_share_link_base_valid(self):
        """Valid ShareLinkBase"""
        data = {
            "transcription_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        link = ShareLinkBase(**data)
        assert isinstance(link.transcription_id, UUID)

    def test_share_link_create_valid(self):
        """Valid ShareLinkCreate"""
        data = {
            "transcription_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        link = ShareLinkCreate(**data)
        assert isinstance(link.transcription_id, UUID)

    def test_share_link_create_invalid_uuid(self):
        """Invalid ShareLinkCreate with bad UUID"""
        data = {"transcription_id": "not-a-uuid"}
        with pytest.raises(ValidationError):
            ShareLinkCreate(**data)

    def test_share_link_in_db_base_valid(self):
        """Valid ShareLinkInDBBase"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "share_token": "abc123def456",
            "created_at": "2024-01-01T00:00:00Z",
            "expires_at": "2024-01-02T00:00:00Z",
            "access_count": 5
        }
        link = ShareLinkInDBBase(**data)
        assert link.share_token == "abc123def456"
        assert link.access_count == 5

    def test_share_link_in_db_base_no_expiration(self):
        """Valid ShareLinkInDBBase without expiration"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "share_token": "abc123def456",
            "created_at": "2024-01-01T00:00:00Z",
            "expires_at": None,
            "access_count": 0
        }
        link = ShareLinkInDBBase(**data)
        assert link.expires_at is None
        assert link.access_count == 0

    def test_share_link_valid(self):
        """Valid ShareLink with public URL"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "share_token": "abc123def456",
            "created_at": "2024-01-01T00:00:00Z",
            "expires_at": "2024-01-02T00:00:00Z",
            "access_count": 10,
            "share_url": "https://example.com/share/abc123def456"
        }
        link = ShareLink(**data)
        assert link.share_url == "https://example.com/share/abc123def456"

    def test_share_link_without_url(self):
        """Valid ShareLink without public URL"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "share_token": "abc123def456",
            "created_at": "2024-01-01T00:00:00Z",
            "expires_at": None,
            "access_count": 0,
            "share_url": None
        }
        link = ShareLink(**data)
        assert link.share_url is None

    def test_shared_transcription_response_valid(self):
        """Valid SharedTranscriptionResponse"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "test.mp3",
            "text": "This is a test transcription",
            "summary": "This is a test summary",
            "language": "en",
            "duration_seconds": 120.5,
            "created_at": "2024-01-01T00:00:00Z"
        }
        response = SharedTranscriptionResponse(**data)
        assert response.file_name == "test.mp3"
        assert response.text == "This is a test transcription"
        assert response.summary == "This is a test summary"

    def test_shared_transcription_response_no_summary(self):
        """Valid SharedTranscriptionResponse without summary"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "test.mp3",
            "text": "This is a test transcription",
            "summary": None,
            "language": "en",
            "duration_seconds": 120.5,
            "created_at": "2024-01-01T00:00:00Z"
        }
        response = SharedTranscriptionResponse(**data)
        assert response.summary is None

    def test_shared_transcription_response_minimal(self):
        """Valid SharedTranscriptionResponse with minimal data"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "test.mp3",
            "text": "Test",
            "summary": None,
            "language": None,
            "duration_seconds": None,
            "created_at": "2024-01-01T00:00:00Z"
        }
        response = SharedTranscriptionResponse(**data)
        assert response.text == "Test"


class TestChatSchemaEdgeCases:
    """Test chat schema edge cases"""

    def test_unicode_chat_message(self):
        """Test chat message with unicode content"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "user_id": "750e8400-e29b-41d4-a716-446655440002",
            "role": "user",
            "content": "こんにちは世界",
            "created_at": "2024-01-01T00:00:00Z"
        }
        message = ChatMessage(**data)
        assert "こんにちは世界" in message.content

    def test_multiline_chat_message(self):
        """Test chat message with multiple lines"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "user_id": "750e8400-e29b-41d4-a716-446655440002",
            "role": "user",
            "content": "Line 1\nLine 2\nLine 3",
            "created_at": "2024-01-01T00:00:00Z"
        }
        message = ChatMessage(**data)
        assert message.content == "Line 1\nLine 2\nLine 3"

    def test_very_long_chat_message(self):
        """Test chat message with very long content"""
        long_content = "x" * 10000
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "user_id": "750e8400-e29b-41d4-a716-446655440002",
            "role": "user",
            "content": long_content,
            "created_at": "2024-01-01T00:00:00Z"
        }
        message = ChatMessage(**data)
        assert len(message.content) == 10000

    def test_chat_history_ordering(self):
        """Test that chat history maintains order"""
        data = {
            "messages": [
                {
                    "id": f"550e8400-e29b-41d4-a716-44665544000{i}",
                    "transcription_id": "650e8400-e29b-41d4-a716-446655440000",
                    "user_id": "750e8400-e29b-41d4-a716-446655440001",
                    "role": "user",
                    "content": f"Message {i}",
                    "created_at": f"2024-01-01T00:0{i}:00Z"
                }
                for i in range(5)
            ]
        }
        response = ChatHistoryResponse(**data)
        assert response.messages[0].content == "Message 0"
        assert response.messages[4].content == "Message 4"


class TestShareLinkSchemaEdgeCases:
    """Test share link schema edge cases"""

    def test_share_token_formats(self):
        """Test various share token formats"""
        valid_tokens = [
            "abc123",
            "token-with-hyphens",
            "TOKEN_WITH_CAPS",
            "123456789",
            "mixedToken-123_ABC"
        ]

        for token in valid_tokens:
            data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
                "share_token": token,
                "created_at": "2024-01-01T00:00:00Z",
                "expires_at": None,
                "access_count": 0,
                "share_url": f"https://example.com/share/{token}"
            }
            link = ShareLink(**data)
            assert link.share_token == token

    def test_share_link_expiration_future(self):
        """Test share link with future expiration"""
        future_time = datetime.now() + timedelta(days=7)
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "share_token": "abc123",
            "created_at": "2024-01-01T00:00:00Z",
            "expires_at": future_time.isoformat(),
            "access_count": 0
        }
        link = ShareLinkInDBBase(**data)
        assert link.expires_at is not None

    def test_share_link_expiration_past(self):
        """Test share link with past expiration (expired link)"""
        past_time = datetime.now() - timedelta(days=1)
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "share_token": "abc123",
            "created_at": "2024-01-01T00:00:00Z",
            "expires_at": past_time.isoformat(),
            "access_count": 100
        }
        link = ShareLinkInDBBase(**data)
        assert link.access_count == 100

    def test_share_link_high_access_count(self):
        """Test share link with high access count"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "share_token": "popular-link",
            "created_at": "2024-01-01T00:00:00Z",
            "expires_at": None,
            "access_count": 999999
        }
        link = ShareLinkInDBBase(**data)
        assert link.access_count == 999999

    def test_shared_transcription_with_unicode(self):
        """Test shared transcription with unicode filename and content"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "テストファイル.mp3",
            "text": "これはテスト転写です",
            "summary": "要約テキスト",
            "language": "ja",
            "duration_seconds": 180.5,
            "created_at": "2024-01-01T00:00:00Z"
        }
        response = SharedTranscriptionResponse(**data)
        assert response.file_name == "テストファイル.mp3"
        assert "テスト転写" in response.text

    def test_shared_transcription_long_text(self):
        """Test shared transcription with very long text"""
        long_text = "This is a long transcription. " * 500  # ~12000 characters
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "long-audio.mp3",
            "text": long_text,
            "summary": None,
            "language": "en",
            "duration_seconds": 3600.0,
            "created_at": "2024-01-01T00:00:00Z"
        }
        response = SharedTranscriptionResponse(**data)
        assert len(response.text) == len(long_text)

    def test_shared_transcription_various_durations(self):
        """Test shared transcription with various duration values"""
        test_durations = [0.5, 10.0, 60.0, 1800.0, 7200.0]
        for duration in test_durations:
            data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "test.mp3",
                "text": "Test",
                "summary": None,
                "language": "en",
                "duration_seconds": duration,
                "created_at": "2024-01-01T00:00:00Z"
            }
            response = SharedTranscriptionResponse(**data)
            assert response.duration_seconds == duration

    def test_share_url_various_formats(self):
        """Test various share URL formats"""
        urls = [
            "https://example.com/share/abc123",
            "https://share.example.com/abc123def456",
            "http://localhost:8000/share/token-123-ABC",
            "https://app.example.com/s/token-456-DEF"
        ]

        for url in urls:
            data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
                "share_token": "token",
                "created_at": "2024-01-01T00:00:00Z",
                "expires_at": None,
                "access_count": 0,
                "share_url": url
            }
            link = ShareLink(**data)
            assert link.share_url == url
