"""
Text Formatting Service

Uses GLM-4.5-Air to format transcribed text by adding punctuation,
fixing capitalization, and improving readability without changing meaning.
"""

import logging
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


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


# Singleton instance
_formatting_service: Optional[TextFormattingService] = None


def get_formatting_service() -> TextFormattingService:
    """Get or create the singleton TextFormattingService instance."""
    global _formatting_service
    if _formatting_service is None:
        _formatting_service = TextFormattingService()
        logger.info("TextFormattingService initialized")
    return _formatting_service
