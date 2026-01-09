"""
NotebookLM Guideline Service

Generates guidelines for NotebookLM to create presentation slides
based on transcription content.
"""

import logging
import os
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# Hardcoded NotebookLM spec prompt
NOTEBOOKLM_SYSTEM_PROMPT = """**角色设定：**
你是一位资深的佛学内容整理专家及演示文稿架构师。你的任务是深入研读提供的佛学讲座、法会或研讨记录，将其转化为一份庄重、严谨且结构清晰的演示文稿大纲，专供 NotebookLM 使用。

**输入内容：**
用户提供的佛学相关的会议或讲座记录文本。

**输出要求：**
1.  **语言：** 全文必须使用**简体中文**。
2.  **篇幅：** 输出内容必须严格控制在 **10 到 15 页** 幻灯片之间。内容需详实深奥，避免过于浅显。
3.  **格式：** 使用标准的 Markdown 格式。每一页幻灯片需清晰标记（例如：`## 幻灯片 1：[标题]`）。
4.  **风格：** 庄重、清净、富有智慧，使用符合佛教传统的专业术语。

**结构框架（必须包含以下六个部分）：**
请根据记录内容的逻辑，将 10-15 页幻灯片合理分配到以下章节中：

1.  **概述**（建议 1-2 页）
    * 介绍讲座/会议缘起、主讲人、参与对象及本次研讨的核心宗旨。

2.  **主要要点**（建议 2-3 页）
    * 提炼本次交流中最重要的核心法义、教理结论或达成的共识。

3.  **详细信息**（建议 3-4 页）
    * 对应原定"详细信息"。详细拆解具体的佛法义理（如：引用经典、譬喻故事、具体法相名词解释、因果逻辑等）。

4.  **核心议题探讨**（建议 2-3 页）
    * 对应原定"Topics"。将讨论内容按佛法主题归类（例如："戒定慧三学"、"空性智慧"、"慈悲观修"、"具体经典研读"等），每页专注于一个主题。

5.  **义理辨析与挑战**（建议 1-2 页）
    * 对应原定"Difficult Points"。识别在理解教义时的难点、修行中可能遇到的障碍、常见的知见误区或本次研讨中存在的争议点。

6.  **修行建议与未来展望**（建议 1-2 页）
    * 对应原定"Future Plans"。列出具体的修行指导建议（Action Items）、后续课程或法会安排、以及弘法利生的长远规划。

**每一页幻灯片的撰写规范：**
* **标题：** 简练典雅，概括该页核心法义。
* **列表内容：** 每页必须包含 3 到 5 个详细的要点。请使用完整的句子进行阐述，确保义理通顺，逻辑严密。
* **信息密度：** 确保内容具有深度，能够体现佛法的智慧。

**操作指令：**
请在接收到用户提供的文本后，立即按照上述佛学语境要求生成全中文的演示文稿大纲。"""


class NotebookLMService:
    """Service for generating NotebookLM presentation guidelines."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "GLM-4.5-Air"
    ):
        """
        Initialize NotebookLM service.

        Args:
            api_key: GLM API Key (from env GLM_API_KEY if not provided)
            base_url: API base URL (from env GLM_BASE_URL if not provided)
            model: Model name to use for generation
        """
        self.api_key = api_key or os.getenv("GLM_API_KEY")
        self.base_url = base_url or os.getenv("GLM_BASE_URL", "https://api.z.ai/api/paas/v4/")
        self.model = model

        if not self.api_key:
            raise ValueError("GLM_API_KEY is not configured")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        logger.info(f"NotebookLMService initialized with model: {self.model}")

    def _load_spec_prompt(self) -> str:
        """
        Return the hardcoded NotebookLM spec prompt.

        Returns:
            str: The spec prompt content
        """
        logger.debug(f"Using hardcoded NotebookLM prompt ({len(NOTEBOOKLM_SYSTEM_PROMPT)} chars)")
        return NOTEBOOKLM_SYSTEM_PROMPT

    def generate_guideline(self, transcription_text: str, file_name: str = None) -> str:
        """
        Generate a NotebookLM guideline based on transcription text.

        The guideline follows the spec in spec/notebooklm.md and provides
        structured instructions for NotebookLM to create presentation slides.

        Args:
            transcription_text: The transcription text to base the guideline on
            file_name: Optional file name for logging

        Returns:
            str: The generated guideline text

        Raises:
            Exception: If generation fails
        """
        import time

        if not transcription_text or len(transcription_text.strip()) < 50:
            raise ValueError("Transcription text is too short to generate guideline")

        # Load the spec prompt
        system_prompt = self._load_spec_prompt()

        start_time = time.time()

        try:
            # Truncate transcription if too long (keep first 10000 chars for context)
            # NotebookLM will work with the actual source, this is just for guidance
            max_input_length = 15000
            input_text = transcription_text[:max_input_length]
            if len(transcription_text) > max_input_length:
                logger.info(f"Transcription truncated from {len(transcription_text)} to {max_input_length} chars for guideline generation")

            # Generate guideline using GLM API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请根据以下转录文本生成 NotebookLM 演示文稿大纲指南：\n\n{input_text}"}
                ],
                temperature=0.7,
                max_tokens=4000,
            )

            response_time_ms = (time.time() - start_time) * 1000

            # Extract guideline from response
            guideline = response.choices[0].message.content

            # Get token usage
            input_tokens = response.usage.prompt_tokens if response.usage else None
            output_tokens = response.usage.completion_tokens if response.usage else None
            total_tokens = response.usage.total_tokens if response.usage else None

            logger.info(
                f"Generated NotebookLM guideline (file: {file_name}, "
                f"length: {len(guideline)} chars, "
                f"tokens: {total_tokens}, "
                f"time: {response_time_ms:.0f}ms)"
            )

            return guideline

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Failed to generate NotebookLM guideline: {e}")
            raise Exception(f"Guideline generation failed: {str(e)}")


# Singleton instance
_notebooklm_service: Optional[NotebookLMService] = None


def get_notebooklm_service() -> NotebookLMService:
    """Get or create the singleton NotebookLMService instance."""
    global _notebooklm_service
    if _notebooklm_service is None:
        _notebooklm_service = NotebookLMService()
        logger.info("NotebookLMService initialized")
    return _notebooklm_service
