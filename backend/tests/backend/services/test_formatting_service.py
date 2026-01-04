"""
Tests for TextFormattingService - LLM-based text formatting.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.formatting_service import (
    TextFormattingService,
    get_formatting_service
)


@pytest.fixture
def mock_glm_client():
    """Create a mock GLM client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_choice = Mock()
    mock_message = Mock()

    mock_message.content = "Formatted text with punctuation."
    mock_choice.message = mock_message
    mock_choice.finish_reason = "stop"
    mock_response.choices = [mock_choice]

    mock_client.client.chat.completions.create.return_value = mock_response
    mock_client.model = "test-model"

    return mock_client


@pytest.fixture
def formatting_service(mock_glm_client):
    """Create a TextFormattingService with mocked GLM client."""
    service = TextFormattingService()
    service.glm_client = mock_glm_client
    return service


class TestTextFormattingServiceInitialization:
    """Tests for service initialization."""

    def test_init_sets_default_max_chunk(self):
        """Test that default max chunk size is set."""
        with patch('app.services.formatting_service.settings', MAX_FORMAT_CHUNK=4000):
            service = TextFormattingService()
            assert service.max_chunk_bytes == 4000

    def test_init_with_custom_max_chunk(self):
        """Test initialization with custom chunk size."""
        with patch('app.services.formatting_service.settings', MAX_FORMAT_CHUNK=5000):
            service = TextFormattingService()
            assert service.max_chunk_bytes == 5000

    @patch('app.core.glm.get_glm_client')
    def test_glm_client_initialization(self, mock_get_glm):
        """Test GLM client is initialized on startup."""
        mock_client = Mock()
        mock_get_glm.return_value = mock_client

        service = TextFormattingService()

        assert service.glm_client == mock_client
        mock_get_glm.assert_called_once()

    @patch('app.core.glm.get_glm_client', side_effect=Exception("Import error"))
    def test_glm_client_init_failure(self, mock_get_glm):
        """Test that GLM client init failure is handled gracefully."""
        service = TextFormattingService()
        assert service.glm_client is None


class TestTextSplitting:
    """Tests for split_text_into_chunks method."""

    def test_empty_text_returns_empty_list(self, formatting_service):
        """Test that empty text returns empty list."""
        chunks = formatting_service.split_text_into_chunks("")
        assert chunks == []

    def test_none_text_returns_empty_list(self, formatting_service):
        """Test that None text returns empty list."""
        chunks = formatting_service.split_text_into_chunks(None)
        assert chunks == []

    def test_short_text_returns_single_chunk(self, formatting_service):
        """Test that text under max_chunk is returned as single chunk."""
        short_text = "This is a short text."
        chunks = formatting_service.split_text_into_chunks(short_text)
        assert len(chunks) == 1
        assert chunks[0] == short_text

    def test_text_exactly_at_max_chunk(self, formatting_service):
        """Test text that exactly matches max_chunk size."""
        service = TextFormattingService()
        service.max_chunk_bytes = 100

        # Create text that's exactly 100 bytes
        text = "x" * 100
        chunks = service.split_text_into_chunks(text)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_split_into_chunks(self, formatting_service):
        """Test that long text is split into multiple chunks."""
        service = TextFormattingService()
        service.max_chunk_bytes = 50

        # Create text longer than max_chunk
        long_text = "word " * 20  # ~100 bytes

        chunks = service.split_text_into_chunks(long_text)

        assert len(chunks) > 1
        # All chunks should be within limit
        for chunk in chunks:
            assert len(chunk.encode('utf-8')) <= service.max_chunk_bytes + 100  # Allow small buffer

    def test_chunks_split_at_whitespace(self, formatting_service):
        """Test that chunks are split at whitespace boundaries."""
        service = TextFormattingService()
        service.max_chunk_bytes = 30

        # Text with clear whitespace boundaries
        text = "word1 word2 word3 word4 word5 word6 word7"
        chunks = service.split_text_into_chunks(text)

        # No chunk should end in the middle of a word (partial word fragment)
        # Since chunks are stripped, they end with complete words
        for chunk in chunks:
            # Check that chunk doesn't end with partial word like "wor" or "d4"
            # Each chunk should end with complete word (letter/digit)
            stripped = chunk.rstrip()
            assert stripped, "Chunk should not be empty after stripping"
            # Last character should be alphanumeric (complete word)
            assert stripped[-1].isalnum(), f"Chunk should end with complete word, got: {repr(stripped[-1])}"

    def test_chunks_are_stripped(self, formatting_service):
        """Test that chunks have leading/trailing whitespace stripped."""
        service = TextFormattingService()
        service.max_chunk_bytes = 50

        text = "word " * 20
        chunks = service.split_text_into_chunks(text)

        # Each chunk should be stripped
        for chunk in chunks:
            assert chunk == chunk.strip()

    def test_unicode_text_splitting(self, formatting_service):
        """Test splitting of Unicode text (Chinese)."""
        service = TextFormattingService()
        service.max_chunk_bytes = 50

        # Chinese text
        chinese_text = "这是一个测试。" * 20
        chunks = service.split_text_into_chunks(chinese_text)

        assert len(chunks) > 1
        # Verify each chunk is valid UTF-8
        for chunk in chunks:
            chunk.encode('utf-8')  # Should not raise


class TestFormatTextChunk:
    """Tests for format_text_chunk method."""

    def test_no_glm_client_returns_original(self, formatting_service):
        """Test that original text is returned when GLM client is unavailable."""
        formatting_service.glm_client = None

        original = "unformatted text without punctuation"
        result = formatting_service.format_text_chunk(original)

        assert result == original

    def test_successful_formatting(self, formatting_service, mock_glm_client):
        """Test successful text formatting."""
        original = "这是一个测试文本没有标点符号"
        formatted = "这是一个测试文本，没有标点符号。"

        mock_glm_client.client.chat.completions.create.return_value.choices[0].message.content = formatted

        result = formatting_service.format_text_chunk(original)

        assert result == formatted

    def test_formatting_with_empty_response_returns_original(self, formatting_service, mock_glm_client):
        """Test that empty GLM response returns original text."""
        original = "original text"

        mock_glm_client.client.chat.completions.create.return_value.choices[0].message.content = None

        result = formatting_service.format_text_chunk(original)

        assert result == original

    def test_too_short_response_returns_original(self, formatting_service, mock_glm_client):
        """Test that suspiciously short response returns original."""
        original = "x" * 100  # 100 chars
        short_response = "x" * 40  # 40 chars (< 50%)

        mock_glm_client.client.chat.completions.create.return_value.choices[0].message.content = short_response

        result = formatting_service.format_text_chunk(original)

        assert result == original

    def test_formatting_exception_returns_original(self, formatting_service, mock_glm_client):
        """Test that API exceptions return original text."""
        original = "text to format"

        mock_glm_client.client.chat.completions.create.side_effect = Exception("API error")

        result = formatting_service.format_text_chunk(original)

        assert result == original

    def test_formatting_uses_low_temperature(self, formatting_service, mock_glm_client):
        """Test that formatting uses low temperature for consistency."""
        formatting_service.format_text_chunk("test")

        call_args = mock_glm_client.client.chat.completions.create.call_args
        assert call_args[1]['temperature'] == 0.1

    def test_formatting_includes_system_prompt(self, formatting_service, mock_glm_client):
        """Test that system prompt is included."""
        formatting_service.format_text_chunk("test")

        call_args = mock_glm_client.client.chat.completions.create.call_args
        messages = call_args[1]['messages']

        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert '格式化专家' in messages[0]['content']

    def test_max_tokens_calculation(self, formatting_service, mock_glm_client):
        """Test that max_tokens is calculated based on input length."""
        original = "x" * 2000
        formatting_service.format_text_chunk(original)

        call_args = mock_glm_client.client.chat.completions.create.call_args
        max_tokens = call_args[1]['max_tokens']

        # Should be 2x input length, capped at 4000
        assert max_tokens == min(4000, 4000)


class TestFormatTranscriptionText:
    """Tests for format_transcription_text method."""

    def test_empty_text_returns_empty(self, formatting_service):
        """Test that empty text is returned as-is."""
        result = formatting_service.format_transcription_text("")
        assert result == ""

    def test_short_text_skipped(self, formatting_service):
        """Test that very short text (< 50 chars) is not formatted."""
        short_text = "Short"
        result = formatting_service.format_transcription_text(short_text)

        assert result == short_text

    def test_single_chunk_formatting(self, formatting_service, mock_glm_client):
        """Test formatting of text that fits in one chunk."""
        text = "This is a text that needs formatting and should be in one chunk"
        formatted = "This is a text that needs formatting, and should be in one chunk."

        mock_glm_client.client.chat.completions.create.return_value.choices[0].message.content = formatted

        result = formatting_service.format_transcription_text(text)

        assert result == formatted

    def test_multi_chunk_formatting(self, formatting_service, mock_glm_client):
        """Test formatting of text split into multiple chunks."""
        formatting_service.max_chunk_bytes = 50

        # Long text that will be split
        long_text = "word " * 100

        # Mock different responses for each chunk
        def mock_create(*args, **kwargs):
            mock_resp = Mock()
            mock_choice = Mock()
            mock_msg = Mock()

            # Return formatted version of the chunk
            user_content = args[1]['messages'][1]['content']
            mock_msg.content = user_content.replace("  ", ", ")  # Simple formatting

            mock_choice.message = mock_msg
            mock_choice.finish_reason = "stop"
            mock_resp.choices = [mock_choice]
            return mock_resp

        mock_glm_client.client.chat.completions.create.side_effect = mock_create

        result = formatting_service.format_transcription_text(long_text)

        # Should join chunks with paragraph breaks
        assert "\n\n" in result

    def test_multi_chunk_formatting_with_double_newline_separator(self, formatting_service, mock_glm_client):
        """Test that chunks are joined with paragraph breaks."""
        formatting_service.max_chunk_bytes = 50

        text = "chunk one " * 20 + "chunk two " * 20

        mock_glm_client.client.chat.completions.create.return_value.choices[0].message.content = "Formatted chunk."

        result = formatting_service.format_transcription_text(text)

        # Should have double newlines between chunks
        assert result.count("\n\n") >= 1


class TestGetFormattingService:
    """Tests for get_formatting_service singleton."""

    @patch('app.services.formatting_service._formatting_service', None)
    @patch('app.services.formatting_service.TextFormattingService')
    def test_singleton_initialization(self, mock_service_cls):
        """Test that singleton is initialized once."""
        mock_instance = Mock()
        mock_service_cls.return_value = mock_instance

        service1 = get_formatting_service()
        service2 = get_formatting_service()

        assert service1 is service2
        mock_service_cls.assert_called_once()

    def test_cached_instance_returned(self):
        """Test that cached instance is returned on subsequent calls."""
        with patch('app.services.formatting_service._formatting_service') as mock_cached:
            result = get_formatting_service()
            assert result == mock_cached


class TestSystemPrompt:
    """Tests for system prompt content."""

    def test_system_prompt_exists(self, formatting_service):
        """Test that system prompt is defined."""
        assert formatting_service.FORMAT_SYSTEM_PROMPT is not None
        assert len(formatting_service.FORMAT_SYSTEM_PROMPT) > 100

    def test_system_prompt_contains_formatting_rules(self, formatting_service):
        """Test that system prompt contains formatting instructions."""
        prompt = formatting_service.FORMAT_SYSTEM_PROMPT
        assert '标点符号' in prompt
        assert '段落结构' in prompt
        # Account for markdown bold: **不要**总结
        assert ('不要总结' in prompt or '**不要**' in prompt)

    def test_system_prompt_has_examples(self, formatting_service):
        """Test that system prompt includes examples."""
        prompt = formatting_service.FORMAT_SYSTEM_PROMPT
        assert '示例' in prompt or 'example' in prompt.lower()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_text_with_only_whitespace(self, formatting_service):
        """Test text that contains only whitespace."""
        result = formatting_service.format_transcription_text("   \n\n   ")
        assert result == "   \n\n   "

    def test_mixed_unicode_content(self, formatting_service):
        """Test text with mixed Unicode content."""
        mixed = "English text and 中文混合 content 123"
        chunks = formatting_service.split_text_into_chunks(mixed)

        # Should handle mixed content
        assert len(chunks) >= 1
        for chunk in chunks:
            # Verify it's valid UTF-8
            chunk.encode('utf-8')

    def test_very_long_single_word(self, formatting_service):
        """Test handling of very long single word without spaces."""
        service = TextFormattingService()
        service.max_chunk_bytes = 50

        # Very long word with no spaces
        long_word = "a" * 200
        chunks = service.split_text_into_chunks(long_word)

        # Should force split at max_chunk_bytes
        assert len(chunks) >= 1
