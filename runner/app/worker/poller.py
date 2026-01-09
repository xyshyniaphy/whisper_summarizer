"""Main polling loop for runner"""
import asyncio
import signal
import sys
from typing import Set
from concurrent.futures import ThreadPoolExecutor
import logging

from ..services.job_client import JobClient
from ..services.audio_processor import AudioProcessor
from ..config import settings
from ..models.job_schemas import Job

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RunnerPoller:
    """
    Main polling loop for the runner service.

    Continuously polls the server for pending jobs, processes them,
    and submits results. Handles graceful shutdown and job concurrency.
    """

    def __init__(self):
        self.client = JobClient()
        self.processor = AudioProcessor()
        self.running = False
        self.active_jobs: Set[str] = set()
        self.executor = ThreadPoolExecutor(max_workers=settings.max_concurrent_jobs)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        logger.info(f"RunnerPoller initialized: {settings.runner_id}")
        logger.info(f"Max concurrent jobs: {settings.max_concurrent_jobs}")
        logger.info(f"Poll interval: {settings.poll_interval_seconds}s")

    def _shutdown(self, signum, frame):
        """Handle shutdown signal gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
        sys.exit(0)

    async def process_job(self, job: Job):
        """
        Process a single job end-to-end.

        Args:
            job: Job to process
        """
        job_id = job.id
        logger.info(f"[{job_id}] Processing {job.file_name}")

        # Step 1: Claim the job
        if not self.client.start_job(job_id):
            logger.error(f"[{job_id}] Failed to claim job")
            return

        # Step 2: Get audio file info
        audio_info = self.client.get_audio_info(job_id)
        if not audio_info:
            self.client.fail_job(job_id, "Failed to get audio file information")
            return

        download_url = audio_info.get("download_url")
        if not download_url:
            self.client.fail_job(job_id, "No download URL provided")
            return

        # Step 3: Download audio via HTTP
        local_audio_path = f"/tmp/whisper_runner/{job_id}.m4a"
        logger.info(f"[{job_id}] Downloading audio from {download_url}")

        if not self.client.download_audio(job_id, download_url, local_audio_path):
            self.client.fail_job(job_id, f"Failed to download audio from {download_url}")
            return

        # Step 4: Process the audio
        try:
            logger.info(f"[{job_id}] Processing audio: {local_audio_path}")
            result = self.processor.process(
                audio_path=local_audio_path,
                language=job.language or settings.whisper_language
            )

            # Step 5: Submit result
            if self.client.complete_job(job_id, result):
                logger.info(f"[{job_id}] Completed successfully in {result.processing_time_seconds}s")
            else:
                logger.error(f"[{job_id}] Failed to submit result")

        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            logger.error(f"[{job_id}] {error_msg}")
            self.client.fail_job(job_id, error_msg)

        finally:
            # Clean up downloaded audio file
            if os.path.exists(local_audio_path):
                try:
                    os.remove(local_audio_path)
                    logger.debug(f"[{job_id}] Cleaned up audio: {local_audio_path}")
                except Exception as e:
                    logger.warning(f"[{job_id}] Failed to cleanup audio: {e}")

            self.active_jobs.discard(job_id)

    async def poll_loop(self):
        """Main polling loop."""
        logger.info("Starting poll loop...")
        self.running = True

        while self.running:
            try:
                # Send heartbeat
                self.client.send_heartbeat(len(self.active_jobs))

                # Check if we can accept more jobs
                if len(self.active_jobs) >= settings.max_concurrent_jobs:
                    logger.debug(f"Max concurrent jobs reached ({len(self.active_jobs)})")
                    await asyncio.sleep(settings.poll_interval_seconds)
                    continue

                # Fetch pending jobs (only as many as we can handle)
                slots_available = settings.max_concurrent_jobs - len(self.active_jobs)
                jobs = self.client.get_pending_jobs(limit=slots_available)

                if not jobs:
                    await asyncio.sleep(settings.poll_interval_seconds)
                    continue

                logger.info(f"Found {len(jobs)} pending jobs, starting processing...")

                # Process jobs concurrently
                tasks = []
                for job in jobs:
                    self.active_jobs.add(job.id)
                    # Create task for concurrent processing
                    task = asyncio.create_task(self.process_job(job))
                    tasks.append(task)

                # Wait a bit before next poll to avoid overwhelming the system
                await asyncio.sleep(settings.poll_interval_seconds)

            except Exception as e:
                logger.error(f"Error in poll loop: {e}", exc_info=True)
                await asyncio.sleep(settings.poll_interval_seconds)

        logger.info("Poll loop stopped")

    def run(self):
        """Run the poller synchronously."""
        try:
            asyncio.run(self.poll_loop())
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.client.close()
            self.executor.shutdown(wait=True)
            logger.info("RunnerPoller shutdown complete")


def main():
    """Entry point for runner service."""
    poller = RunnerPoller()
    poller.run()


if __name__ == "__main__":
    # Import os for file operations
    import os
    main()
