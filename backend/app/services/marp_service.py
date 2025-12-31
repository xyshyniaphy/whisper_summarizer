"""
MARP PPTX Generation Service

Creates PowerPoint presentations using Marp CLI from Markdown.
"""

import subprocess
import logging
from pathlib import Path
from datetime import datetime

from app.models.transcription import Transcription

logger = logging.getLogger(__name__)


class MarpService:
    """Service for generating PowerPoint presentations using Marp CLI."""

    # Characters per slide (rough estimate for content fitting)
    CHARS_PER_SLIDE = 800
    # Maximum slides for content (to prevent huge files)
    MAX_CONTENT_SLIDES = 50

    def __init__(self, output_dir: Path = Path("/app/data/output")):
        """
        Initialize Marp service.

        Args:
            output_dir: Directory to save generated PPTX files
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_pptx(
        self,
        transcription: Transcription,
        summary_text: str | None = None
    ) -> Path:
        """
        Generate a PowerPoint presentation using Marp CLI.

        Args:
            transcription: Transcription model instance
            summary_text: Optional AI summary text

        Returns:
            Path to the generated PPTX file

        Raises:
            ValueError: If transcription has no content
            RuntimeError: If Marp CLI execution fails
        """
        if not transcription.original_text:
            raise ValueError("Cannot generate PPTX: transcription has no content")

        # Generate Marp Markdown content
        markdown_content = self._generate_marp_markdown(transcription, summary_text)

        # Write Markdown to temporary file
        md_path = self.output_dir / f"{transcription.id}.md"
        md_path.write_text(markdown_content, encoding="utf-8")

        # Run Marp CLI to convert to PPTX
        pptx_path = self.output_dir / f"{transcription.id}.pptx"

        try:
            result = subprocess.run(
                [
                    "marp",
                    str(md_path),
                    "--no-stdin",
                    "--allow-local-files",
                    "-o", str(pptx_path)
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                check=True
            )
            logger.info(f"Marp CLI output: {result.stdout}")

            # Clean up temporary Markdown file
            md_path.unlink(missing_ok=True)

            return pptx_path

        except subprocess.TimeoutExpired:
            logger.error(f"Marp CLI timeout for transcription {transcription.id}")
            raise RuntimeError("PPTX generation timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"Marp CLI failed: {e.stderr}")
            raise RuntimeError(f"PPTX generation failed: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error during PPTX generation: {e}")
            raise RuntimeError(f"PPTX generation error: {e}")

    def _generate_marp_markdown(
        self,
        transcription: Transcription,
        summary_text: str | None = None
    ) -> str:
        """
        Generate Marp Markdown content from transcription data.

        Args:
            transcription: Transcription model instance
            summary_text: Optional AI summary text

        Returns:
            Marp-formatted Markdown string
        """
        # Frontmatter
        frontmatter = """---
marp: true
theme: gaia
paginate: true
backgroundColor: #fff
color: #333
style: |
  section {
    font-family: 'Helvetica', 'Noto Sans SC', sans-serif;
    font-size: 24px;
  }
  h1 {
    color: #1971c2;
  }
  h2 {
    color: #1864ab;
  }
  strong {
    color: #1971c2;
  }
---

<!-- _class: lead -->

"""

        # Title slide
        duration_info = ""
        if transcription.duration_seconds:
            minutes = int(transcription.duration_seconds // 60)
            seconds = int(transcription.duration_seconds % 60)
            duration_info = f" | 时长: {minutes}:{seconds:02d}"

        title_slide = f"""# {transcription.file_name}

转录文档{duration_info} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

# 目录

- 转录内容
- AI摘要

---

"""

        # AI Summary slide (if available)
        summary_slides = ""
        if summary_text:
            summary_slides = self._create_summary_slides(summary_text)

        # Content slides
        content_slides = self._create_content_slides(transcription.original_text)

        return frontmatter + title_slide + summary_slides + content_slides

    def _create_summary_slides(self, summary_text: str) -> str:
        """Create Marp slides for AI summary."""
        # Split into paragraphs and create bullet points
        paragraphs = [p.strip() for p in summary_text.split('\n\n') if p.strip()]

        bullets = "\n".join(f"- {para}" for para in paragraphs[:10])  # Max 10 bullets

        return f"""# AI 摘要

{bullets}

---

"""

    def _create_content_slides(self, content: str) -> str:
        """Create Marp slides for transcription content."""
        # Split content into chunks
        chunks = self._chunk_content(content)

        slides = []
        for i, chunk in enumerate(chunks, start=1):
            if len(chunks) > 1:
                title = f"# 转录内容 ({i}/{len(chunks)})"
            else:
                title = "# 转录内容"

            # Convert chunk content to slides with proper formatting
            formatted_content = self._format_content_for_marp(chunk)
            slides.append(f"""{title}

{formatted_content}

---
""")

        return "\n".join(slides)

    def _format_content_for_marp(self, content: str) -> str:
        """
        Format content for Marp Markdown.

        - Preserve paragraph structure
        - Escape special Markdown characters
        - Limit line length for readability
        """
        lines = content.split('\n')
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Escape special Markdown characters but preserve basic formatting
            line = self._escape_markdown(line)
            formatted_lines.append(line)

        return "\n\n".join(formatted_lines)

    def _escape_markdown(self, text: str) -> str:
        """
        Escape special Markdown characters.

        Note: We intentionally don't escape some characters like *, _ to allow
        basic formatting that LLMs might generate.
        """
        # Characters that must be escaped in Markdown
        special_chars = {
            '#': '\\#',
            '`': '\\`',
            '[': '\\[',
            ']': '\\]',
            '<': '\\<',
            '>': '\\>',
            '|': '\\|',
        }

        for char, escaped in special_chars.items():
            text = text.replace(char, escaped)

        return text

    def _chunk_content(self, content: str) -> list[str]:
        """
        Split long content into chunks suitable for slides.

        Args:
            content: Full transcription text

        Returns:
            List of content chunks
        """
        if len(content) <= self.CHARS_PER_SLIDE:
            return [content]

        chunks = []
        current_chunk = []
        current_length = 0
        slide_count = 0

        # Split by lines first to preserve paragraph structure
        lines = content.split('\n')

        for line in lines:
            line_length = len(line) + 1  # +1 for newline

            # Check if we need a new slide
            if (current_length + line_length > self.CHARS_PER_SLIDE and
                    current_chunk):
                # Check if we're about to exceed max slides
                if slide_count >= self.MAX_CONTENT_SLIDES - 1:
                    # Append truncation to current chunk (last chunk) and stop
                    current_chunk.append(f"\n[内容过长，已截断。前 {slide_count + 1} 张幻灯片已包含前 "
                                        f"{(slide_count + 1) * self.CHARS_PER_SLIDE} 字符]")
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []  # Clear to prevent adding extra chunk after loop
                    break
                # Add current chunk and start a new one
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
                slide_count += 1

            current_chunk.append(line)
            current_length += line_length

        # Add remaining content (only if we haven't hit the limit)
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def pptx_exists(self, transcription_id: str) -> bool:
        """Check if PPTX file exists for given transcription."""
        pptx_path = self.output_dir / f"{transcription_id}.pptx"
        return pptx_path.exists()

    def get_pptx_path(self, transcription_id: str) -> Path:
        """Get the path to PPTX file for given transcription."""
        return self.output_dir / f"{transcription_id}.pptx"


# Singleton instance
_marp_service: MarpService | None = None


def get_marp_service() -> MarpService:
    """Get or create the singleton Marp service instance."""
    global _marp_service
    if _marp_service is None:
        _marp_service = MarpService()
        logger.info("Initialized Marp service")
    return _marp_service
