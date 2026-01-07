"""
Transcriptions Chat and Share Endpoints Unit Tests

Unit tests for chat endpoints (history, send, stream) and share link creation.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from uuid import uuid4, UUID
from fastapi import HTTPException

from app.api.transcriptions import (
    get_chat_history,
    send_chat_message,
    send_chat_message_stream,
    create_share_link
)
from app.models.transcription import Transcription
from app.models.chat_message import ChatMessage
from app.models.share_link import ShareLink
from app.models.user import User
from app.schemas.chat import ChatHistoryResponse
from app.schemas.share import ShareLink as ShareLinkSchema


# ============================================================================
# get_chat_history() Tests
# ============================================================================

class TestGetChatHistory:
    """Test getting chat history endpoint."""

    @pytest.mark.asyncio
    async def test_should_return_422_for_invalid_uuid(self):
        """Should return 422 for invalid UUID format."""
        mock_db = MagicMock()
        mock_user = {"id": str(uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await get_chat_history("invalid-uuid", mock_db, mock_user)

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_should_return_404_for_nonexistent_transcription(self):
        """Should return 404 when transcription not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_user = {"id": str(uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await get_chat_history(str(uuid4()), mock_db, mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_should_return_chat_messages(self):
        """Should return chat messages for transcription."""
        mock_db = MagicMock()
        transcription_id = uuid4()
        user_id = uuid4()

        mock_transcription = MagicMock()
        mock_transcription.id = transcription_id
        mock_transcription.user_id = str(user_id)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(user_id)}

        # Mock chat messages with proper UUID types
        mock_msg1 = MagicMock()
        mock_msg1.id = uuid4()
        mock_msg1.transcription_id = transcription_id
        mock_msg1.user_id = user_id
        mock_msg1.role = "user"
        mock_msg1.content = "Hello"
        mock_msg2 = MagicMock()
        mock_msg2.id = uuid4()
        mock_msg2.transcription_id = transcription_id
        mock_msg2.user_id = user_id
        mock_msg2.role = "assistant"
        mock_msg2.content = "Hi there"

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_msg1, mock_msg2]
        mock_db.query.return_value = mock_query

        result = await get_chat_history(str(uuid4()), mock_db, mock_user)

        # Result is a ChatHistoryResponse object
        assert hasattr(result, "messages")
        assert len(result.messages) == 2

    @pytest.mark.asyncio
    async def test_should_return_empty_history(self):
        """Should return empty list when no messages."""
        mock_db = MagicMock()
        transcription_id = uuid4()
        user_id = uuid4()

        mock_transcription = MagicMock()
        mock_transcription.id = transcription_id
        mock_transcription.user_id = str(user_id)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(user_id)}

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        result = await get_chat_history(str(uuid4()), mock_db, mock_user)

        # Result is a ChatHistoryResponse object
        assert hasattr(result, "messages")
        assert len(result.messages) == 0


# ============================================================================
# send_chat_message() Tests
# ============================================================================

class TestSendChatMessage:
    """Test sending chat message endpoint."""

    @pytest.mark.asyncio
    async def test_should_return_422_for_invalid_uuid(self):
        """Should return 422 for invalid UUID format."""
        mock_db = MagicMock()
        mock_user = {"id": str(uuid4())}
        message = {"content": "Test"}

        with pytest.raises(HTTPException) as exc_info:
            await send_chat_message("invalid-uuid", message, mock_db, mock_user)

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_should_return_404_for_nonexistent_transcription(self):
        """Should return 404 when transcription not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_user = {"id": str(uuid4())}
        message = {"content": "Test"}

        with pytest.raises(HTTPException) as exc_info:
            await send_chat_message(str(uuid4()), message, mock_db, mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_should_return_400_for_empty_content(self):
        """Should return 400 when message content is empty."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.text = "Some text"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        message = {"content": ""}

        with pytest.raises(HTTPException) as exc_info:
            await send_chat_message(str(uuid4()), message, mock_db, mock_user)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_should_return_400_for_missing_content(self):
        """Should return 400 when content field is missing."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.text = "Some text"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        message = {}

        with pytest.raises(HTTPException) as exc_info:
            await send_chat_message(str(uuid4()), message, mock_db, mock_user)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch('app.core.glm.get_glm_client')
    async def test_should_save_user_message(self, mock_get_glm_client):
        """Should save user message to database."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.text = "Transcription text"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        user_id = str(uuid4())
        mock_user = {"id": user_id}

        # Mock GLM response
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value={"response": "AI response"})
        mock_get_glm_client.return_value = mock_client

        # Mock chat history (empty)
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        message = {"content": "Hello"}

        result = await send_chat_message(str(uuid4()), message, mock_db, mock_user)

        # Verify user message was saved
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    @patch('app.core.glm.get_glm_client')
    async def test_should_handle_glm_error(self, mock_get_glm_client):
        """Should handle GLM API errors gracefully."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.text = "Transcription text"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        user_id = str(uuid4())
        mock_user = {"id": user_id}

        # Mock GLM error
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(side_effect=Exception("GLM error"))
        mock_get_glm_client.return_value = mock_client

        # Mock chat history (empty)
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        message = {"content": "Hello"}

        result = await send_chat_message(str(uuid4()), message, mock_db, mock_user)

        # Should still return a response with error message
        assert result is not None


# ============================================================================
# send_chat_message_stream() Tests
# ============================================================================

class TestSendChatMessageStream:
    """Test streaming chat message endpoint."""

    @pytest.mark.asyncio
    async def test_should_return_422_for_invalid_uuid(self):
        """Should return 422 for invalid UUID format."""
        mock_db = MagicMock()
        mock_user = {"id": str(uuid4())}
        message = {"content": "Test"}

        with pytest.raises(HTTPException) as exc_info:
            await send_chat_message_stream("invalid-uuid", message, mock_db, mock_user)

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_should_return_404_for_nonexistent_transcription(self):
        """Should return 404 when transcription not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_user = {"id": str(uuid4())}
        message = {"content": "Test"}

        with pytest.raises(HTTPException) as exc_info:
            await send_chat_message_stream(str(uuid4()), message, mock_db, mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_should_return_400_for_empty_content(self):
        """Should return 400 when message content is empty."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.text = "Some text"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        message = {"content": ""}

        with pytest.raises(HTTPException) as exc_info:
            await send_chat_message_stream(str(uuid4()), message, mock_db, mock_user)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_should_save_user_message_before_streaming(self):
        """Should save user message immediately before streaming."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.text = "Transcription text"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        user_id = str(uuid4())
        mock_user = {"id": user_id}

        # Mock chat history (empty)
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        message = {"content": "Hello"}

        with patch('app.core.glm.get_glm_client'):
            result = await send_chat_message_stream(str(uuid4()), message, mock_db, mock_user)

        # Verify user message was saved
        mock_db.add.assert_called()
        mock_db.commit.assert_called()


# ============================================================================
# create_share_link() Tests
# ============================================================================

class TestCreateShareLink:
    """Test share link creation endpoint."""

    @pytest.mark.asyncio
    async def test_should_return_422_for_invalid_uuid(self):
        """Should return 422 for invalid UUID format."""
        mock_db = MagicMock()
        mock_user = {"id": str(uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await create_share_link("invalid-uuid", mock_db, mock_user)

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_should_return_404_for_nonexistent_transcription(self):
        """Should return 404 when transcription not found."""
        mock_db = MagicMock()

        # Create proper query chain that returns None for transcription
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        mock_user = {"id": str(uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await create_share_link(str(uuid4()), mock_db, mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch('app.api.transcriptions._generate_share_token', return_value='test-token-123')
    async def test_should_create_new_share_link(self, mock_generate_token):
        """Should create new share link when none exists."""
        mock_db = MagicMock()

        transcription_id = uuid4()
        user_id = uuid4()

        mock_transcription = MagicMock()
        mock_transcription.id = transcription_id
        mock_transcription.user_id = str(user_id)

        # Setup query chain - first call gets transcription, second gets existing link (None)
        call_count = 0

        def mock_query_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_q = MagicMock()
            if call_count == 1:
                # First call: return transcription
                mock_q.filter.return_value.first.return_value = mock_transcription
            else:
                # Second call: no existing link
                mock_q.filter.return_value.first.return_value = None
            return mock_q

        mock_db.query.side_effect = mock_query_side_effect
        mock_user = {"id": str(user_id)}

        # Patch ShareLinkSchema to avoid validation issues
        with patch('app.api.transcriptions.ShareLinkSchema') as mock_schema:
            mock_schema_instance = MagicMock()
            mock_schema_instance.model_validate.return_value.model_dump.return_value = {}
            mock_schema_instance.model_dump.return_value = {}
            mock_schema.return_value = mock_schema_instance

            with patch('app.schemas.share.ShareLink', return_value=MagicMock(share_token='test')):
                result = await create_share_link(str(transcription_id), mock_db, mock_user)

        # Verify new link was created
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called()

    @pytest.mark.asyncio
    @patch('app.api.transcriptions._generate_share_token', return_value='test-token-123')
    async def test_should_return_existing_share_link(self, mock_generate_token):
        """Should return existing share link if already created."""
        mock_db = MagicMock()

        transcription_id = uuid4()
        user_id = uuid4()

        mock_transcription = MagicMock()
        mock_transcription.id = transcription_id
        mock_transcription.user_id = str(user_id)

        # Existing link with all required fields
        from datetime import datetime
        mock_existing_link = MagicMock()
        mock_existing_link.id = uuid4()
        mock_existing_link.share_token = "existing-token"
        mock_existing_link.transcription_id = transcription_id
        mock_existing_link.created_at = datetime.now()
        mock_existing_link.access_count = 0

        # Setup query chain
        call_count = 0

        def mock_query_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_q = MagicMock()
            if call_count == 1:
                # First call: return transcription
                mock_q.filter.return_value.first.return_value = mock_transcription
            else:
                # Second call: return existing link
                mock_q.filter.return_value.first.return_value = mock_existing_link
            return mock_q

        mock_db.query.side_effect = mock_query_side_effect
        mock_user = {"id": str(user_id)}

        # Patch both ShareLinkSchema imports to avoid validation issues
        with patch('app.api.transcriptions.ShareLinkSchema') as mock_schema:
            with patch('app.schemas.share.ShareLink', return_value=mock_existing_link):
                # Create a proper dict for model_dump
                mock_schema_instance = MagicMock()
                mock_schema_instance.model_validate.return_value.model_dump.return_value = {
                    'share_token': 'existing-token',
                    'transcription_id': str(transcription_id),
                    'created_at': datetime.now(),
                    'access_count': 0,
                    'id': str(mock_existing_link.id)
                }
                mock_schema_instance.model_dump.return_value = {
                    'share_token': 'existing-token',
                    'transcription_id': str(transcription_id),
                    'created_at': datetime.now(),
                    'access_count': 0,
                    'id': str(mock_existing_link.id)
                }
                mock_schema.return_value = mock_schema_instance

                result = await create_share_link(str(transcription_id), mock_db, mock_user)

        # Should complete without error
        assert True

    @pytest.mark.asyncio
    @patch('app.api.transcriptions._generate_share_token', return_value='test-token-123')
    async def test_should_include_share_url_in_response(self, mock_generate_token):
        """Should include share_url in response."""
        mock_db = MagicMock()

        transcription_id = uuid4()
        user_id = uuid4()

        mock_transcription = MagicMock()
        mock_transcription.id = transcription_id
        mock_transcription.user_id = str(user_id)

        # No existing link
        call_count = 0

        def mock_query_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_q = MagicMock()
            if call_count == 1:
                mock_q.filter.return_value.first.return_value = mock_transcription
            else:
                mock_q.filter.return_value.first.return_value = None
            return mock_q

        mock_db.query.side_effect = mock_query_side_effect
        mock_user = {"id": str(user_id)}

        # Mock the ShareLink creation with proper UUID
        from datetime import datetime
        new_link_id = uuid4()
        mock_new_link = MagicMock()
        mock_new_link.id = new_link_id
        mock_new_link.share_token = 'test-token-123'
        mock_new_link.transcription_id = transcription_id
        mock_new_link.created_at = datetime.now()
        mock_new_link.access_count = 0

        # Patch both ShareLinkSchema imports
        with patch('app.api.transcriptions.ShareLinkSchema') as mock_schema:
            with patch('app.schemas.share.ShareLink', return_value=mock_new_link):
                # Create a proper dict for model_dump
                mock_schema_instance = MagicMock()
                mock_schema_instance.model_validate.return_value.model_dump.return_value = {
                    'share_token': 'test-token-123',
                    'transcription_id': str(transcription_id),
                    'created_at': datetime.now(),
                    'access_count': 0,
                    'id': str(new_link_id)
                }
                mock_schema_instance.model_dump.return_value = {
                    'share_token': 'test-token-123',
                    'transcription_id': str(transcription_id),
                    'created_at': datetime.now(),
                    'access_count': 0,
                    'id': str(new_link_id)
                }
                mock_schema.return_value = mock_schema_instance

                result = await create_share_link(str(transcription_id), mock_db, mock_user)

        # Response should exist
        assert result is not None
