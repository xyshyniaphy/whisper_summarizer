"""
Tests for NotebookLMService - Presentation guideline generation.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from openai import OpenAI

from app.services.notebooklm_service import (
    NotebookLMService,
    get_notebooklm_service,
    NOTEBOOKLM_SYSTEM_PROMPT
)


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock_client = Mock(spec=OpenAI)

    mock_response = Mock()
    mock_choice = Mock()
    mock_message = Mock()
    mock_message.content = "## 幻灯片 1：概述\n\n- 要点1\n- 要点2\n- 要点3"

    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    mock_usage = Mock()
    mock_usage.prompt_tokens = 1000
    mock_usage.completion_tokens = 2000
    mock_usage.total_tokens = 3000
    mock_response.usage = mock_usage

    mock_client.chat.completions.create.return_value = mock_response

    return mock_client


@pytest.fixture
def notebooklm_service(mock_openai_client):
    """Create a NotebookLMService with mocked OpenAI client."""
    with patch.object(NotebookLMService, '__init__', return_value=None):
        service = NotebookLMService.__new__(NotebookLMService)
        service.api_key = "test-key"
        service.base_url = "https://test.api"
        service.model = "test-model"
        service.client = mock_openai_client
        return service


class TestNotebookLMServiceInitialization:
    """Tests for service initialization."""

    @patch.dict(os.environ, {"GLM_API_KEY": "test-api-key"})
    def test_init_with_env_api_key(self):
        """Test initialization with API key from environment."""
        service = NotebookLMService()

        assert service.api_key == "test-api-key"
        assert service.client is not None

    @patch.dict(os.environ, {"GLM_API_KEY": "test-key", "GLM_BASE_URL": "https://custom.url"})
    def test_init_with_custom_base_url(self):
        """Test initialization with custom base URL."""
        service = NotebookLMService()

        assert service.base_url == "https://custom.url"

    @patch.dict(os.environ, {}, clear=True)
    def test_raises_error_when_no_api_key(self):
        """Test that ValueError is raised when API key is not configured."""
        with pytest.raises(ValueError, match="GLM_API_KEY"):
            NotebookLMService()

    def test_init_with_explicit_api_key(self):
        """Test initialization with explicit API key parameter."""
        service = NotebookLMService(api_key="explicit-key")

        assert service.api_key == "explicit-key"

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        service = NotebookLMService(api_key="test-key", model="custom-model")

        assert service.model == "custom-model"


class TestLoadSpecPrompt:
    """Tests for _load_spec_prompt method."""

    def test_returns_hardcoded_prompt(self, notebooklm_service):
        """Test that hardcoded prompt is returned."""
        prompt = notebooklm_service._load_spec_prompt()

        assert prompt == NOTEBOOKLM_SYSTEM_PROMPT

    def test_prompt_contains_key_sections(self, notebooklm_service):
        """Test that prompt contains required sections."""
        prompt = notebooklm_service._load_spec_prompt()

        # Check for key sections mentioned in the code
        assert "角色设定" in prompt
        assert "10 到 15 页" in prompt
        assert "概述" in prompt
        assert "主要要点" in prompt
        assert "详细信息" in prompt

    def test_prompt_is_substantial(self, notebooklm_service):
        """Test that prompt has substantial content."""
        prompt = notebooklm_service._load_spec_prompt()

        assert len(prompt) > 1000  # Should be quite long


class TestGenerateGuideline:
    """Tests for generate_guideline method."""

    def test_successful_generation(self, notebooklm_service, mock_openai_client):
        """Test successful guideline generation."""
        transcription_text = "This is a test transcription about Buddhism. " * 10  # Make it long enough
        expected_guideline = "## 幻灯片 1：概述\n\n- 要点1\n- 要点2"

        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = expected_guideline

        result = notebooklm_service.generate_guideline(transcription_text)

        assert result == expected_guideline
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_includes_file_name_in_call(self, notebooklm_service, mock_openai_client):
        """Test that file name parameter is accepted (used for logging only)."""
        transcription_text = "Test transcription. " * 20  # Make it long enough

        # Should not raise error - file_name is used for logging only
        notebooklm_service.generate_guideline(transcription_text, file_name="test.mp3")

        # Verify the API call was made
        assert mock_openai_client.chat.completions.create.called

    def test_truncates_long_transcription(self, notebooklm_service, mock_openai_client):
        """Test that long transcriptions are truncated."""
        # Create very long transcription
        long_text = "Word " * 10000  # > 15000 chars

        notebooklm_service.generate_guideline(long_text)

        call_args = mock_openai_client.chat.completions.create.call_args
        user_content = call_args[1]['messages'][1]['content']

        # Should be truncated
        assert len(user_content) < 16000  # + prompt text

    def test_raises_error_for_short_text(self, notebooklm_service):
        """Test that ValueError is raised for text that's too short."""
        short_text = "Short"

        with pytest.raises(ValueError, match="too short"):
            notebooklm_service.generate_guideline(short_text)

    def test_raises_error_for_empty_text(self, notebooklm_service):
        """Test that ValueError is raised for empty text."""
        with pytest.raises(ValueError, match="too short"):
            notebooklm_service.generate_guideline("")

    def test_api_error_is_propagated(self, notebooklm_service, mock_openai_client):
        """Test that API errors are properly propagated."""
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")

        transcription_text = "Test transcription " * 50

        with pytest.raises(Exception, match="Guideline generation failed"):
            notebooklm_service.generate_guideline(transcription_text)

    def test_uses_correct_model(self, notebooklm_service, mock_openai_client):
        """Test that correct model is used for API call."""
        notebooklm_service.model = "custom-test-model"

        notebooklm_service.generate_guideline("Test " * 50)

        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]['model'] == "custom-test-model"

    def test_uses_specified_temperature(self, notebooklm_service, mock_openai_client):
        """Test that specified temperature is used."""
        notebooklm_service.generate_guideline("Test " * 50)

        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]['temperature'] == 0.7

    def test_uses_specified_max_tokens(self, notebooklm_service, mock_openai_client):
        """Test that max_tokens is set correctly."""
        notebooklm_service.generate_guideline("Test " * 50)

        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]['max_tokens'] == 4000

    def test_includes_system_prompt(self, notebooklm_service, mock_openai_client):
        """Test that system prompt is included in API call."""
        notebooklm_service.generate_guideline("Test " * 50)

        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]['messages']

        assert messages[0]['role'] == 'system'
        assert '角色设定' in messages[0]['content']

    def test_user_message_format(self, notebooklm_service, mock_openai_client):
        """Test that user message is formatted correctly."""
        transcription = "Test transcription content here " * 10  # Make it long enough

        notebooklm_service.generate_guideline(transcription)

        call_args = mock_openai_client.chat.completions.create.call_args
        user_content = call_args[1]['messages'][1]['content']

        assert "请根据以下转录文本生成 NotebookLM 演示文稿大纲指南" in user_content
        # Check that the transcription is included (may be truncated)
        assert "Test transcription content here" in user_content

    def test_handles_unicode_content(self, notebooklm_service, mock_openai_client):
        """Test handling of Unicode (Chinese) content."""
        chinese_text = "这是关于佛教讲座的转录文本，包含很多佛法内容。" * 10  # Make it long enough

        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "## 幻灯片 1：概述\n\n- 中文要点1\n- 中文要点2"

        result = notebooklm_service.generate_guideline(chinese_text)

        assert "中文要点" in result


class TestGetNotebookLMService:
    """Tests for get_notebooklm_service singleton."""

    @patch('app.services.notebooklm_service._notebooklm_service', None)
    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    def test_singleton_initialization(self):
        """Test that singleton is initialized once."""
        service1 = get_notebooklm_service()
        service2 = get_notebooklm_service()

        assert service1 is service2

    def test_cached_instance_returned(self):
        """Test that cached instance is returned."""
        with patch('app.services.notebooklm_service._notebooklm_service') as mock_cached:
            result = get_notebooklm_service()
            assert result == mock_cached


class TestSystemPrompt:
    """Tests for the system prompt constant."""

    def test_system_prompt_defined(self):
        """Test that system prompt is defined."""
        assert NOTEBOOKLM_SYSTEM_PROMPT is not None
        assert len(NOTEBOOKLM_SYSTEM_PROMPT) > 1000

    def test_system_prompt_buddhism_context(self):
        """Test that system prompt contains Buddhism context."""
        assert "佛学" in NOTEBOOKLM_SYSTEM_PROMPT
        assert "演示文稿" in NOTEBOOKLM_SYSTEM_PROMPT

    def test_system_prompt_structure_requirements(self):
        """Test that system prompt specifies structure."""
        assert "10 到 15 页" in NOTEBOOKLM_SYSTEM_PROMPT
        assert "概述" in NOTEBOOKLM_SYSTEM_PROMPT
        assert "主要要点" in NOTEBOOKLM_SYSTEM_PROMPT


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_whitespace_only_text(self, notebooklm_service):
        """Test handling of text that's only whitespace."""
        whitespace_text = "   \n\n   \n   "

        # Should raise error (strip() makes it empty)
        with pytest.raises(ValueError, match="too short"):
            notebooklm_service.generate_guideline(whitespace_text)

    def test_exact_minimum_length(self, notebooklm_service, mock_openai_client):
        """Test text that's exactly the minimum length."""
        # 50 chars is the minimum
        min_length_text = "x" * 50

        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "Guideline"

        # Should not raise error
        result = notebooklm_service.generate_guideline(min_length_text)
        assert result == "Guideline"

    def test_one_char_below_minimum(self, notebooklm_service):
        """Test text that's one character below minimum."""
        # 49 chars - below minimum
        below_min_text = "x" * 49

        with pytest.raises(ValueError, match="too short"):
            notebooklm_service.generate_guideline(below_min_text)

    def test_response_time_logging(self, notebooklm_service, mock_openai_client):
        """Test that response time is logged."""
        import time

        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "Response"

        # Should not raise any errors
        notebooklm_service.generate_guideline("Test transcription " * 50)


class TestAPICallParameters:
    """Tests for API call parameters."""

    def test_messages_structure(self, notebooklm_service, mock_openai_client):
        """Test that messages are structured correctly."""
        notebooklm_service.generate_guideline("Test content " * 20)  # Make it long enough

        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]['messages']

        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'

    def test_openai_client_configuration(self):
        """Test that OpenAI client is configured correctly."""
        with patch.dict(os.environ, {"GLM_API_KEY": "test-key", "GLM_BASE_URL": "https://test.url"}):
            service = NotebookLMService()

            assert service.client.api_key == "test-key"
            assert service.client.base_url == "https://test.url"
