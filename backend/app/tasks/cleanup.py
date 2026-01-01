"""
Scheduled task for automatic cleanup of expired transcriptions.

Runs daily at 9:00 AM (configurable via CLEANUP_HOUR) to delete
transcriptions older than MAX_KEEP_DAYS.
"""

import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.transcription import Transcription
from app.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()


async def cleanup_expired_transcriptions() -> dict:
    """
    Delete transcriptions that have exceeded MAX_KEEP_DAYS.

    This task:
    1. Queries for transcriptions older than MAX_KEEP_DAYS
    2. Deletes the associated text file from storage
    3. Deletes the database record (cascade deletes summaries and logs)

    Returns:
        dict with statistics about the cleanup operation
    """
    db = SessionLocal()
    stats = {
        "deleted_count": 0,
        "failed_count": 0,
        "errors": []
    }

    try:
        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.MAX_KEEP_DAYS)

        # Query for expired transcriptions
        expired_transcriptions = db.query(Transcription).filter(
            Transcription.created_at < cutoff_date
        ).all()

        logger.info(
            f"Found {len(expired_transcriptions)} expired transcriptions "
            f"older than {settings.MAX_KEEP_DAYS} days"
        )

        storage_service = get_storage_service()

        for transcription in expired_transcriptions:
            try:
                # Delete text file from storage
                if transcription.storage_path:
                    storage_service.delete_transcription_text(str(transcription.id))

                # Delete database record (cascade deletes related records)
                db.delete(transcription)
                stats["deleted_count"] += 1

                logger.info(f"Deleted expired transcription: {transcription.id} ({transcription.file_name})")

            except Exception as e:
                stats["failed_count"] += 1
                error_msg = f"Failed to delete {transcription.id}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg)

        # Commit all deletions
        db.commit()

        logger.info(
            f"Cleanup complete: {stats['deleted_count']} deleted, "
            f"{stats['failed_count']} failed"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Cleanup task failed: {str(e)}", exc_info=True)
        stats["errors"].append(f"Task failed: {str(e)}")

    finally:
        db.close()

    return stats


def start_scheduler() -> None:
    """
    Start the APScheduler with daily cleanup task.

    The scheduler runs at CLEANUP_HOUR (default: 9 AM) every day.
    """
    # Using cron trigger: run at specified hour daily
    trigger = CronTrigger(hour=settings.CLEANUP_HOUR, minute=0)

    scheduler.add_job(
        cleanup_expired_transcriptions,
        trigger=trigger,
        id="cleanup_expired_transcriptions",
        name="Daily cleanup of expired transcriptions",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )

    scheduler.start()
    logger.info(
        f"Scheduler started: cleanup task runs daily at {settings.CLEANUP_HOUR}:00"
    )


def stop_scheduler() -> None:
    """Stop the APScheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
