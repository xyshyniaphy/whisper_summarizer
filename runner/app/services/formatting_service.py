"""
Text Formatting Service

Uses GLM-4.5-Air to format transcribed text by adding punctuation,
fixing capitalization, and improving readability without changing meaning.
"""

import logging
import os
from typing import List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# NotebookLM system prompt for generating presentation guidelines
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


class TextFormattingService:
    """Service for formatting transcribed text using LLM."""

    # Format-only system prompt - strict instruction to NOT summarize or explain
    FORMAT_SYSTEM_PROMPT = """你是一个专业的语音转写文本格式化专家。你的任务是为中文语音转录文本添加标点符号和段落结构，使其具有可读性，同时严格保持原意不变。

## 格式化规则

### 标点符号
- 根据语义添加合适的标点：逗号（，）、句号（。）、问号（？）、感叹号（！）
- 对话内容使用引号（""）和冒号（：）
- 列举或并列使用顿号（、）或分号（；）
- 补充说明使用括号（（））
- 话题转折使用破折号（——）

### 段落结构
- 每段不超过200字，过长时按语义分段
- 新话题开始时另起一段
- 明显的讲话停顿处可以分段

### 大小写和数字
- 专有名词（人名、地名、机构名）首字母保持或添加大写
- 数字统一使用阿拉伯数字（1, 2, 3）
- 时间格式：2024年1月2日、下午3点

### 处理语气词
- 明显的口语语气词（嗯、啊、那个、然后、就是）可以删除
- 但不能因此改变句子的原意
- 如果删除后句子不通顺，则保留

## 严格限制
- **不要**总结或解释内容
- **不要**添加原文中没有的信息
- **不要**改变原文的叙述顺序
- **只**返回格式化后的文本，不要有任何前言或后语

## 示例

输入：
今天我们要讨论的是关于人工智能的发展首先呢人工智能已经在我们生活中有很多应用比如说手机里面的语音助手还有自动驾驶等等那么这些技术是如何工作的呢

输出：
今天我们要讨论的是关于人工智能的发展。首先，人工智能已经在我们生活中有很多应用，比如说手机里面的语音助手、自动驾驶等等。那么，这些技术是如何工作的呢？

输入：
嗯这个我觉得吧可能需要再考虑一下因为你也知道我们之前做过类似的项目但是结果不是很理想所以说这次我们可能需要更加谨慎

输出：
我觉得可能需要再考虑一下。你也知道，我们之前做过类似的项目，但结果不是很理想，所以这次我们可能需要更加谨慎。

## 输出格式
直接返回格式化后的文本，不要添加任何说明、引言或解释。"""

    def __init__(self):
        """Initialize the formatting service."""
        self.max_chunk_bytes = getattr(settings, 'MAX_FORMAT_CHUNK', 10000)
        self.glm_client = None
        self._init_glm_client()

    def _init_glm_client(self):
        """Initialize GLM client (lazy import to avoid circular dependencies)."""
        try:
            from app.core.glm import get_glm_client
            self.glm_client = get_glm_client()
            logger.info("GLM client initialized for formatting service")
        except Exception as e:
            logger.error(f"Failed to initialize GLM client: {e}")
            self.glm_client = None

    def split_text_into_chunks(self, text: str) -> List[str]:
        """
        Split long text into chunks for LLM processing.

        Splits at whitespace near the middle of each chunk to avoid cutting words.
        Each chunk is approximately MAX_FORMAT_CHUNK bytes.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        if not text:
            return []

        text_bytes = len(text.encode('utf-8'))
        if text_bytes <= self.max_chunk_bytes:
            return [text]

        chunks = []
        remaining = text

        while remaining:
            remaining_bytes = len(remaining.encode('utf-8'))
            if remaining_bytes <= self.max_chunk_bytes:
                chunks.append(remaining.strip())
                break

            # Take a chunk slightly larger than max_bytes to find split point
            chunk_size = min(self.max_chunk_bytes + 1000, len(remaining))
            chunk = remaining[:chunk_size]

            # Find split point at whitespace in middle third of chunk
            # This avoids cutting at the very edges where context is lost
            search_start = len(chunk) // 3
            search_end = min(len(chunk), (len(chunk) * 2) // 3)

            # Search backwards from middle for whitespace
            split_at = -1
            for i in range(search_end, search_start, -1):
                if chunk[i].isspace():
                    split_at = i
                    break

            # If no whitespace found in middle, try entire chunk
            if split_at == -1:
                for i in range(len(chunk) - 1, 0, -1):
                    if chunk[i].isspace():
                        split_at = i
                        break

            # Last resort: force split at max_bytes
            if split_at == -1:
                split_at = self.max_chunk_bytes

            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()

        logger.info(f"Split text ({text_bytes} bytes) into {len(chunks)} chunks")
        return chunks

    def format_text_chunk(self, chunk: str) -> str:
        """
        Format a single chunk of text using GLM-4.5-Air.

        Args:
            chunk: Text chunk to format

        Returns:
            Formatted text

        Raises:
            Exception: If formatting fails
        """
        if not self.glm_client:
            logger.warning("GLM client not available, returning original text")
            return chunk

        try:
            logger.info(f"[FORMAT] Calling GLM API for chunk ({len(chunk)} chars)")
            # Use the OpenAI client directly from GLMClient
            response = self.glm_client.client.chat.completions.create(
                model=self.glm_client.model,
                messages=[
                    {"role": "system", "content": self.FORMAT_SYSTEM_PROMPT},
                    {"role": "user", "content": chunk}
                ],
                temperature=0.1,  # Low temperature for consistent formatting
                max_tokens=min(int(len(chunk) * 2), 4000)  # Allow more expansion
            )

            # Check both content and reasoning_content (GLM-4.5-Air uses reasoning)
            choice = response.choices[0]
            formatted = choice.message.content or ""

            # GLM-4.5-Air sometimes puts the actual answer in reasoning_content
            if not formatted and hasattr(choice.message, 'reasoning_content') and choice.message.reasoning_content:
                logger.warning("[FORMAT] Content is empty, checking reasoning_content")
                # Extract final answer from reasoning (usually at the end)
                reasoning = choice.message.reasoning_content
                # Look for the actual formatted text in the reasoning
                # The model typically outputs the formatted text at the very end
                lines = reasoning.split('\n')
                for line in reversed(lines):
                    line = line.strip()
                    # Skip empty lines and reasoning markers
                    if line and not line.startswith(('首先', '然后', '接下来', '让我', '我需要', '分析')):
                        # Found potential formatted text
                        formatted = line
                        break

            if formatted:
                formatted = formatted.strip()

            logger.info(f"[FORMAT] GLM returned {len(formatted) if formatted else 0} chars")
            logger.debug(f"[FORMAT] Finish reason: {choice.finish_reason}")

            # If formatted text is significantly shorter (< 50% of original), use original
            if formatted and len(formatted) < len(chunk) * 0.5:
                logger.warning(f"[FORMAT] Formatted text too short ({len(formatted)} < {len(chunk) * 0.5}), returning original")
                return chunk

            if not formatted:
                logger.warning(f"[FORMAT] GLM returned empty response, returning original text")
                return chunk

            return formatted

        except Exception as e:
            logger.error(f"[FORMAT] Failed to format text chunk: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Return original text on failure
            return chunk

    def format_transcription_text(self, text: str) -> str:
        """
        Format transcribed text by splitting into chunks and processing with LLM.

        Args:
            text: Raw transcribed text from Whisper

        Returns:
            Formatted text with proper punctuation and capitalization
        """
        if not text or len(text.strip()) < 50:
            # Too short to format, return as-is
            logger.info(f"Text too short to format ({len(text)} chars), returning original")
            return text

        # Split into chunks
        chunks = self.split_text_into_chunks(text)
        if len(chunks) == 1:
            logger.info(f"Formatting single chunk ({len(text)} chars)")
            return self.format_text_chunk(chunks[0])

        # Format chunks sequentially
        logger.info(f"Formatting {len(chunks)} chunks sequentially")
        formatted_chunks = []

        for i, chunk in enumerate(chunks, 1):
            logger.debug(f"Formatting chunk {i}/{len(chunks)} ({len(chunk)} chars)")
            formatted_chunk = self.format_text_chunk(chunk)
            formatted_chunks.append(formatted_chunk)

        # Join with paragraph breaks
        formatted_text = "\n\n".join(formatted_chunks)
        logger.info(f"Formatted complete text: {len(text)} -> {len(formatted_text)} chars")

        return formatted_text

    def format_transcription(
        self,
        raw_text: str,
        language: Optional[str] = None
    ) -> dict:
        """
        Format transcribed text and return formatted text, summary, and NotebookLM guideline.

        This method matches the interface expected by AudioProcessor.

        Args:
            raw_text: Raw transcribed text from Whisper
            language: Language code (e.g., "zh", "en", "ja")

        Returns:
            Dict with keys:
            - formatted_text: The formatted transcription text
            - summary: Generated summary
            - notebooklm_guideline: Generated NotebookLM presentation guideline
        """
        if not raw_text or len(raw_text.strip()) < 50:
            # Too short to format, return as-is
            logger.info(f"Text too short to format ({len(raw_text)} chars), returning original")
            return {
                "formatted_text": raw_text,
                "summary": "",
                "notebooklm_guideline": ""
            }

        try:
            # Format the text using the existing method
            formatted_text = self.format_transcription_text(raw_text)

            logger.info(f"Formatting complete: {len(raw_text)} -> {len(formatted_text)} chars")

            # Generate summary using GLM
            summary = self._generate_summary(formatted_text)

            # Generate NotebookLM guideline
            notebooklm_guideline = self._generate_notebooklm_guideline(formatted_text)

            return {
                "formatted_text": formatted_text,
                "summary": summary,
                "notebooklm_guideline": notebooklm_guideline
            }
        except Exception as e:
            logger.error(f"Error in format_transcription: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Return original text on failure
            return {
                "formatted_text": raw_text,
                "summary": "",
                "notebooklm_guideline": ""
            }

    def _generate_summary(self, text: str) -> str:
        """
        Generate a summary of the transcribed text using GLM.

        Args:
            text: Formatted transcribed text

        Returns:
            Generated summary or empty string if generation fails
        """
        if not self.glm_client:
            logger.warning("GLM client not available, skipping summary generation")
            return ""

        try:
            logger.info(f"[SUMMARY] Generating summary for text ({len(text)} chars)")

            # Generate summary synchronously using the OpenAI client directly
            from app.core.glm import get_glm_client

            # Get system prompt for summarization
            glm_client = get_glm_client()
            system_prompt = glm_client._get_system_prompt_by_language()

            # Use synchronous OpenAI client call
            response = glm_client.client.chat.completions.create(
                model=glm_client.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"以下の文字起こしテキストを要約してください:\n\n{text}"}
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            summary = response.choices[0].message.content or ""
            logger.info(f"[SUMMARY] Generated summary: {len(summary)} chars")

            return summary

        except Exception as e:
            logger.error(f"[SUMMARY] Failed to generate summary: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ""

    def _generate_notebooklm_guideline(self, text: str) -> str:
        """
        Generate a NotebookLM guideline for presentation slides using GLM.

        Args:
            text: Formatted transcribed text

        Returns:
            Generated NotebookLM guideline or empty string if generation fails
        """
        if not self.glm_client:
            logger.warning("GLM client not available, skipping NotebookLM guideline generation")
            return ""

        try:
            logger.info(f"[NOTEBOOKLM] Generating guideline for text ({len(text)} chars)")

            # Truncate text if too long (keep first 15000 chars for context)
            max_input_length = 15000
            input_text = text[:max_input_length]
            if len(text) > max_input_length:
                logger.info(f"[NOTEBOOKLM] Text truncated from {len(text)} to {max_input_length} chars")

            # Generate guideline synchronously using the OpenAI client directly
            from app.core.glm import get_glm_client

            glm_client = get_glm_client()

            # Use synchronous OpenAI client call
            response = glm_client.client.chat.completions.create(
                model=glm_client.model,
                messages=[
                    {"role": "system", "content": NOTEBOOKLM_SYSTEM_PROMPT},
                    {"role": "user", "content": f"请根据以下转录文本生成 NotebookLM 演示文稿大纲指南：\n\n{input_text}"}
                ],
                temperature=0.7,
                max_tokens=4000,
            )

            guideline = response.choices[0].message.content or ""
            logger.info(f"[NOTEBOOKLM] Generated guideline: {len(guideline)} chars")

            return guideline

        except Exception as e:
            logger.error(f"[NOTEBOOKLM] Failed to generate guideline: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ""


# Singleton instance
_formatting_service: Optional[TextFormattingService] = None


def get_formatting_service() -> TextFormattingService:
    """Get or create the singleton TextFormattingService instance."""
    global _formatting_service
    if _formatting_service is None:
        _formatting_service = TextFormattingService()
        logger.info("TextFormattingService initialized")
    return _formatting_service
