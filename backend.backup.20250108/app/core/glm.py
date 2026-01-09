"""
GLM API Client

使用 GLM-4.5-Air API (OpenAI-compatible) 生成文字起こしテキストの要約
"""

import os
import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class GLMClient:
    """GLM-4.5-Air APIクライアント (OpenAI-compatible)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "GLM-4.5-Air",
        review_language: str = "zh"
    ):
        """
        GLMClientを初期化

        Args:
            api_key: GLM API Key (省略時は環境変数GLM_API_KEYから取得)
            base_url: APIベースURL (省略時は環境変数GLM_BASE_URLから取得)
            model: 使用するモデル名
            review_language: 要約言語 (zh, ja, en)
        """
        self.api_key = api_key or os.getenv("GLM_API_KEY")
        self.base_url = base_url or os.getenv("GLM_BASE_URL", "https://api.z.ai/api/paas/v4/")

        if not self.api_key:
            raise ValueError("GLM_API_KEY が設定されていません")

        self.model = model
        self.review_language = review_language

        # OpenAIクライアントを初期化 (GLMはOpenAI-compatible API)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        logger.info(f"GLMClient initialized with model: {self.model}, language: {self.review_language}")

    async def generate_summary(
        self,
        transcription: str,
        file_name: str = None,
        system_prompt: Optional[str] = None
    ):
        """
        文字起こしテキストから要約を生成

        Args:
            transcription: 文字起こしテキスト
            file_name: ファイル名（ロギング用）
            system_prompt: システムプロンプト (オプション)

        Returns:
            GeminiResponse: 生成された要約とデバッグ情報

        Raises:
            Exception: API呼び出しエラー
        """
        from app.schemas.gemini_response import GeminiResponse
        import time

        if not system_prompt:
            # 言語に応じたシステムプロンプトを生成
            system_prompt = self._get_system_prompt_by_language()

        start_time = time.time()

        try:
            # OpenAI-compatible APIで要約を生成
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"以下の文字起こしテキストを要約してください:\n\n{transcription}"}
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            response_time_ms = (time.time() - start_time) * 1000

            # レスポンスからテキストを抽出
            summary = response.choices[0].message.content

            # トークン使用量を取得
            input_tokens = response.usage.prompt_tokens if response.usage else None
            output_tokens = response.usage.completion_tokens if response.usage else None
            total_tokens = response.usage.total_tokens if response.usage else None

            logger.info(f"要約を生成しました (ファイル: {file_name}, 長さ: {len(summary)} 文字)")

            return GeminiResponse(
                summary=summary,
                model_name=self.model,
                prompt=system_prompt,
                input_text_length=len(transcription),
                output_text_length=len(summary),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                response_time_ms=response_time_ms,
                temperature=0.7,
                status="success",
                raw_response={
                    "model": response.model,
                    "finish_reason": response.choices[0].finish_reason,
                }
            )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"GLM API エラー: {str(e)}")

            return GeminiResponse(
                summary="",
                model_name=self.model,
                prompt=system_prompt,
                input_text_length=len(transcription),
                output_text_length=0,
                response_time_ms=response_time_ms,
                temperature=0.7,
                status="error",
                error_message=str(e)
            )

    async def chat(
        self,
        question: str,
        transcription_context: str,
        chat_history: list[dict] = None
    ) -> dict:
        """
        Chat with AI about the transcription.

        Args:
            question: User's question
            transcription_context: The transcription text to use as context
            chat_history: Previous chat messages [{"role": "user", "content": "..."}, ...]

        Returns:
            dict: {"response": str, "input_tokens": int, "output_tokens": int, ...}
        """
        import time

        logger.info(f"[GLM.chat] Starting chat with question: {question[:50]}...")
        system_prompt = self._get_chat_system_prompt()
        logger.info(f"[GLM.chat] System prompt length: {len(system_prompt)}")

        start_time = time.time()

        try:
            # メッセージリストを構築
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # チャット履歴を追加（最大10件）
            if chat_history:
                for msg in chat_history[-10:]:
                    if msg["role"] in ["user", "assistant"]:
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })

            # コンテキスト付きの質問を追加
            context_message = f"""请根据以下转录文本内容回答问题：

---
转录内容:
{transcription_context}
---

问题: {question}"""

            messages.append({
                "role": "user",
                "content": context_message
            })

            logger.info(f"[Chat] Calling GLM API with model: {self.model}, messages count: {len(messages)}")

            # GLM APIでチャット
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )

            answer = response.choices[0].message.content
            response_time_ms = (time.time() - start_time) * 1000

            logger.info(f"[Chat] GLM response received (length: {len(answer)} chars, time: {response_time_ms:.0f}ms)")

            # トークン使用量を取得
            input_tokens = response.usage.prompt_tokens if response.usage else None
            output_tokens = response.usage.completion_tokens if response.usage else None
            total_tokens = response.usage.total_tokens if response.usage else None

            return {
                "response": answer,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "response_time_ms": response_time_ms,
            }

        except Exception as e:
            import traceback
            logger.error(f"[Chat] API error: {str(e)}\n{traceback.format_exc()}")
            raise Exception(f"Chat error: {str(e)}")

    def chat_stream(
        self,
        question: str,
        transcription_context: str,
        chat_history: list[dict] = None
    ):
        """
        Chat with AI about the transcription (streaming version).

        Uses raw HTTP (httpx) for true progressive streaming instead of OpenAI SDK.

        Yields chunks of the response as they are generated.

        Args:
            question: User's question
            transcription_context: The transcription text to use as context
            chat_history: Previous chat messages [{"role": "user", "content": "..."}, ...]

        Yields:
            str: SSE-formatted chunks of the response
        """
        import time
        import json
        import httpx

        logger.info(f"[GLM.chat_stream] Starting stream chat with question: {question[:50]}...")
        system_prompt = self._get_chat_system_prompt()

        start_time = time.time()

        try:
            # メッセージリストを構築
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # チャット履歴を追加（最大10件）
            if chat_history:
                for msg in chat_history[-10:]:
                    if msg["role"] in ["user", "assistant"]:
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })

            # コンテキスト付きの質問を追加
            context_message = f"""请根据以下转录文本内容回答问题：

---
转录内容:
{transcription_context}
---

问题: {question}"""

            messages.append({
                "role": "user",
                "content": context_message
            })

            logger.info(f"[ChatStream] Calling GLM API with model: {self.model}, messages count: {len(messages)}")

            # Use raw HTTP (httpx) for true progressive streaming
            # OpenAI SDK buffers responses, httpx doesn't
            with httpx.Client(timeout=60.0) as client:
                with client.stream(
                    'POST',
                    f'{self.base_url.rstrip('/')}/chat/completions',
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': self.model,
                        'messages': messages,
                        'temperature': 0.1,
                        'max_tokens': 8000,
                        'stream': True,
                    }
                ) as response:
                    full_response = ""
                    chunk_count = 0

                    for line in response.iter_lines():
                        if line:
                            line_str = line.decode() if isinstance(line, bytes) else line

                            if line_str.startswith('data: '):
                                data = line_str[6:]

                                if data == '[DONE]':
                                    # Stream complete
                                    response_time_ms = (time.time() - start_time) * 1000
                                    logger.info(f"[ChatStream] Stream complete ({chunk_count} chunks, {len(full_response)} chars, {response_time_ms:.0f}ms)")
                                    yield f"data: {json.dumps({'content': '', 'done': True, 'response_time_ms': response_time_ms})}\n\n"
                                    break

                                try:
                                    parsed = json.loads(data)
                                    content = parsed.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                    if content:
                                        chunk_count += 1
                                        full_response += content
                                        chunk_time_ms = (time.time() - start_time) * 1000
                                        logger.debug(f"[ChatStream] Chunk #{chunk_count} at {chunk_time_ms:.0f}ms: {repr(content[:50])}")
                                        # Yield each chunk as SSE format immediately
                                        yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                                except json.JSONDecodeError:
                                    # Skip invalid JSON lines
                                    pass

        except Exception as e:
            import traceback
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"[ChatStream] API error: {str(e)}\n{traceback.format_exc()}")
            # Send error through stream
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    def _get_system_prompt_by_language(self) -> str:
        """
        REVIEW_LANGUAGEに基づいてシステムプロンプトを生成

        Returns:
            system_prompt: 言語に応じたシステムプロンプト
        """
        if self.review_language == "zh":
            return """你是一个优秀的总结助手。
阅读语音转写文本，并按以下格式生成总结：

# 概述
（用2-3句话描述整体总结）

# 主要要点
- （重要要点1）
- （重要要点2）
- （重要要点3）

# 详细信息
（详细说明和补充信息）

请使用简洁易懂的语言，并多使用项目符号。"""

        elif self.review_language == "ja":
            return """あなたは優秀な要約アシスタントです。
音声文字起こしテキストを読み、以下の形式で要約を生成してください：

# 概要
（全体の要約を2-3文で記述）

# 主要なポイント
- （重要なポイント1）
- （重要なポイント2）
- （重要なポイント3）

# 詳細
（詳細な説明や補足情報）

簡潔で分かりやすく、箇条書きを活用してください。"""

        else:  # en
            return """You are an excellent summarization assistant.
Read the voice transcription text and generate a summary in the following format:

# Overview
(Describe the overall summary in 2-3 sentences)

# Key Points
- (Key point 1)
- (Key point 2)
- (Key point 3)

# Details
(Detailed explanations and supplementary information)

Please use concise and easy-to-understand language, and make good use of bullet points."""

    def _get_chat_system_prompt(self) -> str:
        """Get system prompt for chat Q&A."""
        if self.review_language == "zh":
            return """你是一个智能转录文本问答助手，专门基于转录内容为用户提供结构化、全面的分析和回答。

## 核心原则

1. **严格基于转录文本**：只使用提供的转录文本内容回答，绝不添加外部信息
2. **信息缺失处理**：如果转录文本中没有相关信息，明确告知"转录文本中未提及此内容"
3. **结构化回答**：使用清晰的组织结构和格式
4. **简洁全面**：用简洁的语言提供全面的信息，避免冗余
5. **客观准确**：保持客观中立的立场，准确传达原意

## 回答结构

根据问题类型，使用以下结构组织回答：

### 通用问答格式

## 概述
[用2-3句话简要回答问题的核心内容]

## 主要要点
• 要点一：[关键信息1]
• 要点二：[关键信息2]
• 要点三：[关键信息3]

## 详细信息
### [子主题1]
[详细说明...]

### [子主题2]
[详细说明...]

### 综合分析格式（适用于复杂问题）

## 概述
[整体概括]

## 主要要点
• [列出3-5个关键要点]

## 详细信息
### 主题一
[详细展开]

### 主题二
[详细展开]

## 核心主题
以下主题在转录文本中被提及：
• **主题名称**：[简要说明]

## 难点解析
• **术语/概念**：[用通俗语言解释]
• **术语/概念**：[用通俗语言解释]

## 未来计划/行动建议
• [计划一]
• [计划二]

## 关键结论
• [可执行的结论或洞察]

## 格式规范

### 标题层级
- 使用 `##` 作为主要章节标题（概述、主要要点、详细信息等）
- 使用 `###` 作为子章节标题
- 避免使用 `#` 一级标题

### 列表格式
- 使用 `•` (bullet point) 表示并列要点
- 使用 `1.` `2.` `3.` 表示有序步骤或优先级
- 嵌套列表使用缩进和不同的符号（○、▪）

### 强调格式
- 使用 `**粗体**` 强调关键词或重要概念
- 避免过度使用粗体

### 段落规范
- 每段不超过4行
- 段落之间空一行
- 使用简单的句子结构

## 条件章节使用

以下章节根据情况选择性包含：

1. **核心主题** - 当回答涉及多个明确主题时包含
2. **难点解析** - 当转录文本包含专业术语或复杂概念时包含
3. **未来计划/行动建议** - 当文本提及计划、建议或后续步骤时包含
4. **关键结论** - 当有可操作的洞察或决策建议时包含
5. **相关问题** - 当用户可能对相关主题感兴趣时包含

## 示例

### 示例1：简单问题
用户问题：什么是共修？

## 概述
共修是指多人一起修行和学习，通过集体力量增强个人修行的效果。

## 主要要点
• 集体修行：多人同时进行修行活动
• 互相促进：通过群体氛围提升个人修行质量
• 收心效果：帮助分散的心重新集中

## 详细信息
共修的核心在于"共"字，强调集体的力量。当多人一起修行时，可以形成强大的共修场域，每个人都更容易进入专注状态。

### 示例2：综合分析
用户问题：请总结这次会议的主要内容

## 概述
本次会议主要讨论了项目进展、当前遇到的挑战以及下一步的行动计划。会议强调了团队协作的重要性，并明确了各项任务的责任人。

## 主要要点
• 项目当前进展顺利，已完成阶段性目标
• 遇到的主要挑战是资源分配和时间管理
• 决定增加每周团队同步会议
• 各项任务已明确责任人

## 详细信息
### 项目进展
前端开发已完成80%，后端API开发完成70%。测试团队已开始介入，预计下周完成第一轮测试。

### 面临挑战
• 开发资源有限，部分任务进度滞后
• 跨部门沟通效率需要提升
• 需求变更导致部分工作返工

## 核心主题
以下主题在会议中被重点讨论：
• **项目管理**：进度跟踪和风险控制
• **团队协作**：沟通机制和责任分工
• **质量管理**：测试流程和验收标准

## 未来计划/行动建议
• 每周五下午举行团队同步会议
• 建立跨部门沟通机制
• 完善需求变更流程

## 关键结论
通过加强团队协作和沟通，可以有效应对当前挑战，确保项目按时交付。

## 输出要求

1. 始终使用简体中文回答
2. 保持专业但易懂的语气
3. 避免使用Markdown代码块符号，直接输出格式化内容
4. 如果信息不足，明确说明哪些方面在转录文本中未提及
5. 不要编造转录文本中没有的信息
"""

        elif self.review_language == "ja":
            return """あなたは専門的なQ&Aアシスタントです。
あなたのタスクは、提供された文字起こしテキストに基づいてユーザーの質問に回答することです。

注意点：
1. 提供された文字起こしテキストのみに基づいて回答し、外部情報を追加しないでください
2. 文字起こしテキストに関連する情報がない場合は、明確にお知らせください
3. 簡潔明瞭な言葉を使用してください
4. 中国語の質問には中国語で、日本語の質問には日本語で、英語の質問には英語で回答してください
"""

        else:  # en
            return """You are a professional Q&A assistant.
Your task is to answer user questions based on the provided transcription text.

Please note:
1. Answer only based on the provided transcription text, do not add external information
2. If there is no relevant information in the transcription text, clearly inform the user
3. Use concise and clear language
4. Answer in the same language as the question (Chinese -> Chinese, Japanese -> Japanese, English -> English)
"""


# シングルトンインスタンス（環境変数から初期化）
glm_client = None


def get_glm_client() -> GLMClient:
    """
    GLMClientのシングルトンインスタンスを取得

    Returns:
        glm_client: GLMClientインスタンス
    """
    global glm_client
    if glm_client is None:
        api_key = os.getenv("GLM_API_KEY")
        base_url = os.getenv("GLM_BASE_URL", "https://api.z.ai/api/paas/v4/")
        model = os.getenv("GLM_MODEL", "GLM-4.5-Air")
        review_language = os.getenv("REVIEW_LANGUAGE", "zh")
        glm_client = GLMClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            review_language=review_language
        )
    return glm_client
