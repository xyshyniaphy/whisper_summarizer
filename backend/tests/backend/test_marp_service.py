"""
Test suite for Marp Markdown Generation Service.

Tests cover:
- Service initialization and singleton pattern
- Markdown generation (async)
- File operations (save, exists, get path)
- PPTX conversion
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest

from app.services.marp_service import MarpService, get_marp_service


# ============================================================================
# Service Initialization Tests
# ============================================================================

class TestMarpServiceInitialization:
    """Tests for MarpService initialization."""

    def test_init_with_default_output_dir(self):
        """Test that service initializes with default output directory."""
        service = MarpService()
        assert service.output_dir == Path("/app/data/output")
        assert service.theme == "gaia"
        assert service.size == "16:9"

    def test_init_with_custom_output_dir(self, temp_output_dir: Path):
        """Test that service initializes with custom output directory."""
        service = MarpService(output_dir=temp_output_dir)
        assert service.output_dir == temp_output_dir

    def test_output_directory_created(self):
        """Test that output directory is created on initialization."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            service = MarpService(output_dir=output_dir)
            assert output_dir.exists()
            assert output_dir.is_dir()


# ============================================================================
# Singleton Pattern Tests
# ============================================================================

class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_marp_service_returns_singleton(self):
        """Test that get_marp_service returns singleton instance."""
        service1 = get_marp_service()
        service2 = get_marp_service()
        assert service1 is service2

    def test_get_marp_service_initializes_once(self):
        """Test that service is only initialized once."""
        service1 = get_marp_service()
        service2 = get_marp_service()
        assert id(service1) == id(service2)


# ============================================================================
# File Operations Tests
# ============================================================================

class TestFileOperations:
    """Tests for file operations."""

    def test_save_markdown_creates_file(self, marp_service: MarpService):
        """Test that save_markdown creates a markdown file."""
        test_id = str(uuid4())
        markdown = "# Test\n\nContent"

        output_path = marp_service.save_markdown(test_id, markdown)

        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == markdown

    def test_markdown_exists_true(self, marp_service: MarpService):
        """Test that markdown_exists returns True when file exists."""
        test_id = str(uuid4())
        markdown = "# Test"
        marp_service.save_markdown(test_id, markdown)

        assert marp_service.markdown_exists(test_id) is True

    def test_markdown_exists_false(self, marp_service: MarpService):
        """Test that markdown_exists returns False when file does not exist."""
        assert marp_service.markdown_exists("nonexistent") is False

    def test_get_markdown_path(self, marp_service: MarpService):
        """Test that get_markdown_path returns correct path."""
        test_id = str(uuid4())
        expected_path = marp_service.output_dir / f"{test_id}.md"

        assert marp_service.get_markdown_path(test_id) == expected_path

    def test_pptx_exists_true(self, marp_service: MarpService):
        """Test that pptx_exists returns True when file exists."""
        test_id = str(uuid4())
        pptx_path = marp_service.output_dir / f"{test_id}.pptx"
        pptx_path.write_text("fake pptx")

        assert marp_service.pptx_exists(test_id) is True

    def test_pptx_exists_false(self, marp_service: MarpService):
        """Test that pptx_exists returns False when file does not exist."""
        assert marp_service.pptx_exists("nonexistent") is False

    def test_get_pptx_path(self, marp_service: MarpService):
        """Test that get_pptx_path returns correct path."""
        test_id = str(uuid4())
        expected_path = marp_service.output_dir / f"{test_id}.pptx"

        assert marp_service.get_pptx_path(test_id) == expected_path


# ============================================================================
# Markdown Generation Tests
# ============================================================================

class TestMarkdownGeneration:
    """Tests for markdown generation."""

    @pytest.mark.asyncio
    async def test_generate_markdown_basic_structure(self, marp_service: MarpService, mock_transcription):
        """Test that generate_markdown creates valid Marp structure."""
        # Mock the AI client
        mock_response = MagicMock()
        mock_response.summary = "{\"title\": \"Test Title\", \"topics\": [{\"title\": \"Topic 1\", \"content\": \"Point 1\\nPoint 2\\nPoint 3\"}, {\"title\": \"Topic 2\", \"content\": \"Point A\\nPoint B\"}], \"summary\": [\"Summary 1\", \"Summary 2\"], \"appointments\": [\"Task 1\", \"Task 2\"]}"

        with patch.object(marp_service.gemini_client, "generate_summary", new=AsyncMock(return_value=mock_response)):
            markdown = await marp_service.generate_markdown(mock_transcription)

            # Verify frontmatter
            assert markdown.startswith("---")
            assert "theme: gaia" in markdown
            assert "size: 16:9" in markdown

            # Verify title slide
            assert "# <!-- fit --> Test Title" in markdown

            # Verify table of contents
            assert "## 目录" in markdown
            assert "- Topic 1" in markdown
            assert "- Topic 2" in markdown

            # Verify topics
            assert "## Topic 1" in markdown
            assert "- Point 1" in markdown
            assert "- Point 2" in markdown

            # Verify summary
            assert "## 总结" in markdown
            assert "- Summary 1" in markdown

            # Verify appointments
            assert "## 后续安排" in markdown
            assert "- Task 1" in markdown

    @pytest.mark.asyncio
    async def test_generate_markdown_with_empty_transcription(self, marp_service: MarpService):
        """Test that generate_markdown raises error for empty transcription."""
        class EmptyTranscription:
            text = ""
            file_name = "empty.mp3"
            duration_seconds = 0

        with pytest.raises(ValueError, match="Cannot generate markdown: transcription has no content"):
            await marp_service.generate_markdown(EmptyTranscription())

    @pytest.mark.asyncio
    async def test_generate_markdown_with_missing_json_keys(self, marp_service: MarpService, mock_transcription):
        """Test that generate_markdown handles incomplete AI response."""
        # Mock AI response with missing keys
        mock_response = MagicMock()
        mock_response.summary = "{\"title\": \"Test\"}"

        with patch.object(marp_service.gemini_client, "generate_summary", new=AsyncMock(return_value=mock_response)):
            markdown = await marp_service.generate_markdown(mock_transcription)

            # Should still work with defaults
            assert markdown.startswith("---")
            assert "## Test" in markdown

    @pytest.mark.asyncio
    async def test_generate_markdown_with_json_extraneous_text(self, marp_service: MarpService, mock_transcription):
        """Test that generate_markdown extracts JSON from AI response with extra text."""
        # Mock AI response with surrounding text
        mock_response = MagicMock()
        mock_response.summary = "Here is the structured content:\n\n{\"title\": \"Test\", \"topics\": [], \"summary\": [], \"appointments\": []}\n\nHope this helps!"

        with patch.object(marp_service.gemini_client, "generate_summary", new=AsyncMock(return_value=mock_response)):
            markdown = await marp_service.generate_markdown(mock_transcription)

            assert markdown.startswith("---")

    @pytest.mark.asyncio
    async def test_generate_markdown_ai_failure(self, marp_service: MarpService, mock_transcription):
        """Test that generate_markdown handles AI failure."""
        # Mock AI returning non-JSON
        mock_response = MagicMock()
        mock_response.summary = "This is not valid JSON at all"

        with patch.object(marp_service.gemini_client, "generate_summary", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(Exception, match="Failed to parse AI response"):
                await marp_service.generate_markdown(mock_transcription)

    @pytest.mark.asyncio
    async def test_generate_markdown_no_topics_in_summary(self, marp_service: MarpService, mock_transcription):
        """Test that generate_markdown handles response with no topics."""
        mock_response = MagicMock()
        mock_response.summary = "{\"title\": \"Test\", \"topics\": [], \"summary\": [\"Summary\"], \"appointments\": []}"

        with patch.object(marp_service.gemini_client, "generate_summary", new=AsyncMock(return_value=mock_response)):
            markdown = await marp_service.generate_markdown(mock_transcription)

            # Should work, just no topic slides
            assert "## 总结" in markdown

    @pytest.mark.asyncio
    async def test_generate_markdown_long_transcription(self, marp_service: MarpService, mock_long_transcription):
        """Test that generate_markdown truncates long content."""
        mock_response = MagicMock()
        mock_response.summary = "{\"title\": \"Long Audio\", \"topics\": [], \"summary\": [], \"appointments\": []}"

        with patch.object(marp_service.gemini_client, "generate_summary", new=AsyncMock(return_value=mock_response)):
            markdown = await marp_service.generate_markdown(mock_long_transcription)

            assert markdown.startswith("---")


# ============================================================================
# PPTX Conversion Tests
# ============================================================================

class TestPPTXConversion:
    """Tests for PPTX conversion."""

    def test_convert_to_pptx_success(self, marp_service: MarpService):
        """Test successful PPTX conversion."""
        # Create a test markdown file
        test_id = str(uuid4())
        markdown = "# Test\n\n---\n\n## Slide 2"
        md_path = marp_service.save_markdown(test_id, markdown)

        # Mock subprocess.run
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Success", stderr="", returncode=0)

            pptx_path = marp_service.convert_to_pptx(md_path)

            assert pptx_path.exists()
            assert pptx_path.suffix == ".pptx"
            # Verify Marp CLI was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert "marp" in call_args[0][0]
            assert str(md_path) in call_args[0][0]

    def test_convert_to_pptx_custom_output_path(self, marp_service: MarpService):
        """Test PPTX conversion with custom output path."""
        test_id = str(uuid4())
        markdown = "# Test"
        md_path = marp_service.save_markdown(test_id, markdown)
        custom_path = marp_service.output_dir / "custom_output.pptx"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
            custom_path.touch()  # Simulate file creation

            pptx_path = marp_service.convert_to_pptx(md_path, custom_path)

            assert pptx_path == custom_path

    def test_convert_to_pptx_marp_not_found(self, marp_service: MarpService):
        """Test PPTX conversion when Marp CLI is not installed."""
        test_id = str(uuid4())
        markdown = "# Test"
        md_path = marp_service.save_markdown(test_id, markdown)

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(Exception, match="Marp CLI not found"):
                marp_service.convert_to_pptx(md_path)

    def test_convert_to_pptx_timeout(self, marp_service: MarpService):
        """Test PPTX conversion timeout."""
        test_id = str(uuid4())
        markdown = "# Test"
        md_path = marp_service.save_markdown(test_id, markdown)

        with patch("subprocess.run", side_effect=Exception("timeout")):
            with pytest.raises(Exception):
                marp_service.convert_to_pptx(md_path)

    def test_convert_to_pptx_marp_error(self, marp_service: MarpService):
        """Test PPTX conversion when Marp CLI returns error."""
        test_id = str(uuid4())
        markdown = "# Test"
        md_path = marp_service.save_markdown(test_id, markdown)

        mock_error = MagicMock()
        mock_error.stderr = "Marp conversion failed"

        with patch("subprocess.run", side_effect=Exception("Marp CLI error")):
            with pytest.raises(Exception):
                marp_service.convert_to_pptx(md_path)


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_generate_and_save(self, marp_service: MarpService, mock_transcription):
        """Test full workflow: generate markdown and save to file."""
        mock_response = MagicMock()
        mock_response.summary = "{\"title\": \"Full Test\", \"topics\": [{\"title\": \"T1\", \"content\": \"P1\\nP2\"}], \"summary\": [\"S1\"], \"appointments\": []}"

        with patch.object(marp_service.gemini_client, "generate_summary", new=AsyncMock(return_value=mock_response)):
            # Generate markdown
            markdown = await marp_service.generate_markdown(mock_transcription)

            # Save to file
            test_id = str(mock_transcription.id)
            output_path = marp_service.save_markdown(test_id, markdown)

            # Verify file exists and has correct content
            assert output_path.exists()
            saved_content = output_path.read_text(encoding="utf-8")
            assert saved_content == markdown
            assert "## T1" in saved_content
            assert "Full Test" in saved_content

    def test_check_file_existence_workflow(self, marp_service: MarpService):
        """Test checking file existence before and after creation."""
        test_id = str(uuid4())

        # Initially does not exist
        assert marp_service.markdown_exists(test_id) is False
        assert marp_service.pptx_exists(test_id) is False

        # Create markdown
        markdown = "# Test"
        marp_service.save_markdown(test_id, markdown)

        # Now markdown exists
        assert marp_service.markdown_exists(test_id) is True
        assert marp_service.pptx_exists(test_id) is False

        # Create fake PPTX
        pptx_path = marp_service.output_dir / f"{test_id}.pptx"
        pptx_path.write_bytes(b"fake pptx")

        # Now both exist
        assert marp_service.markdown_exists(test_id) is True
        assert marp_service.pptx_exists(test_id) is True
