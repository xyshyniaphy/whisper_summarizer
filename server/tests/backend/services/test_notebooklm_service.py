"""
NotebookLM Service Tests

Tests for generating NotebookLM presentation guidelines from transcription content.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from openai import OpenAI

from app.services.notebooklm_service import NotebookLMService, get_notebooklm_service, NOTEBOOKLM_SYSTEM_PROMPT


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    mock_client = MagicMock(spec=OpenAI)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "## 幻灯片 1：测试标题\n- 要点1\n- 要点2\n- 要点3"
    mock_response.usage.prompt_tokens = 1000
    mock_response.usage.completion_tokens = 500
    mock_response.usage.total_tokens = 1500
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_transcription_text():
    """Sample transcription text for testing."""
    return """
    这是一个关于佛学讲座的转录文本。
    讲座内容涵盖了佛教的基本教义，包括四圣谛、八正道等重要概念。
    主讲人详细解释了这些概念的含义和实践方法。
    """


# ============================================================================
# NotebookLMService.__init__() Tests
# ============================================================================

class TestNotebookLMServiceInit:
    """Test NotebookLMService initialization."""

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_initialize_with_env_vars(self, mock_getenv, mock_openai_client):
        """Should initialize using environment variables."""
        mock_getenv.side_effect = lambda k, d=None: {
            "GLM_API_KEY": "test-api-key",
            "GLM_BASE_URL": "https://test-api.com"
        }.get(k, d)

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService()

            assert service.api_key == "test-api-key"
            assert service.base_url == "https://test-api.com"
            assert service.model == "GLM-4.5-Air"

    def test_should_initialize_with_params(self, mock_openai_client):
        """Should initialize with provided parameters."""
        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService(
                api_key="custom-key",
                base_url="https://custom-url.com",
                model="custom-model"
            )

            assert service.api_key == "custom-key"
            assert service.base_url == "https://custom-url.com"
            assert service.model == "custom-model"

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_raise_error_when_no_api_key(self, mock_getenv):
        """Should raise ValueError when API key is not configured."""
        mock_getenv.return_value = None

        with pytest.raises(ValueError, match="GLM_API_KEY is not configured"):
            NotebookLMService()


# ============================================================================
# NotebookLMService._load_spec_prompt() Tests
# ============================================================================

class TestLoadSpecPrompt:
    """Test loading the spec prompt."""

    def test_should_return_hardcoded_prompt(self, mock_openai_client):
        """Should return the hardcoded NotebookLM system prompt."""
        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService(api_key="test-key")
            prompt = service._load_spec_prompt()

            assert prompt == NOTEBOOKLM_SYSTEM_PROMPT
            assert "角色设定" in prompt
            assert "佛学内容整理专家" in prompt


# ============================================================================
# NotebookLMService.generate_guideline() Tests
# ============================================================================

class TestGenerateGuideline:
    """Test guideline generation."""

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_generate_guideline_successfully(self, mock_getenv, mock_openai_client, sample_transcription_text):
        """Should generate guideline from transcription text."""
        mock_getenv.side_effect = lambda k, d=None: {
            "GLM_API_KEY": "test-api-key",
            "GLM_BASE_URL": "https://test-api.com"
        }.get(k, d)

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService()
            guideline = service.generate_guideline(sample_transcription_text, file_name="test.txt")

            assert guideline is not None
            assert "## 幻灯片 1" in guideline
            assert "要点1" in guideline

            # Verify API was called correctly
            mock_openai_client.chat.completions.create.assert_called_once()
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args[1]['model'] == "GLM-4.5-Air"
            assert len(call_args[1]['messages']) == 2

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_raise_error_for_short_text(self, mock_getenv, mock_openai_client):
        """Should raise ValueError for transcription text that's too short."""
        mock_getenv.side_effect = lambda k, d=None: "test-api-key"

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService()

            with pytest.raises(ValueError, match="Transcription text is too short"):
                service.generate_guideline("短文本")

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_raise_error_for_empty_text(self, mock_getenv, mock_openai_client):
        """Should raise ValueError for empty transcription text."""
        mock_getenv.side_effect = lambda k, d=None: "test-api-key"

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService()

            with pytest.raises(ValueError, match="Transcription text is too short"):
                service.generate_guideline("")

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_truncate_long_text(self, mock_getenv, mock_openai_client, caplog):
        """Should truncate transcription text if too long (max 15000 chars)."""
        mock_getenv.side_effect = lambda k, d=None: "test-api-key"

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService()

            # Create text longer than 15000 chars
            # Need to ensure we exceed the 15000 character limit
            base_text = "测试内容这是一个较长的中文字符串用于测试截断功能。"  # 25 chars
            long_text = base_text * 650  # 25 * 650 = 16250 chars - exceeds 15000 limit!

            import logging
            with caplog.at_level(logging.INFO):
                service.generate_guideline(long_text, file_name="long.txt")

            # Check that truncation was logged
            assert any("truncated" in record.message.lower() for record in caplog.records)

            # Check that text was truncated
            call_args = mock_openai_client.chat.completions.create.call_args
            user_message = call_args[1]['messages'][1]['content']
            assert len(user_message) < len(long_text)  # Should be truncated

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_handle_api_errors(self, mock_getenv, mock_openai_client):
        """Should handle API errors gracefully."""
        mock_getenv.side_effect = lambda k, d=None: "test-api-key"

        # Mock API to raise an error
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService()

            # Need at least 50 characters
            long_text = "这是一个足够长的转录文本内容，用于测试错误处理。这是更多的文本确保长度超过50个字符。" * 2

            with pytest.raises(Exception, match="Guideline generation failed"):
                service.generate_guideline(long_text, file_name="error.txt")

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_log_token_usage(self, mock_getenv, mock_openai_client, sample_transcription_text, caplog):
        """Should log token usage information."""
        mock_getenv.side_effect = lambda k, d=None: "test-api-key"

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService()

            import logging
            with caplog.at_level(logging.INFO):
                service.generate_guideline(sample_transcription_text, file_name="test.txt")

            # Check that token usage was logged
            assert any("1500" in record.message for record in caplog.records)

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_use_custom_model(self, mock_getenv, mock_openai_client):
        """Should use custom model if specified."""
        mock_getenv.side_effect = lambda k, d=None: "test-api-key"

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService(model="custom-model-name")

            # Need at least 50 characters - use a much longer string
            long_text = "这是一个足够长的转录文本内容，包含了足够的字符数量来通过验证。" * 2

            service.generate_guideline(long_text, file_name="test.txt")

            # Verify custom model was used
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args[1]['model'] == "custom-model-name"


# ============================================================================
# get_notebooklm_service() Tests
# ============================================================================

class TestGetNotebookLMService:
    """Test singleton pattern for NotebookLMService."""

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_return_singleton_instance(self, mock_getenv, mock_openai_client):
        """Should return the same instance on multiple calls."""
        mock_getenv.side_effect = lambda k, d=None: "test-api-key"

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            # Reset singleton
            import app.services.notebooklm_service as nb_service
            nb_service._notebooklm_service = None

            service1 = get_notebooklm_service()
            service2 = get_notebooklm_service()

            assert service1 is service2

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_initialize_once(self, mock_getenv, mock_openai_client):
        """Should initialize the service only once."""
        mock_getenv.side_effect = lambda k, d=None: "test-api-key"

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client) as mock_openai:
            # Reset singleton
            import app.services.notebooklm_service as nb_service
            nb_service._notebooklm_service = None

            # Call multiple times
            get_notebooklm_service()
            get_notebooklm_service()
            get_notebooklm_service()

            # OpenAI should only be initialized once
            assert mock_openai.call_count == 1


# ============================================================================
# Edge Cases
# ============================================================================

class TestNotebookLMEdgeCases:
    """Test edge cases and error handling."""

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_handle_whitespace_only_text(self, mock_getenv, mock_openai_client):
        """Should reject text that's only whitespace."""
        mock_getenv.side_effect = lambda k, d=None: "test-api-key"

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService()

            with pytest.raises(ValueError, match="Transcription text is too short"):
                service.generate_guideline("   \n\n   \t   ")

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_handle_exactly_50_chars(self, mock_getenv, mock_openai_client):
        """Should accept text that's exactly 50 characters."""
        mock_getenv.side_effect = lambda k, d=None: "test-api-key"

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService()

            # Text exactly 50 characters
            text = "a" * 50

            # Should not raise an error
            guideline = service.generate_guideline(text)
            assert guideline is not None

    @patch('app.services.notebooklm_service.os.getenv')
    def test_should_handle_response_without_usage(self, mock_getenv, mock_openai_client):
        """Should handle response without token usage information."""
        mock_getenv.side_effect = lambda k, d=None: "test-api-key"

        # Mock response without usage info
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated guideline"
        mock_response.usage = None
        mock_openai_client.chat.completions.create.return_value = mock_response

        with patch('app.services.notebooklm_service.OpenAI', return_value=mock_openai_client):
            service = NotebookLMService()

            # Need at least 50 characters
            long_text = "这是一个足够长的转录文本内容用于测试。" * 3

            # Should not crash even without usage info
            guideline = service.generate_guideline(long_text)
            assert guideline == "Generated guideline"
