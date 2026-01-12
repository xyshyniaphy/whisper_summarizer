"""Runner configuration"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuration for runner service."""

    # Server connection
    server_url: str = "http://localhost:8000"
    runner_api_key: str = ""
    runner_id: str = "runner-01"

    # Polling config
    poll_interval_seconds: int = 10
    max_concurrent_jobs: int = 2
    job_timeout_seconds: int = 3600

    # Whisper config
    faster_whisper_device: str = "cuda"
    faster_whisper_compute_type: str = "int8_float16"
    faster_whisper_model_size: str = "large-v3-turbo"
    whisper_language: str = "zh"
    whisper_threads: int = 4

    # Audio chunking
    enable_chunking: bool = True
    chunk_size_minutes: int = 10
    chunk_overlap_seconds: int = 15
    max_concurrent_chunks: int = 4
    use_vad_split: bool = True
    vad_silence_threshold: int = -30
    vad_min_silence_duration: float = 0.5
    merge_strategy: str = "lcs"
    lcs_chunk_threshold: float = 0.7  # Threshold for LCS merge algorithm

    # Fixed-duration chunking (SRT segmentation)
    enable_fixed_chunks: bool = False
    fixed_chunk_threshold_minutes: int = 60  # Use fixed chunks for audio >= 60 minutes
    fixed_chunk_target_duration: int = 20  # Target chunk duration in seconds
    fixed_chunk_min_duration: int = 10  # Min chunk duration in seconds
    fixed_chunk_max_duration: int = 30  # Max chunk duration in seconds

    # GLM API
    glm_api_key: str = ""
    glm_model: str = "GLM-4.5-Air"
    glm_base_url: str = "https://api.z.ai/api/paas/v4/"
    review_language: str = "zh"

    # Storage
    audio_upload_dir: str = "/app/data/uploads"
    transcription_output_dir: str = "/app/data/transcribes"

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""  # No prefix, use exact env var names

    # Uppercase aliases for compatibility with existing code
    @property
    def WHISPER_LANGUAGE(self):
        return self.whisper_language

    @property
    def WHISPER_THREADS(self):
        return self.whisper_threads

    @property
    def CHUNK_SIZE_MINUTES(self):
        return self.chunk_size_minutes

    @property
    def ENABLE_CHUNKING(self):
        return self.enable_chunking

    @property
    def CHUNK_OVERLAP_SECONDS(self):
        return self.chunk_overlap_seconds

    @property
    def USE_VAD_SPLIT(self):
        return self.use_vad_split

    @property
    def VAD_SILENCE_THRESHOLD(self):
        return self.vad_silence_threshold

    @property
    def VAD_MIN_SILENCE_DURATION(self):
        return self.vad_min_silence_duration

    @property
    def MAX_CONCURRENT_CHUNKS(self):
        return self.max_concurrent_chunks

    @property
    def LCS_CHUNK_THRESHOLD(self):
        return self.lcs_chunk_threshold

    # Fixed-duration chunking aliases
    @property
    def ENABLE_FIXED_CHUNKS(self):
        return self.enable_fixed_chunks

    @property
    def FIXED_CHUNK_THRESHOLD_MINUTES(self):
        return self.fixed_chunk_threshold_minutes

    @property
    def FIXED_CHUNK_TARGET_DURATION(self):
        return self.fixed_chunk_target_duration

    @property
    def FIXED_CHUNK_MIN_DURATION(self):
        return self.fixed_chunk_min_duration

    @property
    def FIXED_CHUNK_MAX_DURATION(self):
        return self.fixed_chunk_max_duration


settings = Settings()
