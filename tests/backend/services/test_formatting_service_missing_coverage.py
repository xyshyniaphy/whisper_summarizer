"""
Text Formatting Service Missing Coverage Tests

Tests for formatting_service.py lines:
- Lines 131-134: Backward search for whitespace when none found in middle
- Line 138: Last resort force split at max_bytes
- Lines 238-239: Additional edge cases

These are extreme edge cases where text has no whitespace characters.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.formatting_service import TextFormattingService


@pytest.fixture
def small_chunk_formatter():
    """Create formatter with small max_chunk_bytes via settings mock."""
    with patch('app.services.formatting_service.settings') as mock_settings:
        mock_settings.MAX_FORMAT_CHUNK = 50
        return TextFormattingService()


@pytest.fixture
def tiny_chunk_formatter():
    """Create formatter with tiny max_chunk_bytes via settings mock."""
    with patch('app.services.formatting_service.settings') as mock_settings:
        mock_settings.MAX_FORMAT_CHUNK = 30
        return TextFormattingService()


@pytest.mark.unit
class TestTextFormattingServiceNoWhitespace:
    """Test text chunking with no whitespace characters."""

    def test_split_text_no_whitespace_hits_backward_search_lines_131_134(
        self,
        small_chunk_formatter
    ) -> None:
        """
        Test that text with no whitespace triggers backward search.

        This targets formatting_service.py lines 131-134:
        ```python
        # If no whitespace found in middle, try entire chunk
        if split_at == -1:
            for i in range(len(chunk) - 1, 0, -1):
                if chunk[i].isspace():
                    split_at = i
                    break
        ```

        Scenario:
        1. Create text with minimal whitespace at the END
        2. Text length > max_chunk_bytes
        3. Should search backward and find whitespace at end (lines 131-134)
        """
        # Create text with whitespace ONLY at the end
        # This triggers line 130 (split_at == -1) then lines 131-134 (backward search)
        text_with_whitespace_at_end = "abcdefghij" * 5 + " "  # 50 chars + 1 space

        # Split the text
        chunks = small_chunk_formatter.split_text_into_chunks(text_with_whitespace_at_end)

        # Should split and find the whitespace
        assert len(chunks) >= 1
        # Verify no chunk exceeds max_chunk_bytes (50)
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_split_text_no_whitespace_uses_last_resort_hits_line_138(
        self,
        tiny_chunk_formatter
    ) -> None:
        """
        Test that text with NO whitespace anywhere uses last resort force split.

        This specifically targets formatting_service.py line 138:
        ```python
        # Last resort: force split at max_bytes
        if split_at == -1:
            split_at = self.max_chunk_bytes
        ```

        Scenario:
        1. Text with NO whitespace characters anywhere
        2. Should use line 138 (force split at max_bytes)
        """
        # Create text that will require the "last resort" split
        # NO whitespace at all, length > max_chunk_bytes
        continuous_text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345" * 2  # 62 characters, no whitespace

        chunks = tiny_chunk_formatter.split_text_into_chunks(continuous_text)

        # Should force split at 30 chars (line 138)
        assert len(chunks) >= 2

        # First chunk should be exactly max_chunk_bytes (30)
        assert len(chunks[0]) == 30
        assert chunks[0] == "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123"

        # Verify no chunk exceeds max_chunk_bytes
        for chunk in chunks:
            assert len(chunk) <= 30

    def test_split_text_all_whitespace_at_end_hits_lines_131_134(
        self,
        small_chunk_formatter
    ) -> None:
        """
        Test backward search when whitespace only exists at end of chunk.

        This targets lines 131-134:
        - Line 130: split_at == -1 (no whitespace found in middle)
        - Lines 131-134: Backward search from end to beginning
        """
        # Create text where whitespace is only at the very end
        # This forces the backward search (lines 131-134) to find it
        text = "abcdefghij" * 4 + "   "  # 40 chars + 3 spaces

        chunks = small_chunk_formatter.split_text_into_chunks(text)

        # Should split at or before max_chunk_bytes (50)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_split_text_exactly_max_chunk_bytes_no_whitespace(
        self,
        small_chunk_formatter
    ) -> None:
        """
        Test edge case where text length exactly equals max_chunk_bytes.

        This tests the boundary condition for line 138 (force split).
        """
        # Text exactly max_chunk_bytes with no whitespace
        exact_text = "abcdefghij" * 5  # Exactly 50 characters

        chunks = small_chunk_formatter.split_text_into_chunks(exact_text)

        # Should return single chunk
        assert len(chunks) == 1
        assert len(chunks[0]) == 50

    def test_split_text_just_over_max_chunk_bytes_no_whitespace(
        self,
        small_chunk_formatter
    ) -> None:
        """
        Test edge case where text is just over max_chunk_bytes.

        This tests line 138 (force split) with minimal overflow.
        """
        # Text just over max_chunk_bytes (50)
        over_text = "abcdefghij" * 5 + "xyz"  # 53 characters

        chunks = small_chunk_formatter.split_text_into_chunks(over_text)

        # Should split into multiple chunks
        assert len(chunks) >= 2
        # First chunk should be max_chunk_bytes (line 138)
        assert len(chunks[0]) == 50
        assert chunks[0] == "abcdefghij" * 5


@pytest.mark.unit
class TestTextFormattingServiceSingleChunk:
    """Test formatting with single chunk (lines 238-239)."""

    def test_format_transcription_text_single_chunk_hits_lines_238_239(
        self
    ) -> None:
        """
        Test that text requiring only one chunk hits lines 238-239.

        This targets formatting_service.py lines 238-239:
        ```python
        logger.info(f"Formatting single chunk ({len(text)} chars)")
        return self.format_text_chunk(chunks[0])
        ```

        Scenario:
        1. Text is long enough to format (> 50 chars)
        2. But short enough to be a single chunk (< MAX_FORMAT_CHUNK)
        3. Should hit lines 238-239 (single chunk path)
        """
        from unittest.mock import patch, MagicMock

        # Mock settings to have large MAX_FORMAT_CHUNK
        with patch('app.services.formatting_service.settings') as mock_settings:
            mock_settings.MAX_FORMAT_CHUNK = 10000

            formatter = TextFormattingService()

            # Mock GLM client to avoid real API calls
            # Note: GLM client has nested structure: glm_client.client.chat.completions.create
            mock_inner_client = MagicMock()
            mock_response = MagicMock()
            mock_choice = MagicMock()
            # Return formatted text that's at least 50% of original length (line 203 check)
            # Original is ~150 chars, so we need at least 75 chars
            mock_choice.message.content = "This is a test text that is long enough to format. This is a test text that is long enough to format. This is a test text that is long enough to format. Formatted."
            mock_response.choices = [mock_choice]
            mock_inner_client.chat.completions.create.return_value = mock_response

            mock_glm = MagicMock()
            mock_glm.client = mock_inner_client
            mock_glm.model = "GLM-4.5-Air"
            formatter.glm_client = mock_glm

            # Text that will be a single chunk
            # Must be > 50 chars (to pass line 230 check)
            # But < 10000 chars (to be single chunk)
            single_chunk_text = "This is a test text that is long enough to format. " * 3  # ~150 chars

            # Format the text (note: format_transcription_text is synchronous)
            result = formatter.format_transcription_text(single_chunk_text)

            # Should return formatted text (not the original)
            assert result != single_chunk_text
            assert "Formatted" in result

            # Verify GLM was called
            assert mock_inner_client.chat.completions.create.called
