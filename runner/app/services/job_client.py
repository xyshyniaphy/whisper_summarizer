"""Client for communicating with server"""
import httpx
import logging
import os
from typing import List, Optional
import time

from ..models.job_schemas import Job, JobResult
from ..config import settings

logger = logging.getLogger(__name__)


class JobClient:
    """
    HTTP client for runner-server communication.

    Handles all communication between the runner and the server:
    - Polling for pending jobs
    - Claiming jobs
    - Getting audio file paths
    - Submitting results
    - Reporting failures
    - Sending heartbeats
    """

    def __init__(self):
        self.base_url = settings.server_url.rstrip('/')
        self.api_key = settings.runner_api_key
        self.runner_id = settings.runner_id
        self.client = httpx.Client(
            base_url=f"{self.base_url}/api/runner",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0  # Longer timeout for audio operations
        )
        logger.info(f"JobClient initialized: server={self.base_url}, runner_id={self.runner_id}")

    def get_pending_jobs(self, limit: int = 1) -> List[Job]:
        """
        Get pending jobs from server.

        Args:
            limit: Maximum number of jobs to fetch

        Returns:
            List of pending jobs
        """
        try:
            response = self.client.get(
                "/jobs",
                params={"status": "pending", "limit": limit}
            )
            response.raise_for_status()
            jobs = [Job(**job) for job in response.json()]
            logger.info(f"Fetched {len(jobs)} pending jobs")
            return jobs
        except httpx.HTTPError as e:
            logger.error(f"Error fetching jobs: {e}")
            return []

    def start_job(self, job_id: str) -> bool:
        """
        Claim a job from server.

        Args:
            job_id: UUID of the job to claim

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.post(
                f"/jobs/{job_id}/start",
                json={"runner_id": self.runner_id}
            )
            response.raise_for_status()
            logger.info(f"Job {job_id} claimed successfully")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Error starting job {job_id}: {e}")
            return False

    def get_audio_info(self, job_id: str) -> Optional[dict]:
        """
        Get audio file information for a job.

        Args:
            job_id: UUID of the job

        Returns:
            Audio file info dict or None if failed
        """
        try:
            response = self.client.get(f"/audio/{job_id}")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Audio info for job {job_id}: {data.get('file_path')}, download_url={data.get('download_url')}")
            return data
        except httpx.HTTPError as e:
            logger.error(f"Error getting audio for job {job_id}: {e}")
            return None

    def download_audio(self, job_id: str, download_url: str, local_path: str) -> bool:
        """
        Download audio file from server to local path.

        Args:
            job_id: UUID of the job
            download_url: URL to download the audio from (can be relative or absolute)
            local_path: Local path to save the audio file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Construct full URL if relative
            if download_url.startswith("/"):
                full_url = f"{self.base_url}{download_url}"
            else:
                full_url = download_url

            # Use a separate client without the /api/runner base path for full URLs
            download_client = httpx.Client(timeout=300.0)  # 5 min timeout for large files
            response = download_client.get(
                full_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                follow_redirects=True
            )
            response.raise_for_status()

            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Write file
            with open(local_path, 'wb') as f:
                f.write(response.content)

            file_size = os.path.getsize(local_path)
            logger.info(f"Downloaded audio for job {job_id}: {local_path} ({file_size} bytes)")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Error downloading audio for job {job_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error saving audio for job {job_id}: {e}")
            return False
        finally:
            try:
                download_client.close()
            except:
                pass

    def complete_job(self, job_id: str, result: JobResult) -> bool:
        """
        Submit job result to server.

        Args:
            job_id: UUID of the job
            result: Processing result

        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                "text": result.text,
                "summary": result.summary,
                "notebooklm_guideline": result.notebooklm_guideline,
                "processing_time_seconds": result.processing_time_seconds
            }
            # Add segments if available (for individual timestamp preservation)
            if result.segments:
                payload["segments"] = result.segments
                logger.info(f"Sending {len(result.segments)} segments for job {job_id}")

            response = self.client.post(
                f"/jobs/{job_id}/complete",
                json=payload
            )
            response.raise_for_status()
            logger.info(f"Job {job_id} completed successfully")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Error completing job {job_id}: {e}")
            return False

    def fail_job(self, job_id: str, error: str) -> bool:
        """
        Report job failure to server.

        Args:
            job_id: UUID of the job
            error: Error message

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.post(
                f"/jobs/{job_id}/fail",
                params={"error_message": error}
            )
            response.raise_for_status()
            logger.error(f"Job {job_id} failed: {error}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Error reporting failure for job {job_id}: {e}")
            return False

    def send_heartbeat(self, current_jobs: int = 0) -> bool:
        """
        Send heartbeat to server.

        Args:
            current_jobs: Number of currently active jobs

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.post(
                "/heartbeat",
                json={"runner_id": self.runner_id, "current_jobs": current_jobs}
            )
            success = response.status_code == 200
            if success:
                logger.debug(f"Heartbeat sent: {current_jobs} active jobs")
            return success
        except httpx.HTTPError:
            return False

    def close(self):
        """Close the HTTP client."""
        try:
            self.client.close()
            logger.info("JobClient closed")
        except Exception as e:
            logger.error(f"Error closing JobClient: {e}")
