"""
GLM Service Tests

Tests for the GLM API client service.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from openai import OpenAI

from app.core.glm import GLMClient


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    with patch('app.core.glm.OpenAI') as mock:
        yield mock


@pytest.fixture
def mock_response():
    """Mock API response."""
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = "This is a summary of the transcription."
    choice.finish_reason = "stop"
    response.choices = [choice]
    response.usage.prompt_tokens = 100
    response.usage.completion_tokens = 50
    response.usage.total_tokens = 150
    return response


# ============================================================================
# GLMClient.__init__() Tests
# ============================================================================

class TestGLMClientInit:
    """Test GLMClient initialization."""

    @patch.dict(os.environ, {"GLM_API_KEY": "test-key", "GLM_BASE_URL": "https://test.api"})
    def test_should_initialize_with_env_vars(self):
        """Should initialize with environment variables."""
        client = GLMClient(api_key="test-key")

        assert client.api_key == "test-key"
        assert client.base_url == "https://test.api"

    def test_should_initialize_with_params(self):
        """Should initialize with provided parameters."""
        client = GLMClient(
            api_key="custom-key",
            base_url="https://custom.api",
            model="custom-model",
            review_language="en"
        )

        assert client.api_key == "custom-key"
        assert client.base_url == "https://custom.api"
        assert client.model == "custom-model"
        assert client.review_language == "en"

    @patch.dict(os.environ, {}, clear=True)
    def test_should_raise_error_without_api_key(self):
        """Should raise ValueError when no API key provided."""
        with pytest.raises(ValueError, match="GLM_API_KEY"):
            GLMClient()

    @patch('app.core.glm.OpenAI')
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    def test_should_initialize_openai_client(self, mock_openai):
        """Should initialize OpenAI client."""
        GLMClient()

        mock_openai.assert_called_once()


# ============================================================================
# _get_system_prompt_by_language() Tests
# ============================================================================

class TestGetSystemPrompt:
    """Test system prompt generation."""

    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    def test_should_generate_chinese_prompt(self):
        """Should generate Chinese system prompt."""
        client = GLMClient(review_language="zh")
        prompt = client._get_system_prompt_by_language()

        assert "总结" in prompt or "助手" in prompt

    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    def test_should_generate_japanese_prompt(self):
        """Should generate Japanese system prompt."""
        client = GLMClient(review_language="ja")
        prompt = client._get_system_prompt_by_language()

        assert "要約" in prompt or "要約" in prompt or "助手" in prompt

    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    def test_should_generate_english_prompt(self):
        """Should generate English system prompt."""
        client = GLMClient(review_language="en")
        prompt = client._get_system_prompt_by_language()

        assert "summary" in prompt.lower() or "summarize" in prompt.lower()


# ============================================================================
# generate_summary() Tests
# ============================================================================

class TestGenerateSummary:
    """Test summary generation."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_generate_summary_successfully(self, mock_response):
        """Should generate summary successfully."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        result = await client.generate_summary("Test transcription text")

        assert result.summary == "This is a summary of the transcription."
        assert result.status == "success"
        assert result.model_name == "GLM-4.5-Air"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_use_custom_system_prompt(self, mock_response):
        """Should use custom system prompt when provided."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        custom_prompt = "Custom system prompt"
        await client.generate_summary("Test text", system_prompt=custom_prompt)

        call_args = client.client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        assert messages[0]['content'] == custom_prompt

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_include_file_name_in_request(self, mock_response):
        """Should include file name in request."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        await client.generate_summary("Test text", file_name="test_audio.wav")

        assert client.client.chat.completions.create.called

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_api_error(self):
        """Should handle API errors gracefully."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(
            side_effect=Exception("API error")
        )

        # Should return error response instead of raising
        result = await client.generate_summary("Test text")

        assert result.status == "error"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_track_response_time(self, mock_response):
        """Should track response time."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        result = await client.generate_summary("Test text")

        assert result.response_time_ms > 0

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_track_token_usage(self, mock_response):
        """Should track token usage."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        result = await client.generate_summary("Test text")

        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.total_tokens == 150

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_return_error_status_on_failure(self):
        """Should return error status on API failure."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(
            side_effect=Exception("Connection failed")
        )

        # Should return error response instead of raising
        result = await client.generate_summary("Test text")

        assert result.status == "error"


# ============================================================================
# Temperature and Parameters Tests
# ============================================================================

class TestGenerationParameters:
    """Test generation parameter handling."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_use_correct_temperature(self, mock_response):
        """Should use correct temperature parameter."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        await client.generate_summary("Test text")

        call_args = client.client.chat.completions.create.call_args
        assert call_args[1]['temperature'] == 0.7

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_set_max_tokens(self, mock_response):
        """Should set max_tokens parameter."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        await client.generate_summary("Test text")

        call_args = client.client.chat.completions.create.call_args
        assert call_args[1]['max_tokens'] == 2000


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_empty_transcription(self, mock_response):
        """Should handle empty transcription text."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        result = await client.generate_summary("")

        # Should still attempt to generate
        assert client.client.chat.completions.create.called

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_handle_long_transcription(self, mock_response):
        """Should handle very long transcription text."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        long_text = "Word " * 10000
        result = await client.generate_summary(long_text)

        assert client.client.chat.completions.create.called


# ============================================================================
# Response Object Tests
# ============================================================================

class TestResponseObject:
    """Test response object structure."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_return_response_with_all_fields(self, mock_response):
        """Should return response with all required fields."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        result = await client.generate_summary("Test text", file_name="test.wav")

        assert hasattr(result, 'summary')
        assert hasattr(result, 'status')
        assert hasattr(result, 'model_name')
        assert hasattr(result, 'input_text_length')
        assert hasattr(result, 'output_text_length')
        assert hasattr(result, 'response_time_ms')

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    async def test_should_include_prompt_in_response(self, mock_response):
        """Should include system prompt in response."""
        client = GLMClient(api_key="test-key")
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        result = await client.generate_summary("Test text")

        assert result.prompt is not None
        assert len(result.prompt) > 0
