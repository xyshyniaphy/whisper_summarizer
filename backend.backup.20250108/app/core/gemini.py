"""
Gemini API クライアント

Google Gemini APIを使用して文字起こしテキストの要約を生成する
"""

import os
import json
import logging
from typing import Optional
import httpx
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiClient:
  """Google Gemini APIクライアント"""
  
  def __init__(
    self,
    api_key: Optional[str] = None,
    api_endpoint: Optional[str] = None,
    model: str = "gemini-2.0-flash-exp",
    review_language: str = "zh"
  ):
    """
    GeminiClientを初期化
    
    Args:
      api_key: Gemini API Key (省略時は環境変数GEMINI_API_KEYから取得)
      api_endpoint: カスタムAPIエンドポイント (オプション)
      model: 使用するモデル名
      review_language: 要約言語 (zh, ja, en)
    """
    self.api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not self.api_key:
      raise ValueError("GEMINI_API_KEY が設定されていません")
    
    self.model = model
    self.api_endpoint = api_endpoint
    self.review_language = review_language
    
    # カスタムエンドポイントを使用しない場合のみSDKクライアントを初期化
    if not self.api_endpoint:
      self.client = genai.Client(api_key=self.api_key)
      logger.info(f"GeminiClient initialized with model: {self.model}, language: {self.review_language}")
    else:
      self.client = None
      logger.info(f"GeminiClient initialized with custom endpoint: {self.api_endpoint}, model: {self.model}, language: {self.review_language}")
  
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
      # カスタムエンドポイントを使用する場合はhttpxで直接呼び出し
      if self.api_endpoint:
        response_data = await self._generate_summary_with_custom_endpoint(transcription, system_prompt, file_name)
      else:
        response_data = await self._generate_summary_with_sdk(transcription, system_prompt, file_name)

      response_time_ms = (time.time() - start_time) * 1000

      # GeminiResponseを構築
      return GeminiResponse(
        summary=response_data.get("summary", ""),
        model_name=self.model,
        prompt=system_prompt,
        input_text_length=len(transcription),
        output_text_length=len(response_data.get("summary", "")),
        input_tokens=response_data.get("input_tokens"),
        output_tokens=response_data.get("output_tokens"),
        total_tokens=response_data.get("total_tokens"),
        response_time_ms=response_time_ms,
        temperature=0.7,
        status="success",
        raw_response=response_data.get("raw_response")
      )

    except Exception as e:
      response_time_ms = (time.time() - start_time) * 1000
      logger.error(f"Gemini API エラー: {str(e)}")

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
  
  async def _generate_summary_with_sdk(
    self,
    transcription: str,
    system_prompt: str,
    file_name: str = None
  ) -> dict:
    """
    Google Gemini SDKを使用して要約を生成

    Returns:
      dict: summary, input_tokens, output_tokens, total_tokens, raw_response
    """
    try:
      # コンテンツの構築
      contents = [
        types.Content(
          role="user",
          parts=[
            types.Part.from_text(
              text=f"以下の文字起こしテキストを要約してください:\n\n{transcription}"
            ),
          ],
        ),
      ]

      # 設定の構築
      generate_content_config = types.GenerateContentConfig(
        system_instruction=[
          types.Part.from_text(text=system_prompt),
        ],
        temperature=0.7,
        max_output_tokens=2000,
      )

      # 非ストリーミング生成を使用
      response = self.client.models.generate_content(
        model=self.model,
        contents=contents,
        config=generate_content_config,
      )

      summary = response.text

      # トークン使用量を取得（SDKから取得できる場合）
      input_tokens = None
      output_tokens = None
      total_tokens = None

      # 使用トークン情報の抽出を試みる
      if hasattr(response, 'usage_metadata') and response.usage_metadata:
        input_tokens = response.usage_metadata.prompt_token_count or getattr(response.usage_metadata, 'input_token_count', None)
        output_tokens = response.usage_metadata.candidates_token_count or getattr(response.usage_metadata, 'output_token_count', None)
        total_tokens = response.usage_metadata.total_token_count

      logger.info(f"要約を生成しました (ファイル: {file_name}, 長さ: {len(summary)} 文字)")

      return {
        "summary": summary,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "raw_response": {
          "model": self.model,
          "finish_reason": getattr(response, 'finish_reason', None),
        }
      }

    except Exception as e:
      logger.error(f"Gemini SDK API エラー: {str(e)}")
      raise Exception(f"要約生成エラー: {str(e)}")
  
  async def _generate_summary_with_custom_endpoint(
    self,
    transcription: str,
    system_prompt: str,
    file_name: str = None
  ) -> dict:
    """
    カスタムエンドポイントを使用して要約を生成
    httpxで直接REST APIを呼び出す

    Returns:
      dict: summary, input_tokens, output_tokens, total_tokens, raw_response
    """
    try:
      # エンドポイントURLを構築
      url = f"{self.api_endpoint}/models/{self.model}:generateContent"

      # リクエストボディを構築（Gemini API形式）
      payload = {
        "contents": [
          {
            "role": "user",
            "parts": [
              {
                "text": f"以下の文字起こしテキストを要約してください:\n\n{transcription}"
              }
            ]
          }
        ],
        "systemInstruction": {
          "parts": [
            {
              "text": system_prompt
            }
          ]
        },
        "generationConfig": {
          "temperature": 0.7,
          "maxOutputTokens": 2000
        }
      }

      headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": self.api_key
      }

      async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()

        # レスポンスからテキストを抽出
        if "candidates" in result and len(result["candidates"]) > 0:
          candidate = result["candidates"][0]
          if "content" in candidate and "parts" in candidate["content"]:
            parts = candidate["content"]["parts"]
            if len(parts) > 0 and "text" in parts[0]:
              summary = parts[0]["text"]

              # トークン使用量を取得（APIレスポンスから）
              input_tokens = None
              output_tokens = None
              total_tokens = None

              if "usageMetadata" in result:
                metadata = result["usageMetadata"]
                input_tokens = metadata.get("promptTokenCount")
                output_tokens = metadata.get("candidatesTokenCount")
                total_tokens = metadata.get("totalTokenCount")

              logger.info(f"要約を生成しました (カスタムエンドポイント, ファイル: {file_name}, 長さ: {len(summary)} 文字)")

              return {
                "summary": summary,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "raw_response": result
              }

        raise Exception(f"要約の抽出に失敗しました: {result}")

    except httpx.HTTPStatusError as e:
      logger.error(f"Custom Endpoint HTTPエラー: {e.response.status_code} - {e.response.text}")
      raise Exception(f"要約生成エラー: {e.response.status_code}")

    except Exception as e:
      logger.error(f"Custom Endpoint エラー: {str(e)}")
      raise Exception(f"要約生成エラー: {str(e)}")

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

    print(f"[Gemini.chat] Starting chat with question: {question[:50]}...")
    # Build system prompt for chat
    system_prompt = self._get_chat_system_prompt()
    print(f"[Gemini.chat] System prompt length: {len(system_prompt)}")

    start_time = time.time()

    try:
      # Use custom endpoint if configured, otherwise use SDK
      if self.api_endpoint:
        print(f"[Gemini.chat] Using custom endpoint")
        return await self._chat_with_custom_endpoint(question, transcription_context, chat_history, system_prompt, start_time)
      else:
        print(f"[Gemini.chat] Using SDK")
        return await self._chat_with_sdk(question, transcription_context, chat_history, system_prompt, start_time)

    except Exception as e:
      import traceback
      logger.error(f"[Chat] API error: {str(e)}\n{traceback.format_exc()}")
      raise Exception(f"Chat error: {str(e)}")

  async def _chat_with_custom_endpoint(
    self,
    question: str,
    transcription_context: str,
    chat_history: list[dict],
    system_prompt: str,
    start_time: float
  ) -> dict:
    """Use custom endpoint via httpx for chat."""
    # Build contents for API
    contents = []

    # Add chat history if available
    if chat_history:
      for msg in chat_history[-10:]:  # Last 10 messages for context
        if msg["role"] in ["user", "assistant"]:
          contents.append({
            "role": msg["role"],
            "parts": [{"text": msg["content"]}]
          })

    # Add current question with context
    context_message = f"""以下の文字起こしテキストを参照して、質問に答えてください:

---
文字起こし:
{transcription_context}
---

質問: {question}"""

    contents.append({
      "role": "user",
      "parts": [{"text": context_message}]
    })

    # Build payload
    payload = {
      "contents": contents,
      "systemInstruction": {
        "parts": [{"text": system_prompt}]
      },
      "generationConfig": {
        "temperature": 0.7,
        "maxOutputTokens": 2000
      }
    }

    url = f"{self.api_endpoint}/models/{self.model}:generateContent"
    headers = {
      "Content-Type": "application/json",
      "x-goog-api-key": self.api_key
    }

    print(f"[Chat] Calling custom endpoint: {url}")
    async with httpx.AsyncClient(timeout=120.0) as client:
      print(f"[Chat] About to POST to endpoint...")
      response = await client.post(url, json=payload, headers=headers)
      print(f"[Chat] Got response, status: {response.status_code}")
      response.raise_for_status()
      print(f"[Chat] Parsing JSON response...")
      result = response.json()
      print(f"[Chat] Response parsed, keys: {result.keys()}")

    # Extract response text
    answer = ""
    if "candidates" in result and len(result["candidates"]) > 0:
      candidate = result["candidates"][0]
      if "content" in candidate and "parts" in candidate["content"]:
        parts = candidate["content"]["parts"]
        if len(parts) > 0 and "text" in parts[0]:
          answer = parts[0]["text"]

    response_time_ms = (time.time() - start_time) * 1000
    print(f"[Chat] Custom endpoint response length: {len(answer)} chars")

    return {
      "response": answer,
      "input_tokens": None,
      "output_tokens": None,
      "total_tokens": None,
      "response_time_ms": response_time_ms,
    }

  async def _chat_with_sdk(
    self,
    question: str,
    transcription_context: str,
    chat_history: list[dict],
    system_prompt: str,
    start_time: float
  ) -> dict:
    """Use Google GenAI SDK for chat."""
    # Build chat contents with history
    contents = []

    # Add chat history if available
    if chat_history:
      for msg in chat_history[-10:]:  # Last 10 messages for context
        if msg["role"] in ["user", "assistant"]:
          contents.append(types.Content(
            role=msg["role"],
            parts=[types.Part.from_text(text=msg["content"])]
          ))

    # Add current question with context
    context_message = f"""以下の文字起こしテキストを参照して、質問に答えてください:

---
文字起こし:
{transcription_context}
---

質問: {question}"""

    contents.append(types.Content(
      role="user",
      parts=[types.Part.from_text(text=context_message)]
    ))

    # Use SDK for chat
    generate_content_config = types.GenerateContentConfig(
      system_instruction=system_prompt,
      temperature=0.7,
      max_output_tokens=2000,
    )

    logger.info(f"[Chat] Calling Gemini API with model: {self.model}, contents count: {len(contents)}")
    print(f"[Chat] Calling Gemini API with model: {self.model}, contents count: {len(contents)}")
    response = self.client.models.generate_content(
      model=self.model,
      contents=contents,
      config=generate_content_config,
    )
    print(f"[Chat] After generate_content, response type: {type(response)}")

    logger.info(f"[Chat] Response received, type: {type(response)}, has text: {hasattr(response, 'text')}")
    print(f"[Chat] Response received, has text: {hasattr(response, 'text')}")
    answer = response.text if hasattr(response, 'text') and response.text else ""
    print(f"[Chat] Answer length: {len(answer)}")
    if not answer:
      logger.error(f"[Chat] Empty response! Response: {response}")
    response_time_ms = (time.time() - start_time) * 1000

    # Extract token usage
    input_tokens = None
    output_tokens = None
    total_tokens = None

    if hasattr(response, 'usage_metadata') and response.usage_metadata:
      input_tokens = response.usage_metadata.prompt_token_count
      output_tokens = response.usage_metadata.candidates_token_count
      total_tokens = response.usage_metadata.total_token_count

    logger.info(f"Chat response generated (length: {len(answer)} chars, time: {response_time_ms:.0f}ms)")

    return {
      "response": answer,
      "input_tokens": input_tokens,
      "output_tokens": output_tokens,
      "total_tokens": total_tokens,
      "response_time_ms": response_time_ms,
    }

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
gemini_client = None

def get_gemini_client() -> GeminiClient:
  """
  GeminiClientのシングルトンインスタンスを取得
  
  Returns:
    gemini_client: GeminiClientインスタンス
  """
  global gemini_client
  if gemini_client is None:
    api_key = os.getenv("GEMINI_API_KEY")
    api_endpoint = os.getenv("GEMINI_API_ENDPOINT")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    review_language = os.getenv("REVIEW_LANGUAGE", "zh")
    gemini_client = GeminiClient(
      api_key=api_key,
      api_endpoint=api_endpoint,
      model=model,
      review_language=review_language
    )
  return gemini_client
