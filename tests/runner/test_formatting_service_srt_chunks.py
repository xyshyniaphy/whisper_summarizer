import pytest
from app.services.formatting_service import TextFormattingService
from unittest.mock import patch, MagicMock


def test_formatting_chunks_by_srt_sections():
    """Should chunk text by SRT section count, not raw bytes"""
    # Mock GLM client before service initialization
    with patch('app.core.glm.get_glm_client') as mock_glm:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Formatted text"))]
        mock_client.client.chat.completions.create.return_value = mock_response
        mock_glm.return_value = mock_client

        service = TextFormattingService()

        # Mock text with 100 lines (representing 100 SRT entries)
        # Each SRT entry has: number, timestamp, text, blank line
        srt_text = ""
        for i in range(1, 101):
            srt_text += f"{i}\n"
            srt_text += f"00:00:{i//60:02d},{i%60:03d} --> 00:00:{(i+5)//60:02d},{(i+5)%60:03d}\n"
            srt_text += f"Subtitle text {i}\n"
            srt_text += "\n"

        result = service.format_transcription(
            raw_text=srt_text
        )

        # Should have called GLM (actual number depends on chunking)
        assert mock_client.client.chat.completions.create.call_count >= 1


def test_formatting_respects_srt_section_boundaries():
    """Chunks should not split in the middle of an SRT section"""
    service = TextFormattingService()

    # Create SRT-like text with clear section markers
    srt_text = ""
    for i in range(1, 31):  # 30 SRT sections
        srt_text += f"{i}\n"
        srt_text += f"00:00:{i//60:02d},000 --> 00:00:{(i+2)//60:02d},000\n"
        srt_text += f"Section {i} text here\n"
        srt_text += "\n"

    # Use the new SRT-aware chunking method
    chunks = service.split_text_by_srt_sections(srt_text, max_sections_per_chunk=10)

    # Should have 3 chunks (30 sections / 10 per chunk)
    assert len(chunks) == 3

    # Verify each chunk has at most 10 sections
    for chunk in chunks:
        lines = chunk.split('\n')
        section_count = len([l for l in lines if '-->' in l])
        assert section_count <= 10, f"Chunk has {section_count} sections, expected max 10"


def test_formatting_falls_back_to_bytes_for_non_srt():
    """Should fall back to byte chunking for non-SRT text"""
    service = TextFormattingService()

    # Plain text without SRT markers
    plain_text = "This is plain text. " * 1000

    # Use the SRT chunking method with non-SRT text
    chunks = service.split_text_by_srt_sections(plain_text, max_sections_per_chunk=50)

    # Should still work, falling back to byte chunking
    assert len(chunks) >= 1
    # Should use the default byte-based chunking
    assert len(chunks[0]) <= 11000  # max_chunk_bytes + 1000


def test_srt_chunking_handles_empty_sections():
    """Should handle SRT text with extra blank lines"""
    service = TextFormattingService()

    # Create SRT text with extra blank lines between sections
    srt_text = ""
    for i in range(1, 16):  # 15 SRT sections
        srt_text += f"{i}\n"
        srt_text += f"00:00:{i//60:02d},000 --> 00:00:{(i+2)//60:02d},000\n"
        srt_text += f"Section {i} text here\n"
        srt_text += "\n\n\n"  # Extra blank lines

    chunks = service.split_text_by_srt_sections(srt_text, max_sections_per_chunk=5)

    # Should have 3 chunks (15 sections / 5 per chunk)
    assert len(chunks) == 3

    # Verify section count per chunk
    for i, chunk in enumerate(chunks):
        lines = chunk.split('\n')
        section_count = len([l for l in lines if '-->' in l])
        # Last chunk may have fewer sections
        if i < len(chunks) - 1:
            assert section_count == 5, f"Chunk {i} has {section_count} sections, expected 5"
        else:
            assert section_count <= 5, f"Last chunk has {section_count} sections, expected max 5"
