"""
Server Application Configuration
Lightweight server - no GPU, no whisper, no GLM
All processing is handled by separate runners
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Server configuration - lightweight API and job queue management"""

    # Database
    DATABASE_URL: str

    # Supabase (Auth only)
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Runner Authentication
    RUNNER_API_KEY: str  # API key for runner authentication

    # Server Configuration
    CORS_ORIGINS: str = "http://localhost:3000"
    LOG_LEVEL: str = "INFO"
    DISABLE_AUTH: bool = False  # Disable authentication for testing

    # Data Retention
    MAX_KEEP_DAYS: int = 30  # Maximum days to keep transcriptions before auto-delete
    CLEANUP_HOUR: int = 9  # Hour to run daily cleanup (24-hour format, default: 9 AM)

    # Pagination
    DEFAULT_PAGE_SIZE: int = 10  # Default number of items per page
    MAX_PAGE_SIZE: int = 100  # Maximum allowed page size

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
