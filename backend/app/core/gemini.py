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
    system_prompt: Optional[str] = None
  ) -> str:
    """
    文字起こしテキストから要約を生成
    
    Args:
      transcription: 文字起こしテキスト
      system_prompt: システムプロンプト (オプション)
    
    Returns:
      summary: 生成された要約
    
    Raises:
      Exception: API呼び出しエラー
    """
    if not system_prompt:
      # 言語に応じたシステムプロンプトを生成
      system_prompt = self._get_system_prompt_by_language()
    
    # カスタムエンドポイントを使用する場合はhttpxで直接呼び出し
    if self.api_endpoint:
      return await self._generate_summary_with_custom_endpoint(transcription, system_prompt)
    else:
      return await self._generate_summary_with_sdk(transcription, system_prompt)
  
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
    system_prompt: str
  ) -> str:
    """
    Google Gemini SDKを使用して要約を生成
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
      logger.info(f"要約を生成しました (長さ: {len(summary)} 文字)")
      
      return summary
    
    except Exception as e:
      logger.error(f"Gemini API エラー: {str(e)}")
      raise Exception(f"要約生成エラー: {str(e)}")
  
  async def _generate_summary_with_custom_endpoint(
    self,
    transcription: str,
    system_prompt: str
  ) -> str:
    """
    カスタムエンドポイントを使用して要約を生成
    httpxで直接REST APIを呼び出す
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
              logger.info(f"要約を生成しました (カスタムエンドポイント, 長さ: {len(summary)} 文字)")
              return summary
        
        raise Exception(f"要約の抽出に失敗しました: {result}")
    
    except httpx.HTTPStatusError as e:
      logger.error(f"Custom Endpoint HTTPエラー: {e.response.status_code} - {e.response.text}")
      raise Exception(f"要約生成エラー: {e.response.status_code}")
    
    except Exception as e:
      logger.error(f"Custom Endpoint エラー: {str(e)}")
      raise Exception(f"要約生成エラー: {str(e)}")


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
