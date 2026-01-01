"""
Transcription Processor Service
Handles complete workflow: upload -> transcribe -> summarize with retry logic
"""

import os
import time
import asyncio
import gzip
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Set
from threading import BoundedSemaphore, Lock, Event
from sqlalchemy.orm import Session

from app.models.transcription import Transcription
from app.models.summary import Summary
from app.models.gemini_request_log import GeminiRequestLog
from app.services.whisper_service import whisper_service
from app.core.gemini import get_gemini_client
from app.core.config import settings

# Class-level semaphore for limiting concurrent transcriptions
_transcription_semaphore: BoundedSemaphore | None = None


def get_transcription_semaphore() -> BoundedSemaphore:
    """Get or create the semaphore for limiting concurrent transcriptions."""
    global _transcription_semaphore
    if _transcription_semaphore is None:
        _transcription_semaphore = BoundedSemaphore(settings.AUDIO_PARALLELISM)
        logger.info(f"Initialized transcription semaphore with parallelism={settings.AUDIO_PARALLELISM}")
    return _transcription_semaphore


# ============================================
# Task Registry for Cancellation Support
# ============================================
# Tracks active transcription tasks with their cancel events and process info
_task_registry: Dict[str, Dict] = {}  # {transcription_id: {"cancel_event": Event, "pids": Set[int], "stage": str}}
_task_registry_lock = Lock()


def register_transcription_task(transcription_id: str, cancel_event: Event) -> None:
    """
    Register a new transcription task for cancellation support.

    Args:
        transcription_id: Transcription UUID
        cancel_event: Threading.Event to signal cancellation
    """
    with _task_registry_lock:
        _task_registry[transcription_id] = {
            "cancel_event": cancel_event,
            "pids": set(),  # Set of subprocess PIDs to kill on cancellation
            "stage": "registered"
        }
        logger.info(f"[TASK_REGISTRY] Registered task: {transcription_id}")


def unregister_transcription_task(transcription_id: str) -> None:
    """
    Unregister a completed transcription task.

    Args:
        transcription_id: Transcription UUID
    """
    with _task_registry_lock:
        if transcription_id in _task_registry:
            pids = _task_registry[transcription_id].get("pids", set())
            stage = _task_registry[transcription_id].get("stage", "unknown")
            del _task_registry[transcription_id]
            logger.info(
                f"[TASK_REGISTRY] Unregistered task: {transcription_id} | "
                f"Stage: {stage} | Tracked PIDs: {len(pids)}"
            )


def mark_transcription_cancelled(transcription_id: str) -> bool:
    """
    Mark a transcription as cancelled by setting its cancel event.

    Args:
        transcription_id: Transcription UUID

    Returns:
        bool: True if task was found and marked for cancellation
    """
    with _task_registry_lock:
        if transcription_id in _task_registry:
            _task_registry[transcription_id]["cancel_event"].set()
            _task_registry[transcription_id]["stage"] = "cancelled"
            logger.info(f"[TASK_REGISTRY] Marked task for cancellation: {transcription_id}")
            return True
        return False


def track_transcription_pid(transcription_id: str, pid: int) -> None:
    """
    Track a subprocess PID associated with a transcription.

    Args:
        transcription_id: Transcription UUID
        pid: Process ID to track
    """
    with _task_registry_lock:
        if transcription_id in _task_registry:
            _task_registry[transcription_id]["pids"].add(pid)
            logger.debug(f"[TASK_REGISTRY] Tracked PID {pid} for task: {transcription_id}")


def get_transcription_task_info(transcription_id: str) -> Optional[Dict]:
    """
    Get information about a registered transcription task.

    Args:
        transcription_id: Transcription UUID

    Returns:
        Dict with task info or None if not found
    """
    with _task_registry_lock:
        return _task_registry.get(transcription_id)


def is_transcription_active(transcription_id: str) -> bool:
    """
    Check if a transcription is currently active/registered.

    Args:
        transcription_id: Transcription UUID

    Returns:
        bool: True if task is registered and active
    """
    with _task_registry_lock:
        return transcription_id in _task_registry


def kill_transcription_processes(transcription_id: str) -> int:
    """
    Kill all tracked subprocesses for a transcription.

    Args:
        transcription_id: Transcription UUID

    Returns:
        int: Number of processes killed
    """
    import signal

    with _task_registry_lock:
        if transcription_id not in _task_registry:
            return 0

        pids = _task_registry[transcription_id].get("pids", set()).copy()

    killed_count = 0
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"[TASK_REGISTRY] Killed PID {pid} for task: {transcription_id}")
            killed_count += 1
        except ProcessLookupError:
            # Process already terminated
            logger.debug(f"[TASK_REGISTRY] PID {pid} already terminated for task: {transcription_id}")
        except PermissionError:
            logger.warning(f"[TASK_REGISTRY] No permission to kill PID {pid} for task: {transcription_id}")

    return killed_count

logger = logging.getLogger(__name__)

# Process stage constants
STAGE_UPLOADING = "uploading"
STAGE_TRANSCRIBING = "transcribing"
STAGE_SUMMARIZING = "summarizing"
STAGE_COMPLETED = "completed"
STAGE_FAILED = "failed"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# Log file configuration
LOG_DIR = Path("/app/logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "transcription_processor.log"


def setup_debug_logging():
    """Setup detailed debug logging to file if LOG_LEVEL is DEBUG"""
    if settings.LOG_LEVEL.upper() == "DEBUG":
        # Clear and create new log file
        if LOG_FILE.exists():
            LOG_FILE.unlink()
        LOG_FILE.touch()

        # Add file handler for detailed debug logs
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )

        # Add to root logger so all modules log to file
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.DEBUG)

        logger.info(f"DEBUG logging enabled. Log file: {LOG_FILE}")
    else:
        logger.info(f"LOG_LEVEL is {settings.LOG_LEVEL}, debug file logging disabled")


class TranscriptionProcessor:
    """Handles complete transcription workflow with retry logic"""

    def __init__(self, db_session_factory):
        """
        Initialize processor

        Args:
            db_session_factory: Callable that returns a new DB session
        """
        self.db_session_factory = db_session_factory
        setup_debug_logging()

    def process_transcription(self, transcription_id: str) -> bool:
        """
        Process transcription through complete workflow with retry

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if successful, False if failed after all retries
        """
        # Create cancellation event for this task
        cancel_event = Event()
        register_transcription_task(transcription_id, cancel_event)

        # Acquire semaphore to limit concurrent transcriptions
        semaphore = get_transcription_semaphore()
        logger.info(f"Waiting for semaphore for transcription: {transcription_id} (parallelism={settings.AUDIO_PARALLELISM})")

        with semaphore:
            logger.info(f"Acquired semaphore, starting processing: {transcription_id}")
            try:
                result = self._process_transcription_impl(transcription_id, cancel_event)
                return result
            finally:
                # Always unregister task on completion
                unregister_transcription_task(transcription_id)
                logger.info(f"Released semaphore for transcription: {transcription_id}")

    def _process_transcription_impl(self, transcription_id: str, cancel_event: Event) -> bool:
        """Internal implementation of transcription processing."""
        db = self.db_session_factory()

        try:
            transcription = db.query(Transcription).filter(
                Transcription.id == transcription_id
            ).first()

            if not transcription:
                logger.error(f"Transcription not found: {transcription_id}")
                return False

            logger.info(f"Starting processing: {transcription_id} - {transcription.file_name}")

            # Execute workflow with retry
            for attempt in range(MAX_RETRIES):
                # Check for cancellation before each attempt
                if cancel_event.is_set():
                    logger.info(f"[CANCEL] Transcription {transcription_id} cancelled before attempt {attempt + 1}")
                    transcription.stage = STAGE_FAILED
                    transcription.error_message = "Transcription cancelled by user"
                    db.commit()
                    return False

                try:
                    transcription.retry_count = attempt
                    db.commit()

                    # Step 1: Transcribe
                    if not self._transcribe_with_retry(transcription, db, cancel_event, transcription_id):
                        if cancel_event.is_set():
                            logger.info(f"[CANCEL] Transcription {transcription_id} cancelled during transcription")
                            transcription.stage = STAGE_FAILED
                            transcription.error_message = "Transcription cancelled by user"
                            db.commit()
                            return False
                        raise Exception("Transcription failed after retries")

                    # Step 2: Summarize (check cancellation again)
                    if cancel_event.is_set():
                        logger.info(f"[CANCEL] Transcription {transcription_id} cancelled before summarization")
                        transcription.stage = STAGE_FAILED
                        transcription.error_message = "Transcription cancelled by user"
                        db.commit()
                        return False

                    if not self._summarize_with_retry(transcription, db):
                        raise Exception("Summarization failed after retries")

                    # Mark as completed
                    transcription.stage = STAGE_COMPLETED
                    transcription.completed_at = datetime.utcnow()
                    transcription.error_message = None
                    db.commit()

                    logger.info(
                        f"Processing completed successfully: {transcription_id} | "
                        f"Text length: {len(transcription.original_text or '')} | "
                        f"Summary: {'Yes' if transcription.summaries else 'No'}"
                    )
                    return True

                except Exception as e:
                    logger.error(f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")

                    transcription.error_message = str(e)
                    db.commit()

                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY_SECONDS * (attempt + 1)
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        # Final attempt failed
                        transcription.stage = STAGE_FAILED
                        transcription.error_message = f"Failed after {MAX_RETRIES} attempts: {str(e)}"
                        db.commit()
                        logger.error(f"Processing failed after all retries: {transcription_id}")
                        return False

        except Exception as e:
            logger.error(f"Unexpected error in process_transcription: {e}")
            return False
        finally:
            db.close()

    def _transcribe_with_retry(
        self,
        transcription: Transcription,
        db: Session,
        cancel_event: Event,
        transcription_id: str
    ) -> bool:
        """
        Transcribe audio file with retry logic

        Args:
            transcription: Transcription model instance
            db: Database session
            cancel_event: Event to check for cancellation
            transcription_id: Transcription UUID for PID tracking

        Returns:
            bool: True if successful
        """
        # Update stage to transcribing
        transcription.stage = STAGE_TRANSCRIBING
        transcription.error_message = None
        db.commit()

        logger.debug(f"Starting transcription for: {transcription.file_name}")

        try:
            output_dir = Path("/app/data/output")
            output_dir.mkdir(exist_ok=True, parents=True)

            # Run whisper transcription with cancellation support
            result = whisper_service.transcribe(
                transcription.file_path,
                output_dir=str(output_dir),
                cancel_event=cancel_event,
                transcription_id=transcription_id
            )

            # Compress text using gzip to avoid SSL connection issues with large text
            text_bytes = result["text"].encode('utf-8')
            compressed_text = gzip.compress(text_bytes, compresslevel=6)

            # Save results
            transcription.original_text = result["text"]  # Keep for backward compatibility
            transcription.original_text_compressed = compressed_text  # New compressed field
            transcription.language = result["language"]
            transcription.duration_seconds = result.get("duration")
            transcription.error_message = None
            db.commit()

            logger.debug(
                f"Transcription successful: {transcription.id} | "
                f"Language: {result['language']} | "
                f"Text length: {len(result['text'])} | "
                f"Duration: {result.get('duration')}s"
            )
            return True

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            transcription.error_message = f"Transcription failed: {str(e)}"
            db.commit()
            raise

    def _summarize_with_retry(self, transcription: Transcription, db: Session) -> bool:
        """
        Generate summary with retry logic

        Args:
            transcription: Transcription model instance
            db: Database session

        Returns:
            bool: True if successful
        """
        if not transcription.original_text:
            logger.warning(f"No text to summarize for: {transcription.id}")
            return True  # Not an error, just nothing to summarize

        # Check if summary already exists
        existing_summary = db.query(Summary).filter(
            Summary.transcription_id == transcription.id
        ).first()

        if existing_summary:
            logger.debug(f"Summary already exists for: {transcription.id}")
            return True

        # Update stage to summarizing
        transcription.stage = STAGE_SUMMARIZING
        db.commit()

        logger.debug(f"Starting summarization for: {transcription.id}")

        try:
            gemini_client = get_gemini_client()
            # Run async function in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                gemini_response = loop.run_until_complete(
                    gemini_client.generate_summary(
                        transcription.original_text,
                        file_name=transcription.file_name
                    )
                )
            finally:
                loop.close()

            # Check for errors
            if gemini_response.status == "error":
                raise Exception(gemini_response.error_message)

            # Create summary record
            new_summary = Summary(
                transcription_id=transcription.id,
                summary_text=gemini_response.summary,
                model_name=gemini_response.model_name
            )
            db.add(new_summary)

            # Create debug log
            request_log = GeminiRequestLog(
                transcription_id=transcription.id,
                file_name=transcription.file_name,
                model_name=gemini_response.model_name,
                prompt=gemini_response.prompt,
                input_text=transcription.original_text[:5000],
                input_text_length=gemini_response.input_text_length,
                output_text=gemini_response.summary,
                output_text_length=gemini_response.output_text_length,
                input_tokens=gemini_response.input_tokens,
                output_tokens=gemini_response.output_tokens,
                total_tokens=gemini_response.total_tokens,
                response_time_ms=gemini_response.response_time_ms,
                temperature=gemini_response.temperature,
                status="success"
            )
            db.add(request_log)

            db.commit()

            logger.debug(
                f"Summarization successful: {transcription.id} | "
                f"Tokens: {gemini_response.total_tokens} | "
                f"Time: {gemini_response.response_time_ms:.0f}ms"
            )
            return True

        except Exception as e:
            logger.error(f"Summarization error: {e}")
            transcription.error_message = f"Summarization failed: {str(e)}"
            db.commit()
            raise


def should_allow_delete(transcription: Transcription) -> bool:
    """
    Check if transcription should be deletable based on age and status

    Args:
        transcription: Transcription model instance

    Returns:
        bool: True if delete button should be shown

    Note: All transcriptions are now deletable, including processing ones.
          Processing transcriptions will be cancelled and processes killed on delete.
    """
    return True
