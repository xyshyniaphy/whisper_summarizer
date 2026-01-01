"""
Marp Markdown Generation Service

Generates Marp-compatible markdown from transcriptions for presentation creation.
Uses Gemini AI to intelligently structure content into topics.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any
import asyncio

from app.models.transcription import Transcription
from app.core.gemini import get_gemini_client

logger = logging.getLogger(__name__)


# Prompt for structuring transcription into Marp presentation format
STRUCTURE_PROMPT = """你是一个专业的演示文稿设计师。请将这段转录文本转换为结构化的Marp Markdown演示文稿。

转录内容:
{transcription_text}

输出格式（只返回JSON，不要有其他文字）:
{{
  "title": "从文件名或内容提取的标题",
  "topics": [
    {{"title": "主题标题", "content": "要点1\\n要点2\\n要点3"}},
    {{"title": "另一个主题", "content": "要点1\\n要点2\\n要点3"}}
  ],
  "summary": ["总结要点1", "总结要点2", "总结要点3", "总结要点4"],
  "appointments": ["后续安排1", "后续安排2"]
}}

要求:
- 提取3-5个主要主题
- 每个主题用3-5个简洁的要点说明
- 总结最多4-5行
- 后续安排：未来的日期、截止日期、行动项、待办事项
- 如果没有明确的后续安排，返回空数组
- 只返回JSON，不要有其他文字或解释
- content字段中的要点用\\n分隔"""


class MarpService:
    """Service for generating Marp-compatible markdown from transcriptions."""

    def __init__(
        self,
        output_dir: Path = Path("/app/data/output"),
        theme: str = "gaia",
        size: str = "16:9"
    ):
        """
        Initialize Marp service.

        Args:
            output_dir: Directory to save generated markdown files
            theme: Marp theme (gaia, default, uncover)
            size: Slide size (16:9, 4:3)
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.theme = theme
        self.size = size
        self.gemini_client = get_gemini_client()

    async def generate_markdown(
        self,
        transcription: Transcription,
        summary_text: str | None = None
    ) -> str:
        """
        Generate Marp-compatible markdown from transcription.

        Args:
            transcription: Transcription model instance
            summary_text: Optional AI summary text

        Returns:
            Markdown string in Marp format

        Raises:
            ValueError: If transcription has no content
            Exception: If AI generation fails
        """
        if not transcription.text:
            raise ValueError("Cannot generate markdown: transcription has no content")

        # Step 1: Use AI to structure the content
        structure = await self._create_structure_from_ai(transcription)

        # Step 2: Build Marp markdown
        markdown = self._build_marp_markdown(structure, transcription)

        return markdown

    async def _create_structure_from_ai(self, transcription: Transcription) -> dict[str, Any]:
        """
        Use Gemini AI to structure transcription into presentation format.

        Args:
            transcription: Transcription model instance

        Returns:
            Dictionary with title, topics, summary, appointments

        Raises:
            Exception: If AI generation or parsing fails
        """
        # Create prompt for AI
        prompt = STRUCTURE_PROMPT.format(
            transcription_text=transcription.text[:15000]  # Limit length
        )

        # Call Gemini API - use generate_summary with custom prompt
        response = await self.gemini_client.generate_summary(
            transcription=transcription.text[:15000],
            file_name=transcription.file_name,
            system_prompt=prompt
        )

        ai_response = response.summary

        # Parse JSON response
        try:
            # Extract JSON from response (AI may add surrounding text)
            json_start = ai_response.find("{")
            json_end = ai_response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in AI response")

            json_str = ai_response[json_start:json_end]
            structure = json.loads(json_str)

            # Validate structure
            required_keys = ["title", "topics", "summary", "appointments"]
            for key in required_keys:
                if key not in structure:
                    structure[key] = [] if key in ["summary", "appointments"] else ""

            return structure

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"AI response: {ai_response[:5000]}")
            raise Exception(f"Failed to parse AI response: {e}")

    def _build_marp_markdown(
        self,
        structure: dict[str, Any],
        transcription: Transcription
    ) -> str:
        """
        Build Marp markdown from structured content.

        Args:
            structure: Dictionary with title, topics, summary, appointments
            transcription: Transcription model instance

        Returns:
            Complete Marp markdown string
        """
        lines = []

        # Frontmatter
        lines.append("---")
        lines.append(f"theme: {self.theme}")
        lines.append(f"size: {self.size}")
        lines.append("style: |")
        lines.append("  section {")
        lines.append("    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', 'SimHei', sans-serif;")
        lines.append("    font-size: 24px;")
        lines.append("  }")
        lines.append("  h1, h2, h3 {")
        lines.append("    font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', 'SimHei', sans-serif;")
        lines.append("  }")
        lines.append("---")
        lines.append("")

        # Slide 1: Title slide
        lines.append("# <!-- fit --> " + structure.get("title", transcription.file_name))
        lines.append("")
        lines.append("*转录文档*")
        if transcription.duration_seconds:
            minutes = int(transcription.duration_seconds // 60)
            seconds = int(transcription.duration_seconds % 60)
            lines.append(f"*时长: {minutes}:{seconds:02d}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Slide 2: Table of Contents
        lines.append("## 目录")
        lines.append("")
        for topic in structure.get("topics", []):
            title = topic.get("title", "")
            lines.append(f"- {title}")
        if structure.get("summary"):
            lines.append("- 总结")
        if structure.get("appointments"):
            lines.append("- 后续安排")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Slides 3+: Topics
        for topic in structure.get("topics", []):
            title = topic.get("title", "")
            content = topic.get("content", "")

            lines.append(f"## {title}")
            lines.append("")

            # Split content by newlines and create bullet points
            if content:
                for point in content.split("\\n"):
                    point = point.strip()
                    if point:
                        lines.append(f"- {point}")

            lines.append("")
            lines.append("---")
            lines.append("")

        # Slide: Summary
        if structure.get("summary"):
            lines.append("## 总结")
            lines.append("")
            for point in structure["summary"][:5]:  # Max 5 lines
                lines.append(f"- {point}")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Slide: Future appointments
        if structure.get("appointments"):
            lines.append("## 后续安排")
            lines.append("")
            for appointment in structure["appointments"]:
                lines.append(f"- {appointment}")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Remove trailing separator if any
        if lines and lines[-1] == "---":
            lines = lines[:-1]
        if lines and lines[-1] == "":
            lines = lines[:-1]

        return "\n".join(lines)

    def save_markdown(
        self,
        transcription_id: str,
        markdown: str
    ) -> Path:
        """
        Save markdown to file.

        Args:
            transcription_id: Transcription ID
            markdown: Markdown content

        Returns:
            Path to saved markdown file
        """
        output_path = self.output_dir / f"{transcription_id}.md"
        output_path.write_text(markdown, encoding="utf-8")
        logger.info(f"Saved markdown to {output_path}")
        return output_path

    def convert_to_pptx(
        self,
        markdown_path: Path,
        output_path: Path | None = None
    ) -> Path:
        """
        Convert markdown to PPTX using Marp CLI.

        Args:
            markdown_path: Path to markdown file
            output_path: Optional output path (defaults to markdown_path with .pptx)

        Returns:
            Path to generated PPTX file

        Raises:
            Exception: If Marp CLI conversion fails
        """
        if output_path is None:
            output_path = markdown_path.with_suffix(".pptx")

        # Marp CLI command
        cmd = [
            "marp",
            str(markdown_path),
            "-o", str(output_path),
            "--theme", self.theme,
            "--allow-local-files"
        ]

        try:
            logger.info(f"Running Marp CLI: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            logger.info(f"Marp conversion successful: {output_path}")
            if result.stdout:
                logger.debug(f"Marp stdout: {result.stdout[:1000]}")

            return output_path

        except subprocess.TimeoutExpired:
            raise Exception(f"Marp CLI timeout after 60 seconds")
        except subprocess.CalledProcessError as e:
            logger.error(f"Marp CLI error: {e.stderr[:1000]}")
            raise Exception(f"Marp CLI conversion failed: {e.stderr}")
        except FileNotFoundError:
            raise Exception("Marp CLI not found. Install with: npm install -g @marp-team/marp-cli")

    def markdown_exists(self, transcription_id: str) -> bool:
        """Check if markdown file exists for given transcription."""
        markdown_path = self.output_dir / f"{transcription_id}.md"
        return markdown_path.exists()

    def get_markdown_path(self, transcription_id: str) -> Path:
        """Get the path to markdown file for given transcription."""
        return self.output_dir / f"{transcription_id}.md"

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
    return _marp_service
