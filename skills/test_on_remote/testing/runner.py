"""
Test runner for executing tests locally and remotely.

Handles test execution in local test containers and via SSH
on remote servers.
"""

import subprocess
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import logging

from ..config import TestOnRemoteConfig
from ..ssh import RemoteServerClient
from .parser import TestResults, parse_pytest_output

logger = logging.getLogger(__name__)


class TestRunner:
    """
    Test runner for local and remote test execution.

    Handles:
    - Local test execution in Docker containers
    - Remote test execution via SSH
    - Test result parsing and analysis
    - Regression detection
    """

    def __init__(self, config: TestOnRemoteConfig):
        self.config = config
        self.project_root = config.project_root

    def run_local_tests(
        self,
        test_path: str = None,
        pytest_args: str = None,
        timeout: int = 300
    ) -> TestResults:
        """
        Run tests in local test container.

        Args:
            test_path: Path to tests (default from config)
            pytest_args: Additional pytest arguments
            timeout: Test timeout

        Returns:
            TestResults: Test execution results
        """
        test_path = test_path or self.config.testing.test_path
        pytest_args = pytest_args or self.config.testing.pytest_args

        logger.info(f"Running local tests: {test_path}")

        # Build docker command to run tests
        cmd = [
            "docker", "exec",
            "whisper_test_prd_runner",
            "python", "-m", "pytest",
            f"/app/tests/{test_path}",
            *pytest_args.split()
        ]

        start_time = datetime.now()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )

            duration = (datetime.now() - start_time).total_seconds()
            output = result.stdout + result.stderr

            # Parse results
            parsed = parse_pytest_output(output)
            parsed.duration = duration

            logger.info(f"Local tests complete: {parsed}")

            return parsed

        except subprocess.TimeoutExpired:
            logger.error(f"Tests timed out after {timeout}s")
            return TestResults(
                total=0,
                passed=0,
                failed=1,
                duration=timeout,
                errors=[],
                failures=[]
            )
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return TestResults(
                total=0,
                passed=0,
                failed=1,
                duration=0,
                errors=[],
                failures=[]
            )

    def run_remote_tests(
        self,
        ssh_client: RemoteServerClient,
        test_path: str = None,
        pytest_args: str = None,
        timeout: int = 300
    ) -> TestResults:
        """
        Run tests on remote server via SSH.

        Args:
            ssh_client: Connected SSH client
            test_path: Path to tests on remote
            pytest_args: Additional pytest arguments
            timeout: Test timeout

        Returns:
            TestResults: Test execution results
        """
        test_path = test_path or self.config.testing.test_path
        pytest_args = pytest_args or self.config.testing.pytest_args

        logger.info(f"Running remote tests: {test_path}")

        # Build command to run in container via SSH
        # This assumes tests are run from within the server container
        # using localhost auth bypass

        # First, check if we can access the API via docker exec
        cmd = (
            f'cd /app && python -m pytest tests/{test_path} '
            f'{pytest_args} --tb=no -q'
        )

        start_time = datetime.now()

        try:
            result = ssh_client.exec_docker(
                self.config.containers.server,
                cmd,
                timeout=timeout
            )

            duration = (datetime.now() - start_time).total_seconds()

            if result.timed_out:
                logger.error(f"Remote tests timed out after {timeout}s")
                return TestResults(
                    total=0,
                    passed=0,
                    failed=1,
                    duration=timeout
                )

            # Parse results
            parsed = parse_pytest_output(result.stdout + result.stderr)
            parsed.duration = duration

            logger.info(f"Remote tests complete: {parsed}")

            return parsed

        except Exception as e:
            logger.error(f"Error running remote tests: {e}")
            return TestResults(
                total=0,
                passed=0,
                failed=1,
                duration=0
            )

    def run_remote_tests_via_runner(
        self,
        ssh_client: RemoteServerClient,
        test_path: str = None
    ) -> TestResults:
        """
        Run tests on remote server using local test runner container.

        This runs tests in a local Docker container that SSH's into
        the remote server (as done in tests/run.prd.sh).

        Args:
            ssh_client: Connected SSH client (for fallback)
            test_path: Path to tests

        Returns:
            TestResults: Test execution results
        """
        test_path = test_path or self.config.testing.test_path

        logger.info(f"Running tests via local test runner: {test_path}")

        # Use the test runner script
        test_compose = self.config.testing.get_test_compose_path(self.project_root)

        cmd = [
            "docker", "compose", "-f", str(test_compose),
            "run", "--rm",
            "-e", f"REMOTE_DEBUG_SERVER={self.config.get_ssh_connection_string()}",
            "-e", f"REMOTE_DEBUG_CONTAINER={self.config.containers.server}",
            "test-runner",
            "pytest", f"/app/tests/{test_path}",
            "-v", "--tb=short"
        ]

        start_time = datetime.now()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.testing.test_timeout,
                cwd=self.project_root
            )

            duration = (datetime.now() - start_time).total_seconds()
            output = result.stdout + result.stderr

            parsed = parse_pytest_output(output)
            parsed.duration = duration

            logger.info(f"Tests complete: {parsed}")

            return parsed

        except subprocess.TimeoutExpired:
            logger.error(f"Tests timed out after {self.config.testing.test_timeout}s")
            return TestResults(
                total=0,
                passed=0,
                failed=1,
                duration=self.config.testing.test_timeout
            )
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return TestResults(
                total=0,
                passed=0,
                failed=1,
                duration=0
            )

    def detect_regression(
        self,
        current: TestResults,
        previous: TestResults
    ) -> List[str]:
        """
        Detect test regressions between runs.

        Args:
            current: Current test results
            previous: Previous test results

        Returns:
            List of regressed test names
        """
        if not previous:
            return []

        # Tests that passed before but fail now
        previous_passed = {test.name for test in previous.tests if test.status.value == "passed"}
        current_failed = {test.name for test in current.tests if test.status.value == "failed"}

        regressed = previous_passed & current_failed

        return sorted(regressed)

    def run_specific_test(
        self,
        test_name: str,
        remote: bool = True,
        ssh_client: RemoteServerClient = None
    ) -> TestResults:
        """
        Run a specific test by name.

        Args:
            test_name: Full test name (e.g., tests/integration/test_xxx.py::TestClass::test_name)
            remote: Run on remote server
            ssh_client: SSH client (required if remote=True)

        Returns:
            TestResults: Test execution results
        """
        if remote and not ssh_client:
            raise ValueError("ssh_client required for remote test execution")

        if remote:
            return self._run_remote_test(test_name, ssh_client)
        else:
            return self._run_local_test(test_name)

    def _run_local_test(self, test_name: str) -> TestResults:
        """Run specific test locally."""
        cmd = [
            "docker", "exec",
            "whisper_test_prd_runner",
            "python", "-m", "pytest",
            f"/app/{test_name}",
            "-v"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.project_root
            )

            return parse_pytest_output(result.stdout + result.stderr)

        except Exception as e:
            logger.error(f"Error running test: {e}")
            return TestResults(total=0, passed=0, failed=1)

    def _run_remote_test(
        self,
        test_name: str,
        ssh_client: RemoteServerClient
    ) -> TestResults:
        """Run specific test on remote server."""
        cmd = f"cd /app && python -m pytest {test_name} -v --tb=no"

        try:
            result = ssh_client.exec_docker(
                self.config.containers.server,
                cmd,
                timeout=60
            )

            return parse_pytest_output(result.stdout + result.stderr)

        except Exception as e:
            logger.error(f"Error running remote test: {e}")
            return TestResults(total=0, passed=0, failed=1)

    def get_test_list(self, remote: bool = False, ssh_client: RemoteServerClient = None) -> List[str]:
        """
        Get list of available tests.

        Args:
            remote: Get from remote server
            ssh_client: SSH client (required if remote=True)

        Returns:
            List of test names
        """
        if remote and not ssh_client:
            raise ValueError("ssh_client required for remote test list")

        cmd = "python -m pytest --collect-only -q"

        if remote:
            result = ssh_client.exec_docker(
                self.config.containers.server,
                f"cd /app && {cmd}",
                timeout=30
            )
            output = result.stdout + result.stderr
        else:
            try:
                result = subprocess.run(
                    ["docker", "exec", "whisper_test_prd_runner",
                     "python", "-m", "pytest", "--collect-only", "-q"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self.project_root
                )
                output = result.stdout + result.stderr
            except Exception as e:
                logger.error(f"Error getting test list: {e}")
                return []

        # Parse test names from output
        tests = []
        for line in output.split('\n'):
            if line.strip().startswith('tests/'):
                test_name = line.split('::')[0].strip()
                tests.append(test_name)

        return tests
