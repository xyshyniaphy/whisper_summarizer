"""
GLM Chat Method Tests

Tests for the GLM client chat functionality.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from openai import OpenAI

from app.core.glm import GLMClient


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_chat_response():
    """Mock chat API response."""
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = "This is the chat response."
    choice.finish_reason = "stop"
    response.choices = [choice]
    response.usage.prompt_tokens = 50
    response.usage.completion_tokens = 30
    response.usage.total_tokens = 80
    response.model = "GLM-4.5-Air"
    return response


@pytest.fixture
def mock_chat_history():
    """Mock chat history."""
    return [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "Second question"},
        {"role": "assistant", "content": "Second answer"},
    ]


# ============================================================================
# chat() Method Tests
# ============================================================================

class TestGLMChatMethod:
    """Test GLMClient chat method."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_chat_with_transcription_context(self, mock_chat_response):
        """Should chat with transcription context successfully."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        result = await client.chat(
            question="What is this about?",
            transcription_context="This is a test transcription."
        )

        assert result["response"] == "This is the chat response."
        assert result["input_tokens"] == 50
        assert result["output_tokens"] == 30
        assert result["total_tokens"] == 80

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_include_chat_history(self, mock_chat_response, mock_chat_history):
        """Should include chat history in the request."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        result = await client.chat(
            question="What is this about?",
            transcription_context="Test transcription",
            chat_history=mock_chat_history
        )

        # Verify the chat history was included
        call_args = client.client.chat.completions.create.call_args
        messages = call_args[1]['messages']

        # Should have system prompt + chat history + current question
        assert len(messages) >= 3  # At least system + last user message + current question

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_limit_chat_history_to_10_items(self, mock_chat_response):
        """Should limit chat history to last 10 items (plus current message = 11 max)."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        # Create 15 message history
        long_history = []
        for i in range(15):
            long_history.append({"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"})

        result = await client.chat(
            question="Latest question?",
            transcription_context="Test",
            chat_history=long_history
        )

        call_args = client.client.chat.completions.create.call_args
        messages = call_args[1]['messages']

        # Should limit to last 10 from history + current question = 11
        user_assistant_messages = [m for m in messages if m["role"] in ["user", "assistant"]]
        assert len(user_assistant_messages) == 11

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_filter_invalid_chat_history_roles(self, mock_chat_response):
        """Should filter out messages with invalid roles."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        # Include invalid roles
        mixed_history = [
            {"role": "user", "content": "Valid user message"},
            {"role": "system", "content": "Invalid system message"},  # Should be filtered
            {"role": "assistant", "content": "Valid assistant message"},
            {"role": "invalid", "content": "Invalid role message"},  # Should be filtered
        ]

        result = await client.chat(
            question="Question?",
            transcription_context="Test",
            chat_history=mixed_history
        )

        call_args = client.client.chat.completions.create.call_args
        messages = call_args[1]['messages']

        # Should only have user and assistant messages from history (2) + current question (1)
        # System prompt is always first
        user_assistant_messages = [m for m in messages[1:] if m["role"] in ["user", "assistant"]]
        assert len(user_assistant_messages) == 3  # 2 from history + 1 current

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_chat_api_error(self):
        """Should handle chat API errors by raising exception."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(
            side_effect=Exception("Chat API error")
        )

        with pytest.raises(Exception, match="Chat error"):
            await client.chat(
                question="Test question",
                transcription_context="Test context"
            )

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_return_response_with_all_fields(self, mock_chat_response):
        """Should return response with all required fields."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        result = await client.chat(
            question="Test question",
            transcription_context="Test context"
        )

        assert "response" in result
        assert "input_tokens" in result
        assert "output_tokens" in result
        assert "total_tokens" in result
        assert "response_time_ms" in result

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_use_chat_system_prompt(self, mock_chat_response):
        """Should use chat-specific system prompt."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        result = await client.chat(
            question="Test question",
            transcription_context="Test transcription"
        )

        call_args = client.client.chat.completions.create.call_args
        messages = call_args[1]['messages']

        # First message should be system prompt
        assert messages[0]["role"] == "system"
        assert len(messages[0]["content"]) > 0

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_include_transcription_context(self, mock_chat_response):
        """Should include transcription context in user message."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        result = await client.chat(
            question="What is discussed?",
            transcription_context="The meeting discusses project updates."
        )

        call_args = client.client.chat.completions.create.call_args
        messages = call_args[1]['messages']

        # Last message should contain context
        last_message = messages[-1]
        assert "The meeting discusses project updates" in last_message["content"]
        assert "What is discussed?" in last_message["content"]


# ============================================================================
# Chat System Prompt Tests
# ============================================================================

class TestChatSystemPrompt:
    """Test chat system prompt generation."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_generate_chinese_chat_prompt(self, mock_chat_response):
        """Should generate Chinese system prompt for chat."""
        client = GLMClient(review_language="zh")
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        await client.chat("问题", "转录内容")

        call_args = client.client.chat.completions.create.call_args
        system_prompt = call_args[1]['messages'][0]['content']

        # Should contain chat-related instructions
        assert len(system_prompt) > 0

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_generate_english_chat_prompt(self, mock_chat_response):
        """Should generate English system prompt for chat."""
        client = GLMClient(review_language="en")
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        await client.chat("Question", "Transcription")

        call_args = client.client.chat.completions.create.call_args
        system_prompt = call_args[1]['messages'][0]['content']

        assert len(system_prompt) > 0


# ============================================================================
# Chat Edge Cases
# ============================================================================

class TestChatEdgeCases:
    """Test chat edge cases."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_empty_chat_history(self, mock_chat_response):
        """Should handle empty chat history."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        result = await client.chat(
            question="Question",
            transcription_context="Context",
            chat_history=[]
        )

        # Should have system prompt + current question
        assert result is not None

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_none_chat_history(self, mock_chat_response):
        """Should handle None chat history."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        result = await client.chat(
            question="Question",
            transcription_context="Context",
            chat_history=None
        )

        # Should have system prompt + current question only
        call_args = client.client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        assert len(messages) == 2  # system + current question

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_empty_question(self, mock_chat_response):
        """Should handle empty question."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        result = await client.chat(
            question="",
            transcription_context="Context"
        )

        # Should still attempt API call
        assert client.client.chat.completions.create.called

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_long_question(self, mock_chat_response):
        """Should handle long question text."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        long_question = "Question " * 1000
        result = await client.chat(
            question=long_question,
            transcription_context="Context"
        )

        assert result is not None

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_long_transcription_context(self, mock_chat_response):
        """Should handle long transcription context."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        long_context = "Word " * 10000
        result = await client.chat(
            question="What is this about?",
            transcription_context=long_context
        )

        assert result is not None

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_unicode_in_chat(self, mock_chat_response):
        """Should handle unicode characters in chat."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        result = await client.chat(
            question="这是问题？",
            transcription_context="这是转录内容"
        )

        assert result is not None


# ============================================================================
# Chat Temperature and Parameters
# ============================================================================

class TestChatParameters:
    """Test chat parameter handling."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_use_correct_temperature_for_chat(self, mock_chat_response):
        """Should use correct temperature for chat."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        await client.chat("Question", "Context")

        call_args = client.client.chat.completions.create.call_args
        assert call_args[1]['temperature'] == 0.7

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_set_max_tokens_for_chat(self, mock_chat_response):
        """Should set max_tokens for chat."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        await client.chat("Question", "Context")

        call_args = client.client.chat.completions.create.call_args
        assert call_args[1]['max_tokens'] == 2000

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_use_correct_model_for_chat(self, mock_chat_response):
        """Should use correct model for chat."""
        client = GLMClient(model="custom-model")
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        await client.chat("Question", "Context")

        call_args = client.client.chat.completions.create.call_args
        assert call_args[1]['model'] == "custom-model"


# ============================================================================
# Chat Response Structure Tests
# ============================================================================

class TestChatResponseStructure:
    """Test chat response structure."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_track_response_time_for_chat(self, mock_chat_response):
        """Should track response time for chat."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        result = await client.chat("Question", "Context")

        assert result["response_time_ms"] >= 0


# ============================================================================
# Chat Error Messages
# ============================================================================

class TestChatErrorMessages:
    """Test chat error message handling."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_wrap_error_message_on_failure(self):
        """Should wrap error message when chat fails."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(
            side_effect=ConnectionError("Network error")
        )

        with pytest.raises(Exception, match="Chat error: Network error"):
            await client.chat("Question", "Context")

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_timeout_error(self):
        """Should handle timeout errors."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(
            side_effect=TimeoutError("Request timeout")
        )

        with pytest.raises(Exception, match="Chat error: Request timeout"):
            await client.chat("Question", "Context")

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_value_error(self):
        """Should handle value errors."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(
            side_effect=ValueError("Invalid parameter")
        )

        with pytest.raises(Exception, match="Chat error: Invalid parameter"):
            await client.chat("Question", "Context")


# ============================================================================
# Chat Message Formatting
# ============================================================================

class TestChatMessageFormatting:
    """Test chat message formatting."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_format_context_message_correctly(self, mock_chat_response):
        """Should format context message correctly."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        await client.chat(
            question="What was discussed?",
            transcription_context="Meeting about Q4 goals."
        )

        call_args = client.client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        last_message = messages[-1]

        # Should contain both context and question
        assert "Meeting about Q4 goals" in last_message["content"]
        assert "What was discussed?" in last_message["content"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_preserve_chat_history_order(self, mock_chat_response):
        """Should preserve chat history order."""
        client = GLMClient()
        client.client.chat.completions.create = MagicMock(return_value=mock_chat_response)

        chat_history = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"},
        ]

        await client.chat("Question", "Context", chat_history)

        call_args = client.client.chat.completions.create.call_args
        messages = call_args[1]['messages']

        # Find user messages from history (excluding system prompt and current message)
        # The last message is the current question
        for i, msg in enumerate(messages[1:-1]):  # Skip system prompt and last message
            if i < len(chat_history):
                expected = chat_history[i]
                if msg["role"] == expected["role"]:
                    assert expected["content"] in msg["content"]
