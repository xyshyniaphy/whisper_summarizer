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

    # Gemini API
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    REVIEW_LANGUAGE: str = "zh"  # zh (中国語), ja (日本語), en (英語)
    GEMINI_API_ENDPOINT: Optional[str] = None  # カスタムエンドポイント（オプション）
    
    # Backend
    SECRET_KEY: str = "your-secret-key-change-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"
    LOG_LEVEL: str = "INFO"
    
    # Whisper.cpp
    WHISPER_SERVICE_URL: str = "http://whispercpp:8001"
    WHISPER_LANGUAGE: str = "ja"
    WHISPER_THREADS: int = 4

    # Audio Processing
    AUDIO_PARALLELISM: int = 1  # Max concurrent audio transcriptions (default: 1)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
