"""
SSH client for remote server operations.

Handles SSH connection, command execution, and container operations
on remote production server.
"""

import paramiko
import socket
from pathlib import Path
from typing import Optional, Tuple, List, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from ..config import TestOnRemoteConfig

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of a remote command execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.exit_code == 0 and not self.timed_out

    def __str__(self) -> str:
        """String representation."""
        if self.timed_out:
            return f"Command timed out after {self.duration:.1f}s"
        if self.success:
            return f"Success (exit: {self.exit_code}, {self.duration:.1f}s)"
        return f"Failed (exit: {self.exit_code}, {self.duration:.1f}s)"


class SSHConnectionError(Exception):
    """Raised when SSH connection fails."""
    pass


class SSHCommandError(Exception):
    """Raised when SSH command execution fails."""
    pass


class RemoteServerClient:
    """
    SSH client for remote server operations.

    Handles:
    - SSH connection with Ed25519 key authentication
    - Remote command execution
    - Docker container operations
    - Log streaming
    - Health checks
    """

    def __init__(self, config: TestOnRemoteConfig):
        self.config = config
        self.client: Optional[paramiko.SSHClient] = None
        self._connected = False

    def connect(self) -> None:
        """
        Establish SSH connection to remote server.

        Raises:
            SSHConnectionError: If connection fails
        """
        if self._connected:
            logger.debug("Already connected to remote server")
            return

        try:
            self.client = paramiko.SSHClient()
            self.client.load_system_host_keys(str(self.config.ssh.expand_known_hosts_path()))
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            key_path = self.config.ssh.expand_key_path()

            logger.info(f"Connecting to {self.config.get_ssh_connection_string()}...")

            # Load Ed25519 key
            try:
                key = paramiko.Ed25519Key.from_private_key_file(str(key_path))
            except paramiko.PasswordRequiredException:
                raise SSHConnectionError(
                    f"SSH key requires password: {key_path}\n"
                    "Please use a key without passphrase or add to SSH agent."
                )
            except paramiko.SSHException as e:
                raise SSHConnectionError(f"Failed to load SSH key: {e}")

            # Connect
            self.client.connect(
                hostname=self.config.server.host,
                port=self.config.server.port,
                username=self.config.server.user,
                pkey=key,
                timeout=self.config.ssh.connect_timeout,
                banner_timeout=30,
            )

            self._connected = True
            logger.info(f"Connected to {self.config.get_ssh_connection_string()}")

        except paramiko.AuthenticationException:
            raise SSHConnectionError("SSH authentication failed. Check your key permissions.")
        except paramiko.SSHException as e:
            raise SSHConnectionError(f"SSH connection error: {e}")
        except socket.timeout:
            raise SSHConnectionError(f"Connection timeout to {self.config.server.host}")
        except Exception as e:
            raise SSHConnectionError(f"Unexpected error connecting: {e}")

    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.client and self._connected:
            self.client.close()
            self._connected = False
            logger.info("Disconnected from remote server")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def exec_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        check: bool = False
    ) -> CommandResult:
        """
        Execute command on remote server.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds (default from config)
            check: Raise exception if command fails

        Returns:
            CommandResult: Command execution result

        Raises:
            SSHCommandError: If command fails and check=True
        """
        if not self._connected:
            raise SSHConnectionError("Not connected to remote server")

        timeout = timeout or self.config.ssh.command_timeout

        logger.debug(f"Executing remote command: {command[:100]}...")

        start_time = datetime.now()
        stdout = ""
        stderr = ""
        exit_code = 0
        timed_out = False

        try:
            stdin, channel = self.client.exec_command(command, timeout=timeout)

            # Read stdout and stderr
            while True:
                if channel.recv_ready():
                    stdout += channel.recv(1024).decode('utf-8', errors='replace')
                if channel.recv_stderr_ready():
                    stderr += channel.recv_stderr(1024).decode('utf-8', errors='replace')

                if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                    break

            exit_code = channel.recv_exit_status() or 0

        except socket.timeout:
            timed_out = True
            logger.warning(f"Command timed out after {timeout}s: {command[:50]}...")
            try:
                channel.close()
            except:
                pass

        duration = (datetime.now() - start_time).total_seconds()

        result = CommandResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            timed_out=timed_out
        )

        if check and not result.success:
            raise SSHCommandError(
                f"Command failed with exit code {exit_code}: {command[:100]}\n"
                f"stderr: {stderr[:500]}"
            )

        return result

    def exec_docker(
        self,
        container: str,
        command: str,
        timeout: Optional[int] = None
    ) -> CommandResult:
        """
        Execute command inside a Docker container on remote server.

        Args:
            container: Container name
            command: Command to execute inside container
            timeout: Command timeout

        Returns:
            CommandResult: Command execution result
        """
        docker_cmd = f"docker exec {container} {command}"
        return self.exec_command(docker_cmd, timeout=timeout)

    def get_container_logs(
        self,
        container: str,
        tail: int = 100,
        follow: bool = False
    ) -> str:
        """
        Get logs from a container.

        Args:
            container: Container name
            tail: Number of lines from end
            follow: Whether to follow logs (not implemented)

        Returns:
            str: Container logs
        """
        cmd = f"docker logs --tail {tail} {container}"
        result = self.exec_command(cmd)
        return result.stdout if result.success else ""

    def restart_container(
        self,
        container: str,
        timeout: int = 60
    ) -> CommandResult:
        """
        Restart a container on remote server.

        Args:
            container: Container name
            timeout: Wait timeout for container to be healthy

        Returns:
            CommandResult: Restart result
        """
        logger.info(f"Restarting container: {container}")

        restart_cmd = f"docker restart {container}"
        result = self.exec_command(restart_cmd, timeout=30)

        if result.success:
            # Wait for container to be healthy
            logger.info(f"Waiting for {container} to be healthy...")
            # Could add health check here

        return result

    def pull_image(self, image: str, timeout: int = 300) -> CommandResult:
        """
        Pull a Docker image on remote server.

        Args:
            image: Image name with tag
            timeout: Pull timeout

        Returns:
            CommandResult: Pull result
        """
        logger.info(f"Pulling image on remote: {image}")
        pull_cmd = f"docker pull {image}"
        return self.exec_command(pull_cmd, timeout=timeout)

    def get_container_status(self, container: str) -> dict:
        """
        Get container status information.

        Args:
            container: Container name

        Returns:
            dict: Container status with keys: running, health, uptime, etc.
        """
        # Check if container is running
        ps_cmd = f"docker ps --filter 'name={container}' --format '{{{{.Status}}}'"
        result = self.exec_command(ps_cmd)

        if not result.success or not result.stdout.strip():
            return {"running": False, "health": "not running"}

        status_line = result.stdout.strip()

        # Parse status (e.g., "Up 2 hours (healthy)")
        running = True
        health = "unknown"

        if "healthy" in status_line.lower():
            health = "healthy"
        elif "unhealthy" in status_line.lower():
            health = "unhealthy"
        elif "starting" in status_line.lower() or "health: starting" in status_line.lower():
            health = "starting"

        return {
            "running": running,
            "health": health,
            "status": status_line
        }

    def check_health(self) -> dict:
        """
        Check health of all configured containers.

        Returns:
            dict: Health status of all containers
        """
        health_status = {}

        for container in self.config.containers.get_all():
            try:
                status = self.get_container_status(container)
                health_status[container] = status
            except Exception as e:
                health_status[container] = {
                    "running": False,
                    "health": "error",
                    "error": str(e)
                }

        return health_status

    def wait_for_healthy(
        self,
        container: str,
        timeout: int = 60,
        interval: int = 5
    ) -> bool:
        """
        Wait for container to become healthy.

        Args:
            container: Container name
            timeout: Maximum wait time
            interval: Check interval

        Returns:
            bool: True if container became healthy, False if timeout
        """
        import time
        start = datetime.now()

        while (datetime.now() - start).total_seconds() < timeout:
            status = self.get_container_status(container)

            if status.get("health") == "healthy":
                logger.info(f"Container {container} is healthy")
                return True

            if not status.get("running"):
                logger.warning(f"Container {container} is not running")
                return False

            logger.debug(f"Container {container} status: {status.get('health')}")
            time.sleep(interval)

        logger.warning(f"Timeout waiting for {container} to be healthy")
        return False

    def get_disk_usage(self, path: str = "/var/lib/docker") -> dict:
        """
        Get disk usage on remote server.

        Args:
            path: Path to check

        Returns:
            dict: Disk usage info
        """
        cmd = f"df -h {path}"
        result = self.exec_command(cmd)

        if not result.success:
            return {"error": result.stderr}

        # Parse df output
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            return {
                "filesystem": parts[0],
                "size": parts[1],
                "used": parts[2],
                "available": parts[3],
                "use_percent": parts[4],
                "mountpoint": parts[5] if len(parts) > 5 else path
            }

        return {}

    def get_system_info(self) -> dict:
        """
        Get system information from remote server.

        Returns:
            dict: System info (hostname, os, docker version, etc.)
        """
        info = {}

        # Hostname
        result = self.exec_command("hostname")
        if result.success:
            info["hostname"] = result.stdout.strip()

        # OS info
        result = self.exec_command("cat /etc/os-release | grep PRETTY_NAME")
        if result.success:
            info["os"] = result.stdout.split('=')[1].strip().strip('"')

        # Docker version
        result = self.exec_command("docker --version")
        if result.success:
            info["docker_version"] = result.stdout.strip()

        # Uptime
        result = self.exec_command("uptime")
        if result.success:
            info["uptime"] = result.stdout.strip()

        return info
