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
    CORS_ORIGINS: str = "http://localhost:3000"
    LOG_LEVEL: str = "INFO"
    DISABLE_AUTH: bool = False  # Disable authentication for testing
    
    # Whisper.cpp
    WHISPER_SERVICE_URL: str = "http://whispercpp:8001"
    WHISPER_LANGUAGE: str = "ja"
    WHISPER_THREADS: int = 4

    # Audio Processing
    AUDIO_PARALLELISM: int = 1  # Max concurrent audio transcriptions (default: 1)


    # Audio Chunking (for faster transcription of long audio)
    ENABLE_CHUNKING: bool = True  # Master toggle for chunking feature
    CHUNK_SIZE_MINUTES: int = 10  # Target chunk length in minutes
    CHUNK_OVERLAP_SECONDS: int = 15  # Overlap duration in seconds
    MAX_CONCURRENT_CHUNKS: int = 2  # Max chunks to process in parallel (CPU-based)
    USE_VAD_SPLIT: bool = True  # Use Voice Activity Detection for smart splitting
    VAD_SILENCE_THRESHOLD: int = -30  # dB threshold for silence detection
    VAD_MIN_SILENCE_DURATION: float = 0.5  # Minimum silence duration in seconds
    MERGE_STRATEGY: str = "lcs"  # Merge strategy: "lcs" (text-based) or "timestamp" (simple)
    LCS_CHUNK_THRESHOLD: int = 10  # Use timestamp merge for >= N chunks (optimization for large files)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
