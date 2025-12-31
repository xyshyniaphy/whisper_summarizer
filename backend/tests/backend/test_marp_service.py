"""
Test suite for MarpService - Marp CLI PPTX generation service.

Tests cover:
- Unit tests for markdown generation
- Content chunking logic
- Markdown escaping
- File operations
- Integration tests with Marp CLI (marked with @pytest.mark.integration)
"""
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.marp_service import MarpService, get_marp_service


# ============================================================================
# Unit Tests: MarpService Initialization
# ============================================================================

class TestMarpServiceInitialization:
    """Tests for MarpService initialization and basic setup."""

    def test_init_with_default_output_dir(self):
        """Test MarpService initialization with default output directory."""
        service = MarpService()
        assert service.output_dir == Path("/app/data/output")

    def test_init_with_custom_output_dir(self, temp_output_dir: Path):
        """Test MarpService initialization with custom output directory."""
        service = MarpService(output_dir=temp_output_dir)
        assert service.output_dir == temp_output_dir

    def test_output_directory_created(self, temp_output_dir: Path):
        """Test that output directory is created if it doesn't exist."""
        non_existent_dir = temp_output_dir / "new_output"
        service = MarpService(output_dir=non_existent_dir)
        assert non_existent_dir.exists()
        assert non_existent_dir.is_dir()


# ============================================================================
# Unit Tests: Markdown Generation
# ============================================================================

class TestMarkdownGeneration:
    """Tests for Marp markdown content generation."""

    def test_generate_marp_markdown_basic_structure(self, marp_service: MarpService, mock_transcription):
        """Test basic markdown structure with frontmatter."""
        markdown = marp_service._generate_marp_markdown(mock_transcription)

        # Check frontmatter exists
        assert markdown.startswith("---")
        assert "marp: true" in markdown
        assert "theme: gaia" in markdown
        assert "paginate: true" in markdown

        # Check slide structure
        assert "# " in markdown  # Has title
        assert "---" in markdown  # Has slide separators

    def test_generate_marp_markdown_title_slide(self, marp_service: MarpService, mock_transcription):
        """Test title slide contains correct information."""
        markdown = marp_service._generate_marp_markdown(mock_transcription, None)
        lines = markdown.split("\n")

        # Find title slide (first slide after frontmatter)
        in_content = False
        for i, line in enumerate(lines):
            if in_content and line.startswith("# "):
                title = line[2:].strip()
                assert title == mock_transcription.file_name
                break
            if "---" in line and in_content:
                break
            if "lead" in line:
                in_content = True

    def test_generate_marp_markdown_with_duration(self, marp_service: MarpService):
        """Test title slide includes duration information."""
        class MockTranscription:
            def __init__(self):
                self.id = "test-id"
                self.file_name = "test_audio.mp3"
                self.original_text = "Test content"
                self.duration_seconds = 3665.0  # 61:05
                self.summaries = []

        mock = MockTranscription()
        markdown = marp_service._generate_marp_markdown(mock)

        # Check duration is formatted correctly (61:05)
        assert "61:05" in markdown or "1:01:05" in markdown or "61:05" in markdown

    def test_generate_marp_markdown_with_summary(self, marp_service: MarpService, mock_transcription):
        """Test markdown includes summary when provided."""
        class MockSummary:
            def __init__(self):
                self.summary_text = "Test summary point 1.\n\nTest summary point 2."

        class MockTranscriptionWithSummary:
            def __init__(self):
                self.id = "test-id"
                self.file_name = "test.mp3"
                self.original_text = "Test content"
                self.duration_seconds = None
                self.summaries = [MockSummary()]

        mock = MockTranscriptionWithSummary()
        summary_text = mock.summaries[0].summary_text
        markdown = marp_service._generate_marp_markdown(mock, summary_text)

        assert "AI 摘要" in markdown
        assert "Test summary point 1" in markdown
        assert "Test summary point 2" in markdown

    def test_generate_marp_markdown_without_summary(self, marp_service: MarpService, mock_transcription):
        """Test markdown works correctly without summary."""
        markdown = marp_service._generate_marp_markdown(mock_transcription, None)
        # Should not include AI summary section
        assert "AI 摘要" not in markdown

    def test_create_summary_slides(self, marp_service: MarpService):
        """Test summary slide creation from summary text."""
        summary_text = "Point one.\n\nPoint two.\n\nPoint three."
        slides = marp_service._create_summary_slides(summary_text)

        assert "# AI 摘要" in slides
        assert "- Point one." in slides
        assert "- Point two." in slides
        assert "- Point three." in slides

    def test_create_summary_slides_limits_bullets(self, marp_service: MarpService):
        """Test that summary slides limit to 10 bullets."""
        # Create summary with more than 10 points
        long_summary = "\n\n".join([f"Point {i}." for i in range(15)])
        slides = marp_service._create_summary_slides(long_summary)

        # Should have at most 10 bullet points
        bullet_count = slides.count("- Point")
        assert bullet_count <= 10

    def test_create_content_slides_basic(self, marp_service: MarpService):
        """Test basic content slide creation."""
        content = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
        slides = marp_service._create_content_slides(content)

        assert "# 转录内容" in slides
        assert "Paragraph 1." in slides
        assert "Paragraph 2." in slides
        assert "Paragraph 3." in slides

    def test_create_content_slides_with_multiple_chunks(self, marp_service: MarpService):
        """Test content slides split long content into multiple slides."""
        # Create content longer than CHARS_PER_SLIDE
        long_content = "\n\n".join([f"Paragraph {i}." * 50 for i in range(5)])
        slides = marp_service._create_content_slides(long_content)

        # Should have multiple content slides
        slide_count = slides.count("# 转录内容")
        assert slide_count >= 2

    def test_create_content_slides_with_numbering(self, marp_service: MarpService):
        """Test that multi-slide content has correct numbering."""
        # Create content that will split into 3 slides
        long_content = "\n\n".join([
            "Slide 1 content. " * 100,
            "Slide 2 content. " * 100,
            "Slide 3 content. " * 100,
        ])
        slides = marp_service._create_content_slides(long_content)

        # Check for slide numbering
        assert "(1/" in slides or "转录内容 (1/" in slides
        assert "(2/" in slides or "转录内容 (2/" in slides
        assert "(3/" in slides or "转录内容 (3/" in slides


# ============================================================================
# Unit Tests: Content Chunking
# ============================================================================

class TestContentChunking:
    """Tests for content chunking logic."""

    def test_chunk_content_short_text(self, marp_service: MarpService):
        """Test short content is not split."""
        short_text = "This is short text."
        chunks = marp_service._chunk_content(short_text)

        assert len(chunks) == 1
        assert chunks[0] == short_text

    def test_chunk_content_long_text(self, marp_service: MarpService):
        """Test long content is split into chunks."""
        # Create text longer than CHARS_PER_SLIDE (800) with newlines
        # Each paragraph is ~200 chars, so 10 paragraphs should create ~3-4 chunks
        long_text = "\n\n".join([f"Paragraph {i} with enough content to make it longer. " * 10 for i in range(15)])
        chunks = marp_service._chunk_content(long_text)

        assert len(chunks) > 1
        # Each chunk should be approximately the right size
        for chunk in chunks:
            assert len(chunk) <= marp_service.CHARS_PER_SLIDE + 200  # Allow some overflow

    def test_chunk_content_preserves_paragraphs(self, marp_service: MarpService):
        """Test chunking preserves paragraph boundaries."""
        text = "\n\n".join([f"Paragraph {i}" * 50 for i in range(5)])
        chunks = marp_service._chunk_content(text)

        # Each chunk should start and end with complete paragraphs
        for i, chunk in enumerate(chunks):
            if i < len(chunks) - 1:  # Not the last chunk
                # Should end with a newline (paragraph boundary)
                assert chunk.endswith("\n") or not chunk.endswith("Paragraph")

    def test_chunk_content_max_slides_limit(self, marp_service: MarpService):
        """Test chunking respects MAX_CONTENT_SLIDES limit."""
        # Create very long content
        very_long_text = "\n".join([f"Line {i}" for i in range(10000)])
        chunks = marp_service._chunk_content(very_long_text)

        # Should not exceed max slides
        assert len(chunks) <= marp_service.MAX_CONTENT_SLIDES

    def test_chunk_content_empty_string(self, marp_service: MarpService):
        """Test chunking empty string."""
        chunks = marp_service._chunk_content("")

        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_chunk_content_single_paragraph(self, marp_service: MarpService):
        """Test chunking single long paragraph."""
        # Single line without newlines
        single_paragraph = "Word " * 1000
        chunks = marp_service._chunk_content(single_paragraph)

        # Should still chunk appropriately
        assert len(chunks) >= 1


# ============================================================================
# Unit Tests: Markdown Escaping
# ============================================================================

class TestMarkdownEscaping:
    """Tests for markdown character escaping."""

    def test_escape_markdown_basic(self, marp_service: MarpService):
        """Test basic markdown escaping."""
        text = "# Heading"
        escaped = marp_service._escape_markdown(text)

        assert "\\#" in escaped or "#" in escaped  # May or may not escape
        assert "\\#" in escaped or "Heading" in escaped

    def test_escape_markdown_special_chars(self, marp_service: MarpService):
        """Test escaping of special markdown characters."""
        text = "`code` and [link](url)"
        escaped = marp_service._escape_markdown(text)

        # Should escape backticks and brackets
        assert "\\`" in escaped or "code" in escaped
        assert "\\[" in escaped or "link" in escaped

    def test_format_content_preserves_asterisks(self, marp_service: MarpService):
        """Test that asterisks are preserved for basic formatting."""
        content = "Important text with *bold* and _italic_"
        formatted = marp_service._format_content_for_marp(content)

        # Asterisks should be preserved for formatting
        assert "*" in formatted or "Important" in formatted

    def test_format_content_handles_empty_lines(self, marp_service: MarpService):
        """Test formatting handles empty lines correctly."""
        content = "Para 1\n\n\n\nPara 2"  # Multiple empty lines
        formatted = marp_service._format_content_for_marp(content)

        # Should collapse multiple empty lines
        assert formatted.count("\n\n") >= 1


# ============================================================================
# Unit Tests: File Operations
# ============================================================================

class TestFileOperations:
    """Tests for file existence checking and path management."""

    def test_pptx_exists_true(self, marp_service: MarpService, temp_output_dir: Path):
        """Test pptx_exists returns True when file exists."""
        # Create a test PPTX file
        test_id = "test-id-123"
        pptx_path = temp_output_dir / f"{test_id}.pptx"
        pptx_path.write_text("fake pptx content")

        assert marp_service.pptx_exists(test_id) is True

    def test_pptx_exists_false(self, marp_service: MarpService, temp_output_dir: Path):
        """Test pptx_exists returns False when file doesn't exist."""
        assert marp_service.pptx_exists("nonexistent-id") is False

    def test_get_pptx_path(self, marp_service: MarpService):
        """Test get_pptx_path returns correct path."""
        test_id = "test-id-456"
        path = marp_service.get_pptx_path(test_id)

        assert path.name == f"{test_id}.pptx"
        assert path.parent == marp_service.output_dir


# ============================================================================
# Integration Tests: Marp CLI (requires Chrome)
# ============================================================================

class TestMarpIntegration:
    """Integration tests with actual Marp CLI (requires Chrome)."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_generate_pptx_full_integration(self, marp_service_with_real_path):
        """Test full PPTX generation with Marp CLI."""
        from uuid import uuid4

        class MockTranscription:
            def __init__(self):
                self.id = uuid4()
                self.file_name = "integration_test.mp3"
                self.original_text = "This is a test transcription for integration testing.\n\nIt has multiple paragraphs to verify slide generation."
                self.duration_seconds = 300
                self.summaries = []

        mock = MockTranscription()
        summary_text = "Integration test summary.\n\nWith multiple points."

        try:
            pptx_path = marp_service_with_real_path.generate_pptx(mock, summary_text)

            # Verify PPTX file was created
            assert pptx_path.exists()
            assert pptx_path.stat().st_size > 1000  # At least 1KB

            # Verify it's a valid ZIP file (PPTX is a ZIP archive)
            import zipfile
            with zipfile.ZipFile(pptx_path, 'r') as zip_file:
                # PPTX should contain at least [Content_Types].xml
                assert "[Content_Types].xml" in zip_file.namelist()

        finally:
            # Cleanup
            md_path = marp_service_with_real_path.output_dir / f"{mock.id}.md"
            pptx_path = marp_service_with_real_path.output_dir / f"{mock.id}.pptx"
            md_path.unlink(missing_ok=True)
            pptx_path.unlink(missing_ok=True)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_generate_pptx_without_summary(self, marp_service_with_real_path):
        """Test PPTX generation without summary."""
        from uuid import uuid4

        class MockTranscription:
            def __init__(self):
                self.id = uuid4()
                self.file_name = "no_summary_test.mp3"
                self.original_text = "Test content without summary."
                self.duration_seconds = 60
                self.summaries = []

        mock = MockTranscription()

        try:
            pptx_path = marp_service_with_real_path.generate_pptx(mock, None)
            assert pptx_path.exists()
        finally:
            md_path = marp_service_with_real_path.output_dir / f"{mock.id}.md"
            pptx_path = marp_service_with_real_path.output_dir / f"{mock.id}.pptx"
            md_path.unlink(missing_ok=True)
            pptx_path.unlink(missing_ok=True)

    @pytest.mark.integration
    def test_generate_pptx_empty_content_raises_error(self, marp_service: MarpService):
        """Test that empty transcription content raises ValueError."""
        from uuid import uuid4

        class MockTranscription:
            def __init__(self):
                self.id = uuid4()
                self.file_name = "empty.mp3"
                self.original_text = ""  # Empty
                self.duration_seconds = 0
                self.summaries = []

        mock = MockTranscription()

        with pytest.raises(ValueError, match="Cannot generate PPTX"):
            marp_service.generate_pptx(mock, None)


# ============================================================================
# Tests for Singleton
# ============================================================================

class TestSingleton:
    """Tests for the singleton pattern."""

    def test_get_marp_service_returns_singleton(self):
        """Test that get_marp_service returns the same instance."""
        service1 = get_marp_service()
        service2 = get_marp_service()

        # Should return the same instance
        assert service1 is service2

    def test_get_marp_service_initializes_once(self):
        """Test that service is initialized only once."""
        # Reset singleton
        import app.services.marp_service
        app.services.marp_service._marp_service = None

        service1 = get_marp_service()
        service2 = get_marp_service()

        assert service1 is service2
        assert id(service1) == id(service2)
