"""Audio processing service for runner"""
import os
import logging
import time
from typing import Optional
from pathlib import Path

from .whisper_service import TranscribeService
from .formatting_service import TextFormattingService
from ..config import settings
from ..models.job_schemas import JobResult

logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    Process audio files through transcription and summarization.

    This service orchestrates:
    1. Audio file validation
    2. Whisper transcription
    3. LLM formatting/summarization
    4. Timing tracking
    """

    def __init__(self):
        self.whisper_service = TranscribeService()
        self.formatting_service = TextFormattingService()
        logger.info("AudioProcessor initialized")

    def process(self, audio_path: str, language: Optional[str] = None) -> JobResult:
        """
        Process an audio file through transcription and summarization.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., "zh", "en", "ja")

        Returns:
            JobResult with text, summary, and timing

        Raises:
            Exception: If processing fails
        """
        start_time = time.time()
        logger.info(f"Processing audio: {audio_path}")

        # Validate audio file exists
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Detect language if not provided
        if not language:
            language = settings.whisper_language
            logger.info(f"Using default language: {language}")

        # Step 1: Transcribe with Whisper
        logger.info("Step 1: Transcribing with Whisper...")
        try:
            transcription_result = self.whisper_service.transcribe(
                audio_path=audio_path,
                language=language
            )

            if not transcription_result or not transcription_result.get("text"):
                raise ValueError("Transcription returned empty text")

            raw_text = transcription_result["text"]
            segments = transcription_result.get("segments", [])
            logger.info(f"Transcription complete: {len(raw_text)} characters, {len(segments)} segments")
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise

        # Step 2: Format with LLM (punctuation, paragraphs, summary)
        logger.info("Step 2: Formatting with LLM...")
        try:
            formatted_result = self.formatting_service.format_transcription(
                raw_text=raw_text,
                language=language
            )

            formatted_text = formatted_result.get("formatted_text", raw_text)
            summary = formatted_result.get("summary", "")

            logger.info(f"Formatting complete: summary={bool(summary)}")
        except Exception as e:
            logger.warning(f"LLM formatting failed: {e}, using raw text")
            formatted_text = raw_text
            summary = ""

        # Calculate processing time
        processing_time = int(time.time() - start_time)
        logger.info(f"Processing complete in {processing_time}s")

        return JobResult(
            text=formatted_text,
            summary=summary,
            processing_time_seconds=processing_time
        )

    def process_with_timestamps(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> dict:
        """
        Process audio and return detailed results with timestamps.

        Args:
            audio_path: Path to audio file
            language: Language code

        Returns:
            Dict with text, summary, segments, and timing
        """
        start_time = time.time()
        logger.info(f"Processing audio with timestamps: {audio_path}")

        # Transcribe
        transcription_result = self.whisper_service.transcribe(
            audio_path=audio_path,
            language=language or settings.whisper_language
        )

        raw_text = transcription_result["text"]
        segments = transcription_result.get("segments", [])

        # Format with LLM
        try:
            formatted_result = self.formatting_service.format_transcription(
                raw_text=raw_text,
                language=language or settings.whisper_language
            )
            formatted_text = formatted_result.get("formatted_text", raw_text)
            summary = formatted_result.get("summary", "")
        except Exception as e:
            logger.warning(f"LLM formatting failed: {e}")
            formatted_text = raw_text
            summary = ""

        processing_time = int(time.time() - start_time)

        return {
            "text": formatted_text,
            "summary": summary,
            "segments": segments,
            "processing_time_seconds": processing_time
        }
