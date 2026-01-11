#!/usr/bin/env python3
"""
test_prd - Production Server Testing Skill

Automated remote testing and debugging workflow with intelligent fix-verify cycles.
"""

import sys
import os
import argparse
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

# Add skill directory to path for imports
SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR))

from config import load_config, ServerConfig, ConfigError
from ssh_client import SSHClient, SSHError
from test_runner import TestRunner, TestResults
from fix_cycle import FixCycle, FixPlan


@dataclass
class SkillResult:
    """Result of skill execution."""
    success: bool
    iterations: int
    final_results: Optional[TestResults]
    error: Optional[str] = None
    duration: float = 0.0

    def __str__(self) -> str:
        """String representation."""
        if self.success:
            return f"SUCCESS: {self.final_results} ({self.iterations} iterations, {self.duration:.1f}s)"
        elif self.error:
            return f"ERROR: {self.error}"
        else:
            return f"FAILED: {self.final_results} ({self.iterations} iterations, {self.duration:.1f}s)"


class TestPrdSkill:
    """
    Automated remote testing and debugging skill.

    Features:
    - SSH remote execution with id_ed25519 authentication
    - Automated test execution and result analysis
    - UltraThink-powered debugging and fix planning
    - Automated Docker build, push, and deployment
    - Git commit and push integration
    - Fix-verify loop until tests pass or max retries
    """

    def __init__(self, config_path: Path = None, verbose: bool = False):
        self.config_path = config_path
        self.verbose = verbose
        self.config: Optional[ServerConfig] = None
        self.ssh: Optional[SSHClient] = None
        self.test_runner: Optional[TestRunner] = None
        self.fix_cycle: Optional[FixCycle] = None
        self.start_time: Optional[datetime] = None

    def log_info(self, msg: str):
        """Log info message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")

    def log_success(self, msg: str):
        """Log success message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [SUCCESS] {msg}")

    def log_error(self, msg: str):
        """Log error message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [ERROR] {msg}", file=sys.stderr)

    def log_warning(self, msg: str):
        """Log warning message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [WARNING] {msg}", file=sys.stderr)

    def load_configuration(self) -> bool:
        """Load configuration from prd_server_info."""
        self.log_info("Loading Configuration")
        self.log_info("-" * 40)

        try:
            # Find config file
            if self.config_path:
                config_file = self.config_path
            else:
                # Check current directory and project root
                project_root = Path.cwd()
                config_file = project_root / "prd_server_info"
                if not config_file.exists():
                    config_file = SKILL_DIR.parent.parent.parent / "prd_server_info"

            if not config_file.exists():
                self.log_error(f"Configuration file not found: {config_file}")
                self.log_error("Create a prd_server_info file with server configuration")
                return False

            self.config = load_config(config_file)
            self.log_success(f"Configuration loaded from: {config_file}")
            self.log_info(f"Server: {self.config.server.user}@{self.config.server.host}:{self.config.server.port}")
            return True

        except ConfigError as e:
            self.log_error(f"Configuration error: {e}")
            return False
        except Exception as e:
            self.log_error(f"Failed to load configuration: {e}")
            return False

    def setup_test_environment(self) -> bool:
        """Set up local test environment."""
        self.log_info("Test Environment Setup")
        self.log_info("-" * 40)

        try:
            test_compose = self.config.testing.get("test_compose", "tests/docker-compose.test.prd.yml")
            project_root = SKILL_DIR.parent.parent.parent
            compose_file = project_root / test_compose

            if not compose_file.exists():
                self.log_error(f"Test compose file not found: {compose_file}")
                return False

            # Start test container
            self.log_info(f"Starting test container: {compose_file.name}")
            cmd = ["docker", "compose", "-f", str(compose_file), "up", "-d", "test-runner"]

            if self.verbose:
                self.log_info(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                self.log_error(f"Failed to start test container: {result.stderr}")
                return False

            self.log_success("Test container ready")
            return True

        except subprocess.TimeoutExpired:
            self.log_error("Timeout starting test container")
            return False
        except Exception as e:
            self.log_error(f"Failed to setup test environment: {e}")
            return False

    def connect_to_remote(self) -> bool:
        """Connect to remote server."""
        self.log_info("Remote Connection")
        self.log_info("-" * 40)

        try:
            self.ssh = SSHClient(self.config, verbose=self.verbose)
            self.ssh.connect()

            self.log_success(f"Connected to {self.config.server.user}@{self.config.server.host}")

            # Check container health
            health = self.ssh.check_health()
            self.log_info(f"Container health: {health}")

            return True

        except SSHError as e:
            self.log_error(f"SSH connection failed: {e}")
            return False
        except Exception as e:
            self.log_error(f"Connection error: {e}")
            return False

    def run_tests(self) -> TestResults:
        """Run tests on remote server."""
        self.log_info("Running Tests")
        self.log_info("-" * 40)

        self.test_runner = TestRunner(self.config, self.ssh, verbose=self.verbose)
        results = self.test_runner.run_tests()

        if results.all_passed:
            self.log_success(f"All tests passed: {results}")
        else:
            self.log_warning(f"Tests failed: {results.get_summary()}")

        return results

    def run_fix_cycle(self, initial_results: TestResults) -> TestResults:
        """Run fix-verify loop."""
        self.log_info("Fix Cycle")
        self.log_info("-" * 40)

        max_retries = self.config.testing.get("max_retries", 3)
        current_results = initial_results

        for iteration in range(1, max_retries + 1):
            self.log_info(f"Iteration {iteration}/{max_retries}")

            # Check if we should stop
            if current_results.all_passed:
                self.log_success("All tests passed!")
                return current_results

            # Run fix cycle
            self.fix_cycle = FixCycle(self.config, self.ssh, verbose=self.verbose)
            fix_plan = self.fix_cycle.analyze_failures(current_results, iteration)

            if fix_plan.should_stop:
                self.log_info(f"Stopping: {fix_plan.reason_for_stopping}")
                return current_results

            self.log_info(f"Fix plan: {len(fix_plan.fixes)} fixes, priority={fix_plan.priority}")

            # Apply fixes
            if not self.fix_cycle.apply_fixes(fix_plan):
                self.log_error("Failed to apply fixes")
                return current_results

            # Build and push
            if not self.fix_cycle.build_and_push():
                self.log_error("Failed to build and push")
                return current_results

            # Git commit and push
            if self.config.git.get("auto_commit", False):
                if not self.fix_cycle.commit_and_push(fix_plan):
                    self.log_error("Failed to commit and push")
                    return current_results

            # Remote deployment
            if not self.fix_cycle.deploy_to_remote():
                self.log_error("Failed to deploy to remote")
                return current_results

            # Wait for services
            self.log_info("Waiting for services to be healthy...")
            import time
            time.sleep(10)

            # Re-run tests
            self.log_info("Re-running tests...")
            new_results = self.run_tests()
            current_results = new_results

        self.log_warning(f"Max iterations ({max_retries}) reached")
        return current_results

    def cleanup(self):
        """Clean up resources."""
        self.log_info("Cleaning up...")

        if self.ssh:
            try:
                self.ssh.disconnect()
            except:
                pass

        self.log_info("Cleanup complete")

    def generate_report(self, result: SkillResult):
        """Generate execution report."""
        print()
        print("=" * 60)
        print("  Test on Remote - Execution Report")
        print("=" * 60)
        print()

        if result.success:
            print("✅ Status: SUCCESS")
            print(f"   Iterations: {result.iterations}")
            print(f"   Duration: {result.duration:.1f}s")
            print()
            print(f"   Results: {result.final_results}")
        else:
            print("❌ Status: FAILED")
            print(f"   Iterations: {result.iterations}")
            print(f"   Duration: {result.duration:.1f}s")
            print()
            if result.final_results:
                print(f"   Results: {result.final_results}")
                print()
                print(f"   Failures:")
                for test in result.final_results.failures[:10]:
                    print(f"     - {test.name}")
                if len(result.final_results.failures) > 10:
                    print(f"     ... and {len(result.final_results.failures) - 10} more")
            elif result.error:
                print(f"   Error: {result.error}")

        print()
        print("=" * 60)

    def execute(self, test_only: bool = False) -> SkillResult:
        """Main execution entry point."""
        self.start_time = datetime.now()

        try:
            # Phase 1: Load configuration
            if not self.load_configuration():
                return SkillResult(
                    success=False,
                    iterations=0,
                    final_results=None,
                    error="Configuration error",
                    duration=0.0
                )

            # Phase 2: Setup test environment
            if not self.setup_test_environment():
                return SkillResult(
                    success=False,
                    iterations=0,
                    final_results=None,
                    error="Test environment setup failed",
                    duration=(datetime.now() - self.start_time).total_seconds()
                )

            # Phase 3: Connect to remote
            if not self.connect_to_remote():
                return SkillResult(
                    success=False,
                    iterations=0,
                    final_results=None,
                    error="Remote connection failed",
                    duration=(datetime.now() - self.start_time).total_seconds()
                )

            # Phase 4: Run tests
            results = self.run_tests()

            if test_only or results.all_passed:
                return SkillResult(
                    success=results.all_passed,
                    iterations=1,
                    final_results=results,
                    duration=(datetime.now() - self.start_time).total_seconds()
                )

            # Phase 5: Fix loop if needed
            final_results = self.run_fix_cycle(results)

            return SkillResult(
                success=final_results.all_passed,
                iterations=1,
                final_results=final_results,
                duration=(datetime.now() - self.start_time).total_seconds()
            )

        except Exception as e:
            self.log_error(f"Unexpected error: {e}")
            return SkillResult(
                success=False,
                iterations=0,
                final_results=None,
                error=str(e),
                duration=(datetime.now() - self.start_time).total_seconds()
            )

        finally:
            # Phase 6: Cleanup
            self.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test on Remote - Automated Testing and Debugging"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to prd_server_info file"
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Run tests only, skip fix loop"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        help="Maximum fix-verify iterations"
    )

    args = parser.parse_args()

    # Print banner
    print()
    print("=" * 60)
    print("  Test on Remote - Automated Testing & Debugging")
    print("=" * 60)
    print()

    # Create and run skill
    skill = TestPrdSkill(
        config_path=Path(args.config) if args.config else None,
        verbose=args.verbose
    )

    result = skill.execute(test_only=args.test_only)

    # Generate report
    skill.generate_report(result)

    # Exit with appropriate code
    if result.success:
        sys.exit(0)
    elif result.error:
        sys.exit(2)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
