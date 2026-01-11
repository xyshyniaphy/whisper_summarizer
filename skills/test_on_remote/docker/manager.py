"""
Docker manager for local container operations.

Handles Docker Compose operations for building, running, and managing
local test containers.
"""

import subprocess
import re
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

try:
    import docker
    from docker.errors import DockerException
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

from ..config import TestOnRemoteConfig

logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    """Result of a Docker build operation."""
    service: str
    success: bool
    image_id: Optional[str]
    duration: float
    output: str
    error: Optional[str] = None

    @property
    def tag(self) -> str:
        """Get the image tag."""
        if self.image_id:
            return self.image_id[:12]
        return "unknown"


@dataclass
class ContainerStatus:
    """Status of a container."""
    name: str
    running: bool
    status: str
    health: str
    ports: List[str]

    @classmethod
    def from_ps_output(cls, name: str, ps_output: str) -> 'ContainerStatus':
        """Parse docker ps output."""
        if not ps_output.strip():
            return cls(name, False, "not running", "unknown", [])

        # Parse status (format: "Up 2 hours (healthy) | 0.0.0.0:80->80/tcp")
        parts = ps_output.split(' | ')
        status = parts[0].strip()

        running = status.startswith("Up")
        health = "unknown"

        if "(healthy)" in status:
            health = "healthy"
        elif "(unhealthy)" in status:
            health = "unhealthy"
        elif "health: starting" in status:
            health = "starting"

        ports = []
        if len(parts) > 1:
            ports = [p.strip() for p in parts[1].split(', ')]

        return cls(name, running, status, health, ports)


class DockerManager:
    """
    Docker operations manager for local containers.

    Handles:
    - Docker Compose operations (up, down, build)
    - Container status monitoring
    - Image building and pushing
    - Change detection for targeted builds
    """

    def __init__(self, config: TestOnRemoteConfig):
        self.config = config
        self.project_root = config.project_root

        # Try to initialize Docker client
        self._docker_client = None
        if DOCKER_AVAILABLE:
            try:
                self._docker_client = docker.from_env()
            except DockerException as e:
                logger.warning(f"Docker client unavailable: {e}")

    def _run_compose(
        self,
        compose_file: Path,
        command: List[str],
        capture: bool = True
    ) -> subprocess.CompletedProcess:
        """Run Docker Compose command."""
        cmd = [
            "docker", "compose",
            "-f", str(compose_file),
            "-p", self.config.docker.project_name
        ] + command

        logger.debug(f"Running: {' '.join(cmd)}")

        if capture:
            return subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
        else:
            return subprocess.run(cmd, cwd=self.project_root)

    def start_test_container(self) -> bool:
        """
        Start local test container.

        Returns:
            bool: True if successful
        """
        test_compose = self.config.testing.get_test_compose_path(self.project_root)

        if not test_compose.exists():
            logger.error(f"Test compose file not found: {test_compose}")
            return False

        logger.info("Starting test container...")

        try:
            result = self._run_compose(
                test_compose,
                ["up", "-d", "test-runner"],
                capture=False
            )

            if result.returncode == 0:
                logger.info("Test container started")
                return True
            else:
                logger.error(f"Failed to start test container: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Timeout starting test container")
            return False
        except Exception as e:
            logger.error(f"Error starting test container: {e}")
            return False

    def stop_test_container(self) -> bool:
        """
        Stop local test container.

        Returns:
            bool: True if successful
        """
        test_compose = self.config.testing.get_test_compose_path(self.project_root)

        logger.info("Stopping test container...")

        try:
            result = self._run_compose(
                test_compose,
                ["down"],
                capture=False
            )

            if result.returncode == 0:
                logger.info("Test container stopped")
                return True
            else:
                logger.warning(f"Failed to stop test container: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error stopping test container: {e}")
            return False

    def build_service(self, service: str, push: bool = False) -> BuildResult:
        """
        Build a specific service.

        Args:
            service: Service name to build
            push: Whether to push after building

        Returns:
            BuildResult: Build result
        """
        main_compose = self.config.docker.get_compose_path(self.project_root)

        logger.info(f"Building service: {service}")

        start_time = datetime.now()

        try:
            result = self._run_compose(
                main_compose,
                ["build", service],
                capture=True
            )

            duration = (datetime.now() - start_time).total_seconds()
            success = result.returncode == 0

            # Extract image ID from output
            image_id = None
            if success and result.stdout:
                # Look for image ID in build output
                match = re.search(r'Successfully built ([a-f0-9]{12})', result.stdout)
                if match:
                    image_id = match.group(1)

            build_result = BuildResult(
                service=service,
                success=success,
                image_id=image_id,
                duration=duration,
                output=result.stdout,
                error=result.stderr if not success else None
            )

            if success:
                logger.info(f"Built {service}: {build_result.tag} ({duration:.1f}s)")

                if push:
                    self.push_image(service)

            return build_result

        except subprocess.TimeoutExpired:
            return BuildResult(
                service=service,
                success=False,
                image_id=None,
                duration=(datetime.now() - start_time).total_seconds(),
                output="",
                error="Build timeout"
            )
        except Exception as e:
            return BuildResult(
                service=service,
                success=False,
                image_id=None,
                duration=(datetime.now() - start_time).total_seconds(),
                output="",
                error=str(e)
            )

    def build_all_changed(self, changed_files: List[str] = None) -> List[BuildResult]:
        """
        Build all services that have changes.

        Args:
            changed_files: List of changed files (for detecting affected services)

        Returns:
            List[BuildResult]: Results of all builds
        """
        # Map files to services
        service_files = {
            'server': 'server/',
            'runner': 'runner/',
            'frontend': 'frontend/',
            'nginx': 'nginx/',
        }

        services_to_build = set()

        if changed_files:
            for file_path in changed_files:
                for service, path in service_files.items():
                    if file_path.startswith(path):
                        services_to_build.add(service)
        else:
            # Build all services
            services_to_build = service_files.keys()

        results = []
        for service in services_to_build:
            result = self.build_service(service)
            results.append(result)

        return results

    def push_image(self, service: str) -> bool:
        """
        Push service image to registry.

        Args:
            service: Service name

        Returns:
            bool: True if successful
        """
        if not self.config.docker.registry:
            logger.warning("No registry configured, skipping push")
            return True

        image_name = f"{self.config.docker.image_prefix}{service}"
        full_image = f"{self.config.docker.registry}/{image_name}"

        logger.info(f"Pushing image: {full_image}")

        try:
            result = subprocess.run(
                ["docker", "push", full_image],
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode == 0:
                logger.info(f"Pushed {full_image}")
                return True
            else:
                logger.error(f"Failed to push: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Timeout pushing image")
            return False

    def get_container_status(self, container: str) -> ContainerStatus:
        """
        Get status of a local container.

        Args:
            container: Container name

        Returns:
            ContainerStatus: Container status
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={container}",
                 "--format", "{{.Status}} | {{.Ports}}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            return ContainerStatus.from_ps_output(container, result.stdout)

        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return ContainerStatus(container, False, "error", "unknown", [])

    def get_logs(self, container: str, tail: int = 100) -> str:
        """
        Get logs from a container.

        Args:
            container: Container name
            tail: Number of lines from end

        Returns:
            str: Container logs
        """
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(tail), container],
                capture_output=True,
                text=True,
                timeout=10
            )

            return result.stdout if result.returncode == 0 else ""

        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return ""

    def is_container_running(self, container: str) -> bool:
        """
        Check if container is running.

        Args:
            container: Container name

        Returns:
            bool: True if running
        """
        status = self.get_container_status(container)
        return status.running

    def restart_container(self, container: str) -> bool:
        """
        Restart a container.

        Args:
            container: Container name

        Returns:
            bool: True if successful
        """
        logger.info(f"Restarting container: {container}")

        try:
            result = subprocess.run(
                ["docker", "restart", container],
                capture_output=True,
                text=True,
                timeout=60
            )

            success = result.returncode == 0
            if success:
                logger.info(f"Restarted {container}")
            else:
                logger.error(f"Failed to restart: {result.stderr}")

            return success

        except Exception as e:
            logger.error(f"Error restarting container: {e}")
            return False
