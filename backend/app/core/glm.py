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
        self.base_url = base_url or os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

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
            context_message = f"""以下の文字起こしテキストを参照して、質問に答えてください:

---
文字起こし:
{transcription_context}
---

質問: {question}"""

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
            return """你是一个专业的问答助手。
你的任务是基于提供的文字起こしテキスト（转录文本）来回答用户的问题。

请注意：
1. 仅根据提供的转录文本回答问题，不要添加外部信息
2. 如果转录文本中没有相关信息，请明确告知
3. 使用简洁明了的语言
4. 如果是中文问题，用中文回答；如果是日文问题，用日文回答；如果是英文问题，用英文回答
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
        base_url = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
        model = os.getenv("GLM_MODEL", "GLM-4.5-Air")
        review_language = os.getenv("REVIEW_LANGUAGE", "zh")
        glm_client = GLMClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            review_language=review_language
        )
    return glm_client
