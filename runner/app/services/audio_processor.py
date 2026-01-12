"""Audio processing service for runner"""
import os
import logging
import time
from typing import Optional, Dict, Any
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

    def _get_audio_duration(self, audio_path: str) -> float:
        """
        Get audio file duration in seconds.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}")
            return 0.0

    def _should_use_fixed_chunks(self, audio_path: str) -> bool:
        """
        Determine if fixed-duration chunking should be used.

        Args:
            audio_path: Path to audio file

        Returns:
            True if fixed chunks should be used
        """
        if not getattr(settings, 'ENABLE_FIXED_CHUNKS', False):
            return False

        duration_seconds = self._get_audio_duration(audio_path)
        threshold_minutes = getattr(settings, 'FIXED_CHUNK_THRESHOLD_MINUTES', 60)
        threshold_seconds = threshold_minutes * 60

        return duration_seconds >= threshold_seconds

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
            # Check if we should use fixed chunks
            use_fixed_chunks = self._should_use_fixed_chunks(audio_path)

            if use_fixed_chunks:
                logger.info(f"Using fixed-chunk transcription for long audio")
                transcription_result: Dict[str, Any] = self.whisper_service.transcribe_fixed_chunks(
                    audio_path=audio_path,
                    target_duration_seconds=getattr(settings, 'FIXED_CHUNK_TARGET_DURATION', 20),
                    min_duration_seconds=getattr(settings, 'FIXED_CHUNK_MIN_DURATION', 10),
                    max_duration_seconds=getattr(settings, 'FIXED_CHUNK_MAX_DURATION', 30),
                    language=language,
                )
                # For fixed chunks, raw_text is the concatenation of segment text
                segments = transcription_result.get("segments", [])
                raw_text = "\n".join([seg.get("text", "") for seg in segments])
                logger.info(f"Fixed-chunk transcription complete: {len(segments)} chunks")
            else:
                logger.info("Using standard Whisper transcription")
                transcription_result = self.whisper_service.transcribe(
                    audio_file_path=audio_path
                )

                if not transcription_result or not transcription_result.get("text"):
                    raise ValueError("Transcription returned empty text")

                raw_text = transcription_result["text"]
                segments = transcription_result.get("segments", [])
                logger.info(f"Transcription complete: {len(raw_text)} characters, {len(segments)} segments")
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise

        # Step 2: Format with LLM (punctuation, paragraphs, summary, NotebookLM guideline)
        logger.info("Step 2: Formatting with LLM...")
        try:
            formatted_result = self.formatting_service.format_transcription(
                raw_text=raw_text,
                language=language
            )

            formatted_text = formatted_result.get("formatted_text", raw_text)
            summary = formatted_result.get("summary", "")
            notebooklm_guideline = formatted_result.get("notebooklm_guideline", "")

            logger.info(f"Formatting complete: summary={bool(summary)}, notebooklm_guideline={bool(notebooklm_guideline)}")
        except Exception as e:
            logger.warning(f"LLM formatting failed: {e}, using raw text")
            formatted_text = raw_text
            summary = ""
            notebooklm_guideline = ""

        # Calculate processing time
        processing_time = int(time.time() - start_time)
        logger.info(f"Processing complete in {processing_time}s")

        return JobResult(
            text=formatted_text,
            summary=summary,
            notebooklm_guideline=notebooklm_guideline,
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

        # Check if we should use fixed chunks
        use_fixed_chunks = self._should_use_fixed_chunks(audio_path)

        if use_fixed_chunks:
            logger.info(f"Using fixed-chunk transcription for long audio")
            transcription_result: Dict[str, Any] = self.whisper_service.transcribe_fixed_chunks(
                audio_path=audio_path,
                target_duration_seconds=getattr(settings, 'FIXED_CHUNK_TARGET_DURATION', 20),
                min_duration_seconds=getattr(settings, 'FIXED_CHUNK_MIN_DURATION', 10),
                max_duration_seconds=getattr(settings, 'FIXED_CHUNK_MAX_DURATION', 30),
                language=language or settings.whisper_language,
            )
            segments = transcription_result.get("segments", [])
            raw_text = "\n".join([seg.get("text", "") for seg in segments])
        else:
            logger.info("Using standard Whisper transcription")
            # Transcribe
            transcription_result = self.whisper_service.transcribe(
                audio_file_path=audio_path
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
