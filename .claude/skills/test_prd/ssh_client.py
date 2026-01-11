"""
SSH client for remote server operations.

Provides SSH connectivity and command execution on remote servers.
"""

import paramiko
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List


class SSHError(Exception):
    """SSH operation error."""
    pass


@dataclass
class CommandResult:
    """Result of a command execution."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration: float = 0.0


class SSHClient:
    """
    SSH client for remote server operations.

    Handles SSH connections, command execution, and Docker operations.
    """

    def __init__(self, config, verbose: bool = False):
        """
        Initialize SSH client.

        Args:
            config: ServerConfigFull configuration object
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.client: Optional[paramiko.SSHClient] = None
        self._connected = False

    def connect(self) -> None:
        """
        Establish SSH connection to remote server.

        Raises:
            SSHError: If connection fails
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.load_system_host_keys(str(
                Path(self.config.ssh.known_hosts_path).expanduser()
            ))
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Load private key
            key_path = self.config.ssh.expand_key_path()
            if not key_path.exists():
                raise SSHError(f"SSH key not found: {key_path}")

            key = paramiko.Ed25519Key.from_private_key_file(str(key_path))

            if self.verbose:
                print(f"[SSH] Connecting to {self.config.server.host}:{self.config.server.port}")

            self.client.connect(
                hostname=self.config.server.host,
                port=self.config.server.port,
                username=self.config.server.user,
                pkey=key,
                timeout=self.config.ssh.connect_timeout,
                banner_timeout=30
            )

            self._connected = True

        except paramiko.AuthenticationException:
            raise SSHError("SSH authentication failed")
        except paramiko.SSHException as e:
            raise SSHError(f"SSH connection error: {e}")
        except FileNotFoundError:
            raise SSHError(f"SSH key not found: {key_path}")
        except Exception as e:
            raise SSHError(f"Failed to connect: {e}")

    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.client:
            try:
                self.client.close()
            except:
                pass
            self._connected = False

    def exec_command(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        """
        Execute command on remote server.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            CommandResult: Execution result
        """
        if not self._connected:
            raise SSHError("Not connected to server")

        timeout = timeout or self.config.ssh.command_timeout

        if self.verbose:
            print(f"[SSH] Executing: {command}")

        start_time = time.time()

        try:
            stdin, stdout, stderr = self.client.exec_command(
                command,
                timeout=timeout,
                get_pty=True
            )

            exit_status = stdout.channel.recv_exit_status()
            stdout_str = stdout.read().decode('utf-8', errors='replace')
            stderr_str = stderr.read().decode('utf-8', errors='replace')

            duration = time.time() - start_time

            return CommandResult(
                success=(exit_status == 0),
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=exit_status,
                duration=duration
            )

        except paramiko.SSHException as e:
            raise SSHError(f"Command execution error: {e}")
        except Exception as e:
            raise SSHError(f"Failed to execute command: {e}")

    def docker_exec(self, container: str, command: str) -> CommandResult:
        """
        Execute command inside a Docker container.

        Args:
            container: Container name
            command: Command to execute

        Returns:
            CommandResult: Execution result
        """
        docker_cmd = f"docker exec {container} {command}"
        return self.exec_command(docker_cmd)

    def check_health(self) -> dict:
        """
        Check health of containers.

        Returns:
            dict: Health status of containers
        """
        health = {}

        for container in self.config.containers.get_all():
            try:
                result = self.exec_command(
                    f"docker inspect --format='{{{{.State.Status}}}}' {container} 2>/dev/null || echo 'not-found'",
                    timeout=10
                )

                status = result.stdout.strip().split('\n')[-1]
                health[container] = status

            except Exception:
                health[container] = "unknown"

        return health

    def restart_container(self, container: str, timeout: int = 60) -> CommandResult:
        """
        Restart a container on remote server.

        Args:
            container: Container name
            timeout: Wait timeout in seconds

        Returns:
            CommandResult: Restart result
        """
        result = self.exec_command(f"docker restart {container}", timeout=10)

        if result.success:
            # Wait for container to be healthy
            if self.verbose:
                print(f"[SSH] Waiting for {container} to be healthy...")

            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    check_result = self.exec_command(
                        f"docker inspect --format='{{{{.State.Status}}}}' {container}",
                        timeout=5
                    )
                    if "running" in check_result.stdout:
                        return result
                except:
                    pass
                time.sleep(2)

        return result

    def pull_image(self, image: str, timeout: int = 300) -> CommandResult:
        """
        Pull a Docker image on remote server.

        Args:
            image: Image name
            timeout: Pull timeout in seconds

        Returns:
            CommandResult: Pull result
        """
        if self.verbose:
            print(f"[SSH] Pulling image: {image}")

        return self.exec_command(f"docker pull {image}", timeout=timeout)

    def get_logs(self, container: str, tail: int = 100) -> CommandResult:
        """
        Get logs from a container.

        Args:
            container: Container name
            tail: Number of lines to get

        Returns:
            CommandResult: Logs
        """
        return self.exec_command(f"docker logs --tail {tail} {container}", timeout=30)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
