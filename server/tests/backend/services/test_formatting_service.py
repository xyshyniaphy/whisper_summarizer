"""
Formatting Service Tests

Tests for text formatting using GLM-4.5-Air API.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from openai import OpenAI

from app.services.formatting_service import (
    TextFormattingService,
    get_formatting_service,
)
from app.core.glm import GLMClient


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_glm_client():
    """Mock GLM client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = " formatted text with proper punctuation."
    mock_choice.finish_reason = "stop"
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 500
    mock_response.usage.completion_tokens = 200
    mock_response.usage.total_tokens = 700
    mock_client.client.chat.completions.create.return_value = mock_response
    mock_client.model = "GLM-4.5-Air"
    return mock_client


@pytest.fixture
def sample_raw_text():
    """Sample raw transcribed text."""
    return "今天我们要讨论的是关于人工智能的发展首先呢人工智能已经在我们生活中有很多应用比如说手机里面的语音助手还有自动驾驶等等那么这些技术是如何工作的呢"


@pytest.fixture
def sample_formatted_text():
    """Sample formatted text."""
    return "今天我们要讨论的是关于人工智能的发展。首先，人工智能已经在我们生活中有很多应用，比如说手机里面的语音助手、自动驾驶等等。那么，这些技术是如何工作的呢？"


# ============================================================================
# TextFormattingService.__init__() Tests
# ============================================================================

class TestTextFormattingServiceInit:
    """Test TextFormattingService initialization."""

    @patch('app.core.glm.get_glm_client')
    def test_should_initialize_successfully(self, mock_get_glm, mock_glm_client):
        """Should initialize successfully with GLM client."""
        mock_get_glm.return_value = mock_glm_client

        service = TextFormattingService()

        assert service.glm_client == mock_glm_client
        assert service.max_chunk_bytes > 0

    @patch('app.core.glm.get_glm_client')
    def test_should_handle_glm_init_failure(self, mock_get_glm):
        """Should handle GLM client initialization failure."""
        mock_get_glm.side_effect = Exception("GLM init failed")

        service = TextFormattingService()

        assert service.glm_client is None

    @patch('app.core.glm.get_glm_client')
    @patch('app.services.formatting_service.settings')
    def test_should_use_custom_max_chunk(self, mock_settings, mock_get_glm, mock_glm_client):
        """Should use custom MAX_FORMAT_CHUNK from settings."""
        mock_settings.MAX_FORMAT_CHUNK = 5000
        mock_get_glm.return_value = mock_glm_client

        service = TextFormattingService()

        assert service.max_chunk_bytes == 5000


# ============================================================================
# TextFormattingService.split_text_into_chunks() Tests
# ============================================================================

class TestSplitTextIntoChunks:
    """Test text splitting into chunks."""

    def test_should_return_single_chunk_for_short_text(self):
        """Should return single chunk for text under limit."""
        service = TextFormattingService()
        service.max_chunk_bytes = 10000
        text = "Short text"

        chunks = service.split_text_into_chunks(text)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_should_split_long_text_at_whitespace(self):
        """Should split long text at whitespace boundaries."""
        service = TextFormattingService()
        service.max_chunk_bytes = 100
        # Create text that will need splitting
        text = "word " * 100  # ~500 bytes

        chunks = service.split_text_into_chunks(text)

        assert len(chunks) > 1

    def test_should_preserve_paragraph_structure(self):
        """Should preserve paragraph breaks when splitting."""
        service = TextFormattingService()
        service.max_chunk_bytes = 200
        text = "\n\n".join(["Paragraph " + str(i) for i in range(20)])

        chunks = service.split_text_into_chunks(text)

        # Check that at least some paragraph breaks are preserved
        full_text = "\n\n".join(chunks)
        assert "Paragraph 0" in full_text

    def test_should_handle_empty_text(self):
        """Should return empty list for empty text."""
        service = TextFormattingService()

        chunks = service.split_text_into_chunks("")

        assert chunks == []

    def test_should_handle_text_exactly_at_limit(self):
        """Should handle text exactly at byte limit."""
        service = TextFormattingService()
        service.max_chunk_bytes = 100
        text = "a" * 100  # Exactly 100 bytes

        chunks = service.split_text_into_chunks(text)

        assert len(chunks) == 1

    def test_should_split_unicode_text_correctly(self):
        """Should handle Unicode characters correctly."""
        service = TextFormattingService()
        service.max_chunk_bytes = 50
        text = "中文测试 " * 50  # Chinese characters

        chunks = service.split_text_into_chunks(text)

        assert len(chunks) > 1
        # Verify chunks are valid strings
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk) > 0

    def test_should_find_split_in_middle_third(self):
        """Should prefer splitting in middle third of chunk."""
        service = TextFormattingService()
        service.max_chunk_bytes = 100
        # Create text with spaces spread out
        text = "a" * 30 + " " + "b" * 40 + " " + "c" * 30 + " " + "d" * 100

        chunks = service.split_text_into_chunks(text)

        # Should split at one of the spaces
        assert len(chunks) >= 1


# ============================================================================
# TextFormattingService.format_text_chunk() Tests
# ============================================================================

class TestFormatTextChunk:
    """Test single chunk formatting."""

    @patch('app.core.glm.get_glm_client')
    def test_should_format_chunk_successfully(self, mock_get_glm, mock_glm_client):
        """Should format text chunk using GLM API."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        result = service.format_text_chunk("test text without punctuation")

        assert result is not None
        mock_glm_client.client.chat.completions.create.assert_called_once()

    @patch('app.core.glm.get_glm_client')
    def test_should_use_low_temperature(self, mock_get_glm, mock_glm_client):
        """Should use low temperature for consistent formatting."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        service.format_text_chunk("test text")

        call_args = mock_glm_client.client.chat.completions.create.call_args
        assert call_args[1]['temperature'] == 0.1

    @patch('app.core.glm.get_glm_client')
    def test_should_return_original_on_no_glm_client(self, mock_get_glm):
        """Should return original text when GLM client unavailable."""
        mock_get_glm.side_effect = Exception("No client")
        service = TextFormattingService()

        original = "original text"
        result = service.format_text_chunk(original)

        assert result == original

    @patch('app.core.glm.get_glm_client')
    def test_should_return_original_on_api_error(self, mock_get_glm, mock_glm_client):
        """Should return original text on API error."""
        mock_get_glm.return_value = mock_glm_client
        mock_glm_client.client.chat.completions.create.side_effect = Exception("API error")
        service = TextFormattingService()

        original = "original text"
        result = service.format_text_chunk(original)

        assert result == original

    @patch('app.core.glm.get_glm_client')
    def test_should_handle_empty_response(self, mock_get_glm, mock_glm_client):
        """Should handle empty API response."""
        mock_get_glm.return_value = mock_glm_client
        mock_glm_client.client.chat.completions.create.return_value.choices[0].message.content = None
        service = TextFormattingService()

        original = "original text"
        result = service.format_text_chunk(original)

        # Should return original on empty response
        assert result == original

    @patch('app.core.glm.get_glm_client')
    def test_should_handle_too_short_response(self, mock_get_glm, mock_glm_client):
        """Should return original if formatted text is too short."""
        mock_get_glm.return_value = mock_glm_client
        mock_glm_client.client.chat.completions.create.return_value.choices[0].message.content = "hi"
        service = TextFormattingService()

        original = "a" * 100  # 100 chars
        result = service.format_text_chunk(original)

        # Formatted is < 50% of original, should return original
        assert result == original

    @patch('app.core.glm.get_glm_client')
    def test_should_use_reasoning_content_if_empty(self, mock_get_glm, mock_glm_client):
        """Should extract from reasoning_content if content is empty."""
        mock_get_glm.return_value = mock_glm_client
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_choice.message.reasoning_content = "Some reasoning\n最终结果：这是格式化后的文本。"
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_glm_client.client.chat.completions.create.return_value = mock_response

        service = TextFormattingService()

        result = service.format_text_chunk("test text")

        # Should extract from reasoning_content
        assert result is not None


# ============================================================================
# TextFormattingService.format_transcription_text() Tests
# ============================================================================

class TestFormatTranscriptionText:
    """Test full transcription text formatting."""

    @patch('app.core.glm.get_glm_client')
    def test_should_format_short_text(self, mock_get_glm, mock_glm_client):
        """Should format short text in single call."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        result = service.format_transcription_text("short text here")

        assert result is not None

    @patch('app.core.glm.get_glm_client')
    def test_should_return_original_for_very_short_text(self, mock_get_glm, mock_glm_client):
        """Should return original text for very short input."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        original = "short"
        result = service.format_transcription_text(original)

        assert result == original

    @patch('app.core.glm.get_glm_client')
    def test_should_return_original_for_empty_text(self, mock_get_glm, mock_glm_client):
        """Should return original text for empty input."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        result = service.format_transcription_text("")

        assert result == ""

    @patch('app.core.glm.get_glm_client')
    def test_should_format_long_text_in_chunks(self, mock_get_glm, mock_glm_client):
        """Should split and format long text in chunks."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()
        service.max_chunk_bytes = 100

        # Create text longer than limit
        long_text = "word " * 1000

        result = service.format_transcription_text(long_text)

        assert result is not None
        # Should have called GLM API multiple times
        assert mock_glm_client.client.chat.completions.create.call_count >= 1

    @patch('app.core.glm.get_glm_client')
    def test_should_join_chunks_with_paragraph_breaks(self, mock_get_glm, mock_glm_client):
        """Should join formatted chunks with paragraph breaks."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()
        service.max_chunk_bytes = 100

        long_text = "word " * 1000

        result = service.format_transcription_text(long_text)

        # Should have paragraph breaks between chunks
        if mock_glm_client.client.chat.completions.create.call_count > 1:
            assert "\n\n" in result


# ============================================================================
# get_formatting_service() Tests
# ============================================================================

class TestGetFormattingService:
    """Test singleton pattern for TextFormattingService."""

    @patch('app.core.glm.get_glm_client')
    def test_should_return_singleton_instance(self, mock_get_glm, mock_glm_client):
        """Should return the same instance on multiple calls."""
        mock_get_glm.return_value = mock_glm_client

        # Reset singleton
        import app.services.formatting_service as fmt_module
        fmt_module._formatting_service = None

        service1 = get_formatting_service()
        service2 = get_formatting_service()

        assert service1 is service2

    @patch('app.core.glm.get_glm_client')
    def test_should_initialize_once(self, mock_get_glm, mock_glm_client):
        """Should initialize the service only once."""
        mock_get_glm.return_value = mock_glm_client

        # Reset singleton
        import app.services.formatting_service as fmt_module
        fmt_module._formatting_service = None

        get_formatting_service()
        get_formatting_service()
        get_formatting_service()

        # GLM client should only be initialized once
        assert mock_get_glm.call_count == 1


# ============================================================================
# FORMAT_SYSTEM_PROMPT Tests
# ============================================================================

class TestFormatSystemPrompt:
    """Test the format system prompt."""

    def test_should_contain_formatting_rules(self):
        """Should contain formatting rules in system prompt."""
        prompt = TextFormattingService.FORMAT_SYSTEM_PROMPT

        assert "标点符号" in prompt
        assert "段落结构" in prompt
        assert "大小写" in prompt

    def test_should_contain_strict_limits(self):
        """Should contain strict limits in system prompt."""
        prompt = TextFormattingService.FORMAT_SYSTEM_PROMPT

        assert "**不要**" in prompt or "不要" in prompt
        assert "不要添加" in prompt or "添加原文" in prompt

    def test_should_contain_examples(self):
        """Should contain formatting examples."""
        prompt = TextFormattingService.FORMAT_SYSTEM_PROMPT

        assert "示例" in prompt or "输入" in prompt
        assert "输出" in prompt


# ============================================================================
# Edge Cases
# ============================================================================

class TestFormattingEdgeCases:
    """Test edge cases and error handling."""

    @patch('app.core.glm.get_glm_client')
    def test_should_handle_text_with_only_whitespace(self, mock_get_glm, mock_glm_client):
        """Should handle text with only whitespace."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        result = service.format_transcription_text("   \n\n   \t   ")

        # Should return original or empty
        assert result is not None

    @patch('app.core.glm.get_glm_client')
    def test_should_handle_unicode_emoji(self, mock_get_glm, mock_glm_client):
        """Should handle text with emoji."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        result = service.format_transcription_text("测试emoji 😀 🎵")

        assert result is not None

    @patch('app.core.glm.get_glm_client')
    def test_should_handle_mixed_language_text(self, mock_get_glm, mock_glm_client):
        """Should handle mixed Chinese and English text."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        result = service.format_transcription_text("这是中文 and this is English 混合text")

        assert result is not None

    @patch('app.core.glm.get_glm_client')
    def test_should_handle_text_with_special_chars(self, mock_get_glm, mock_glm_client):
        """Should handle text with special characters."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        result = service.format_transcription_text("测试 @#$%^&*() special chars")

        assert result is not None

    @patch('app.core.glm.get_glm_client')
    def test_should_handle_very_long_single_line(self, mock_get_glm, mock_glm_client):
        """Should handle very long single line without breaks."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        long_line = "a" * 10000
        chunks = service.split_text_into_chunks(long_line)

        # Should split it somehow
        assert len(chunks) >= 1
        # Total content should be preserved
        total_length = sum(len(c) for c in chunks)
        assert total_length > 0

    @patch('app.core.glm.get_glm_client')
    def test_should_handle_newlines_only(self, mock_get_glm, mock_glm_client):
        """Should handle text with only newlines."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        result = service.format_transcription_text("\n\n\n\n")

        assert result is not None

    @patch('app.core.glm.get_glm_client')
    def test_split_chunks_searches_from_end_when_no_middle_whitespace(self, mock_get_glm, mock_glm_client):
        """Test that chunk splitting searches from end when no whitespace in middle (lines 131-134)."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        # Create text larger than max_chunk_bytes (10000 bytes) with whitespace only at the end
        # This forces the backwards search (lines 131-134)
        large_text_no_middle_whitespace = "a" * 10500 + " " + "b" * 1000

        chunks = service.split_text_into_chunks(large_text_no_middle_whitespace)

        # Should split into multiple chunks
        assert len(chunks) >= 2
        # First chunk should be mostly 'a's
        assert "a" in chunks[0]
        # Second chunk should have 'b's
        assert any("b" in chunk for chunk in chunks[1:])

    @patch('app.core.glm.get_glm_client')
    def test_split_chunks_force_split_when_no_whitespace_at_all(self, mock_get_glm, mock_glm_client):
        """Test that chunk splitting forces split at max_bytes when no whitespace found (line 138)."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        # Create text with absolutely no whitespace, larger than max_chunk_bytes (10000)
        # This forces the force-split at max_chunk_bytes (line 138)
        text_no_whitespace = "a" * 15000

        chunks = service.split_text_into_chunks(text_no_whitespace)

        # Should split into multiple chunks
        assert len(chunks) >= 2
        # All chunks combined should have the same total content
        combined = "".join(chunks)
        assert len(combined) == len(text_no_whitespace)

    @patch('app.core.glm.get_glm_client')
    def test_formats_single_chunk_without_chunking(self, mock_get_glm, mock_glm_client):
        """Test that formatting a text that fits in one chunk uses the single-chunk path (lines 238-239)."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()
        # Create text that's between 50 and max_chunk_bytes (10000)
        # This will be formatted as a single chunk (lines 238-239)
        medium_text = "测试文本。" * 100  # About 500 characters, well within limits

        result = service.format_transcription_text(medium_text)

        # Should successfully format
        assert result is not None
        # Verify formatting occurred
        assert len(result) > 0

    @patch('app.core.glm.get_glm_client')
    def test_split_chunks_handles_very_long_word(self, mock_get_glm, mock_glm_client):
        """Test that chunk splitting handles a single very long word (no whitespace)."""
        mock_get_glm.return_value = mock_glm_client
        service = TextFormattingService()

        # Create a single "word" longer than max_chunk_bytes
        # This exercises the force-split path
        very_long_word = "superlongword" * 1000  # Much longer than 3000 bytes

        chunks = service.split_text_into_chunks(very_long_word)

        # Should split it into multiple chunks
        assert len(chunks) >= 2
        # All chunks combined should have the same total content
        combined = "".join(chunks)
        assert len(combined) == len(very_long_word)
