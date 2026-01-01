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

    # GLM API (OpenAI-compatible)
    GLM_API_KEY: str
    GLM_MODEL: str = "GLM-4.5-Air"
    GLM_BASE_URL: Optional[str] = "https://open.bigmodel.cn/api/paas/v4"  # GLM API endpoint
    REVIEW_LANGUAGE: str = "zh"  # zh (中国語), ja (日本語), en (英語)
    
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

    # Data Retention
    MAX_KEEP_DAYS: int = 30  # Maximum days to keep transcriptions before auto-delete
    CLEANUP_HOUR: int = 9  # Hour to run daily cleanup (24-hour format, default: 9 AM)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
