"""
Test result parser for pytest output.

Parses pytest output and extracts structured information about
test results, failures, and errors.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class TestCase:
    """Single test case result."""
    name: str
    status: TestStatus
    duration: float = 0.0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    module: str = ""
    class_name: str = ""

    @property
    def short_name(self) -> str:
        """Get short test name."""
        parts = self.name.split("::")
        if len(parts) > 2:
            return "::".join(parts[-2:])
        return self.name

    @property
    def is_failure(self) -> bool:
        """Check if test failed."""
        return self.status == TestStatus.FAILED

    @property
    def is_error(self) -> bool:
        """Check if test had error."""
        return self.status == TestStatus.ERROR


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
    failures: List[TestCase] = field(default_factory=list)
    errors: List[TestCase] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.now)
    pytest_version: str = ""
    python_version: str = ""

    @property
    def success_rate(self) -> float:
        """Get success rate (0-1)."""
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    @property
    def all_passed(self) -> bool:
        """Check if all tests passed."""
        return self.failed == 0 and self.errors == 0

    @property
    def has_failures(self) -> bool:
        """Check if there are any failures."""
        return self.failed > 0 or self.errors > 0

    def get_failure_summary(self) -> str:
        """Get summary of failures."""
        if not self.has_failures:
            return "All tests passed"

        lines = [f"Failures: {self.failed} failed, {self.errors} errors"]

        for test in self.failures[:5]:  # Show first 5
            lines.append(f"  - {test.short_name}: {test.error_message or test.error_type or 'Unknown error'}")

        if len(self.failures) > 5:
            lines.append(f"  ... and {len(self.failures) - 5} more")

        return "\n".join(lines)

    def get_new_failures(self, previous: 'TestResults') -> List[TestCase]:
        """
        Get tests that failed in this run but passed in previous run.

        Args:
            previous: Previous test results

        Returns:
            List of newly failed tests
        """
        if not previous:
            return self.failures

        previous_passed = {test.name for test in previous.tests if test.status == TestStatus.PASSED}
        new_failures = [test for test in self.failures if test.name in previous_passed]

        return new_failures

    def __str__(self) -> str:
        """String representation."""
        return (
            f"{self.passed} passed, {self.failed} failed, "
            f"{self.skipped} skipped ({self.duration:.1f}s)"
        )


class PytestOutputParser:
    """Parse pytest output into structured results."""

    # Patterns for parsing pytest output
    SUMMARY_PATTERN = re.compile(r'(\d+) passed, (\d+) failed, (\d+) skipped')
    SUMMARY_WITH_ERRORS = re.compile(r'(\d+) passed, (\d+) failed, (\d+) errors, (\d+) skipped')
    DURATION_PATTERN = re.compile(r'in (\d+\.?\d*)s')
    TEST_PATTERN = re.compile(r'tests/(.+?)::(\w+)\s+\[(PASS|FAIL|SKIP|ERROR)\]')

    def __init__(self):
        self.current_tests: List[TestCase] = []
        self.current_failures: List[TestCase] = []

    def parse(self, output: str) -> TestResults:
        """
        Parse pytest output.

        Args:
            output: Raw pytest output

        Returns:
            TestResults: Parsed test results
        """
        results = TestResults()

        # Parse summary line
        summary_match = self.SUMMARY_WITH_ERRORS.search(output)
        if summary_match:
            results.passed = int(summary_match.group(1))
            results.failed = int(summary_match.group(2))
            results.errors = int(summary_match.group(3))
            results.skipped = int(summary_match.group(4))
        else:
            summary_match = self.SUMMARY_PATTERN.search(output)
            if summary_match:
                results.passed = int(summary_match.group(1))
                results.failed = int(summary_match.group(2))
                results.skipped = int(summary_match.group(3))

        results.total = results.passed + results.failed + results.errors + results.skipped

        # Parse duration
        duration_match = self.DURATION_PATTERN.search(output)
        if duration_match:
            results.duration = float(duration_match.group(1))

        # Parse version info
        version_match = re.search(r'pytest-(\d+\.\d+\.\d+)', output)
        if version_match:
            results.pytest_version = version_match.group(1)

        python_match = re.search(r'python-version = (\d+\.\d+)', output)
        if python_match:
            results.python_version = python_match.group(1)

        # Parse individual test results (from verbose output)
        results.tests = self._parse_tests(output)
        results.failures = [t for t in results.tests if t.is_failure or t.is_error]

        return results

    def _parse_tests(self, output: str) -> List[TestCase]:
        """Parse individual test results from verbose output."""
        tests = []

        # Pattern for test lines: tests/integration/test_xxx.py::TestClass::test_name PASSED
        test_pattern = re.compile(r'tests/[^\s]+::\w+(?:\[\w+\])?\s+\[(PASS|FAIL|XPASS|XFAIL|SKIP|ERROR)\]')

        lines = output.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for test result line
            test_match = test_pattern.search(line)
            if test_match:
                status_str = test_match.group(1)

                # Extract test name
                name_match = re.search(r'(tests/[^\s]+)', line)
                if name_match:
                    test_name = name_match.group(1)

                    # Determine status
                    if status_str in ['PASS', 'XPASS']:
                        status = TestStatus.PASSED
                    elif status_str == 'FAIL':
                        status = TestStatus.FAILED
                        # Parse failure details
                        test_case = self._parse_failure(test_name, lines, i + 1)
                        tests.append(test_case)
                        i += 1
                        continue
                    elif status_str in ['SKIP', 'XFAIL']:
                        status = TestStatus.SKIPPED
                    else:
                        status = TestStatus.ERROR

                    if status != TestStatus.FAILED:
                        # Extract module and class
                        parts = test_name.split('::')
                        module = parts[0] if len(parts) > 0 else ""
                        class_name = parts[1] if len(parts) > 1 else ""

                        tests.append(TestCase(
                            name=test_name,
                            status=status,
                            module=module,
                            class_name=class_name
                        ))

            i += 1

        return tests

    def _parse_failure(self, test_name: str, lines: List[str], start_idx: int) -> TestCase:
        """Parse failure details from output."""
        error_type = None
        error_message = None
        traceback_lines = []

        i = start_idx
        while i < len(lines):
            line = lines[i]

            # Stop at next test or end of failures section
            if line.startswith('tests/') or line.strip().startswith('='):
                break

            # Look for error indicators
            if 'AssertionError:' in line or 'Error:' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    error_type = parts[0].strip()
                    error_message = parts[1].strip()

            # Collect traceback lines
            if line.strip().startswith('File ') or line.strip().startswith('    '):
                traceback_lines.append(line)

            i += 1

        # Extract module and class
        parts = test_name.split('::')
        module = parts[0] if len(parts) > 0 else ""
        class_name = parts[1] if len(parts) > 1 else ""

        return TestCase(
            name=test_name,
            status=TestStatus.FAILED,
            error_type=error_type,
            error_message=error_message,
            traceback='\n'.join(traceback_lines) if traceback_lines else None,
            module=module,
            class_name=class_name
        )

    def parse_file(self, file_path: str) -> TestResults:
        """
        Parse pytest output from file.

        Args:
            file_path: Path to pytest output file

        Returns:
            TestResults: Parsed test results
        """
        with open(file_path, 'r') as f:
            output = f.read()
        return self.parse(output)


def parse_pytest_output(output: str) -> TestResults:
    """
    Convenience function to parse pytest output.

    Args:
        output: Raw pytest output

    Returns:
        TestResults: Parsed test results
    """
    parser = PytestOutputParser()
    return parser.parse(output)
