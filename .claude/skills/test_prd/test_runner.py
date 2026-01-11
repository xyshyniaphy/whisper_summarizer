"""
Test runner for remote test execution.

Handles test execution via docker exec on remote containers.
"""

import re
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class TestCase:
    """Single test case result."""
    name: str
    status: str  # passed, failed, skipped, error
    duration: float = 0.0
    error_message: str = ""
    traceback: str = ""

    @property
    def is_failure(self) -> bool:
        return self.status in ("failed", "error")

    @property
    def is_passed(self) -> bool:
        return self.status == "passed"


@dataclass
class TestResults:
    """Complete test run results."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    tests: List[TestCase] = field(default_factory=list)

    @property
    def failures(self) -> List[TestCase]:
        return [t for t in self.tests if t.is_failure]

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.errors == 0

    def get_summary(self) -> str:
        """Get summary string."""
        return f"{self.passed} passed, {self.failed} failed, {self.skipped} skipped"

    def __str__(self) -> str:
        return f"Tests: {self.get_summary()} ({self.duration:.1f}s)"


class TestRunner:
    """
    Test runner for remote test execution.

    Executes tests via docker exec on remote containers.
    """

    # Pytest output patterns
    SUMMARY_PATTERN = re.compile(r'(\d+)\s+passed,\s+(\d+)\s+failed(?:,\s+(\d+)\s+skipped)?')
    DURATION_PATTERN = re.compile(r'in\s+(\d+\.?\d*)s')
    TEST_PATTERN = re.compile(r'(test_\w+)\s+(PASSED|FAILED|ERROR|SKIP)')
    FAIL_PATTERN = re.compile(r'FAILED\s+(test_\w+)')

    def __init__(self, config, ssh_client, verbose: bool = False):
        """
        Initialize test runner.

        Args:
            config: ServerConfigFull configuration
            ssh_client: SSHClient instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.ssh = ssh_client
        self.verbose = verbose

    def run_tests(self) -> TestResults:
        """
        Run tests on remote server.

        Returns:
            TestResults: Test execution results
        """
        # Build test command
        test_path = self.config.testing.get("test_path", "tests/integration")
        pytest_args = self.config.testing.get("pytest_args", "-v --tb=short")
        test_timeout = self.config.testing.get("test_timeout", 300)

        # Execute via docker exec on remote server
        container = self.config.containers.server
        command = f"cd /app && python -m pytest {test_path} {pytest_args} --color=no"

        if self.verbose:
            print(f"[TEST] Running: {command}")

        result = self.ssh.docker_exec(container, command)

        # Parse output
        return self._parse_output(result.stdout, result.stderr)

    def _parse_output(self, stdout: str, stderr: str) -> TestResults:
        """
        Parse pytest output.

        Args:
            stdout: Standard output
            stderr: Standard error

        Returns:
            TestResults: Parsed results
        """
        output = stdout + "\n" + stderr

        results = TestResults()
        tests_seen = set()

        # Parse summary line
        summary_match = self.SUMMARY_PATTERN.search(output)
        if summary_match:
            results.passed = int(summary_match.group(1))
            results.failed = int(summary_match.group(2))
            results.skipped = int(summary_match.group(3)) if summary_match.group(3) else 0
            results.total = results.passed + results.failed + results.skipped

        # Parse duration
        duration_match = self.DURATION_PATTERN.search(output)
        if duration_match:
            results.duration = float(duration_match.group(1))

        # Parse test results (simple pattern matching)
        for match in self.TEST_PATTERN.finditer(output):
            name = match.group(1)
            status = match.group(2).lower()

            if name not in tests_seen:
                tests_seen.add(name)
                results.tests.append(TestCase(
                    name=name,
                    status=status
                ))

        # Parse failures
        for match in self.FAIL_PATTERN.finditer(output):
            name = match.group(1)

            # Find existing test or create new
            test = next((t for t in results.tests if t.name == name), None)
            if test:
                test.status = "failed"
            elif name not in tests_seen:
                tests_seen.add(name)
                results.tests.append(TestCase(
                    name=name,
                    status="failed"
                ))

        # If we have summary but no individual tests, create placeholder tests
        if not results.tests and results.total > 0:
            for i in range(min(results.passed, 10)):
                results.tests.append(TestCase(
                    name=f"test_{i}",
                    status="passed"
                ))
            for i in range(min(results.failed, 10)):
                results.tests.append(TestCase(
                    name=f"failed_test_{i}",
                    status="failed"
                ))

        return results

    def detect_regression(self, new_results: TestResults, old_results: TestResults) -> List[str]:
        """
        Detect new test failures (regressions).

        Args:
            new_results: New test results
            old_results: Old test results

        Returns:
            List of newly failed test names
        """
        old_passed = {t.name for t in old_results.tests if t.is_passed}
        new_failed = {t.name for t in new_results.tests if t.is_failure}

        return list(new_failed & old_passed)


class LocalTestRunner:
    """
    Local test runner for development/testing.

    Runs tests locally using docker compose.
    """

    def __init__(self, config, verbose: bool = False):
        """
        Initialize local test runner.

        Args:
            config: ServerConfigFull configuration
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose

    def run_tests(self) -> TestResults:
        """
        Run tests locally via docker compose.

        Returns:
            TestResults: Test execution results
        """
        test_compose = self.config.testing.get("test_compose", "tests/docker-compose.test.prd.yml")
        test_path = self.config.testing.get("test_path", "tests/integration")
        pytest_args = self.config.testing.get("pytest_args", "-v --tb=short")

        project_root = Path.cwd()
        compose_file = project_root / test_compose

        if not compose_file.exists():
            # Fallback to running in current directory
            compose_file = Path("tests/docker-compose.test.prd.yml")

        # Build docker compose command
        cmd = [
            "docker", "compose", "-f", str(compose_file),
            "run", "--rm",
            "test-runner",
            "pytest", f"/app/{test_path}", pytest_args
        ]

        if self.verbose:
            print(f"[TEST] Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            output = result.stdout + "\n" + result.stderr
            return self._parse_output(output)

        except subprocess.TimeoutExpired:
            return TestResults(total=0, failed=1)
        except Exception as e:
            return TestResults(total=0, failed=1)

    def _parse_output(self, output: str) -> TestResults:
        """Parse pytest output."""
        results = TestResults()

        # Parse summary
        summary_match = TestRunner.SUMMARY_PATTERN.search(output)
        if summary_match:
            results.passed = int(summary_match.group(1))
            results.failed = int(summary_match.group(2))
            results.skipped = int(summary_match.group(3)) if summary_match.group(3) else 0
            results.total = results.passed + results.failed + results.skipped

        # Parse duration
        duration_match = TestRunner.DURATION_PATTERN.search(output)
        if duration_match:
            results.duration = float(duration_match.group(1))

        # Parse tests
        for match in TestRunner.TEST_PATTERN.finditer(output):
            name = match.group(1)
            status = match.group(2).lower()
            results.tests.append(TestCase(
                name=name,
                status=status
            ))

        return results
