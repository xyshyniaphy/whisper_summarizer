"""
GLM4.7 API統合
"""

import httpx
from app.core.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GLMClient:
    """GLM4.7 APIクライアント"""
    
    def __init__(self):
        self.api_key = settings.GLM_API_KEY
        self.endpoint = settings.GLM_API_ENDPOINT
        self.model = settings.GLM_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
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
            system_prompt = """あなたは優秀な要約アシスタントです。
音声文字起こしテキストを読み、以下の形式で要約を生成してください:

# 概要
(全体の要約を2-3文で記述)

# 主要なポイント
- (重要なポイント1)
- (重要なポイント2)
- (重要なポイント3)

# 詳細
(詳細な説明や補足情報)

簡潔で分かりやすく、箇条書きを活用してください。"""
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.endpoint}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"以下の文字起こしテキストを要約してください:\n\n{transcription}"}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                summary = data["choices"][0]["message"]["content"]
                logger.info(f"要約を生成しました (長さ: {len(summary)} 文字)")
                
                return summary
        
        except httpx.HTTPStatusError as e:
            logger.error(f"GLM API HTTPエラー: {e.response.status_code} - {e.response.text}")
            raise Exception(f"要約生成エラー: {e.response.status_code}")
        
        except Exception as e:
            logger.error(f"GLM API エラー: {str(e)}")
            raise Exception(f"要約生成エラー: {str(e)}")


# シングルトンインスタンス
glm_client = GLMClient()
