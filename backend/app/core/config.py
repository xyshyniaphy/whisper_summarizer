"""
アプリケーション設定
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """環境変数から設定を読み込み"""
    
    # Database
    DATABASE_URL: str
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # GLM4.7
    GLM_API_KEY: str
    GLM_API_ENDPOINT: str = "https://api.glm.ai/v1"
    GLM_MODEL: str = "glm-4.0-turbo"
    
    # Gemini
    GEMINI_API_KEY: str
    GEMINI_API_ENDPOINT: Optional[str] = None  # カスタムエンドポイント（オプション）
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    REVIEW_LANGUAGE: str = "zh"  # zh (中国語), ja (日本語), en (英語)
    
    # Backend
    SECRET_KEY: str = "your-secret-key-change-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"
    LOG_LEVEL: str = "INFO"
    
    # Whisper.cpp
    WHISPER_SERVICE_URL: str = "http://whispercpp:8001"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
