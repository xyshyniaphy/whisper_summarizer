"""
Fix cycle for automated debugging.

Handles intelligent failure analysis and fix application.
"""

import time
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class FixPlan:
    """Generated fix plan."""
    should_stop: bool
    reason_for_stopping: str = ""
    fixes: List[Dict[str, Any]] = field(default_factory=list)
    priority: str = "medium"
    confidence: float = 0.5
    estimated_effort: str = "medium"


class FixCycle:
    """
    Automated fix cycle for test failures.

    Analyzes failures and applies fixes using UltraThink integration.
    """

    def __init__(self, config, ssh_client, verbose: bool = False):
        """
        Initialize fix cycle.

        Args:
            config: ServerConfigFull configuration
            ssh_client: SSHClient instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.ssh = ssh_client
        self.verbose = verbose
        self.project_root = Path.cwd()

    def log_info(self, msg: str):
        """Log info message."""
        if self.verbose:
            print(f"[FIX] {msg}")

    def log_warning(self, msg: str):
        """Log warning message."""
        print(f"[FIX] [WARNING] {msg}")

    def analyze_failures(self, test_results, iteration: int) -> FixPlan:
        """
        Analyze test failures and generate fix plan.

        Args:
            test_results: TestResults with failures
            iteration: Current iteration number

        Returns:
            FixPlan: Generated fix plan
        """
        self.log_info("Analyzing failures...")

        if not test_results.failures:
            return FixPlan(
                should_stop=True,
                reason_for_stopping="No failures to analyze"
            )

        # Check if UltraThink is enabled
        if not self.config.ultrathink.get("enabled", True):
            self.log_warning("UltraThink disabled - stopping")
            return FixPlan(
                should_stop=True,
                reason_for_stopping="UltraThink disabled"
            )

        # Build analysis prompt
        failures_summary = "\n".join([
            f"- {test.name}: {test.status}" + (f" - {test.error_message}" if test.error_message else "")
            for test in test_results.failures[:5]
        ])

        prompt = f"""I'm analyzing test failures from iteration {iteration} of automated testing.

Test Failures:
{failures_summary}

Please analyze these failures and determine:
1. Root cause of the failures
2. Most likely fix strategy
3. Whether to continue fixing or stop
4. Priority and estimated effort

Respond with a JSON object:
{{
    "should_stop": false,
    "reason": "",
    "fixes": [
        {{
            "type": "code_change|config_change|restart_service",
            "target": "file_path_or_service_name",
            "description": "what to fix",
            "priority": "high|medium|low"
        }}
    ],
    "confidence": 0.8,
    "estimated_effort": "low|medium|high"
}}
"""

        # For now, create a simple fix plan based on failure patterns
        # In production, this would use UltraThink MCP
        fixes = []

        for failure in test_results.failures[:3]:
            if "404" in failure.error_message or "not found" in failure.error_message.lower():
                fixes.append({
                    "type": "code_change",
                    "target": "server/api/routes.py",
                    "description": f"Add missing route for {failure.name}",
                    "priority": "high"
                })
            elif "timeout" in failure.error_message.lower():
                fixes.append({
                    "type": "config_change",
                    "target": "timeout settings",
                    "description": "Increase timeout for slow operations",
                    "priority": "medium"
                })
            elif "permission" in failure.error_message.lower() or "auth" in failure.error_message.lower():
                fixes.append({
                    "type": "config_change",
                    "target": "authentication settings",
                    "description": "Fix authentication/permissions",
                    "priority": "high"
                })
            else:
                fixes.append({
                    "type": "code_change",
                    "target": "unknown",
                    "description": f"Fix {failure.name}",
                    "priority": "medium"
                })

        # Check if we should continue
        max_retries = self.config.testing.get("max_retries", 3)
        should_stop = iteration >= max_retries

        return FixPlan(
            should_stop=should_stop,
            reason_for_stopping=f"Max iterations ({max_retries}) reached" if should_stop else "",
            fixes=fixes[:5],  # Limit fixes
            priority="high" if any(f.get("priority") == "high" for f in fixes) else "medium"
        )

    def apply_fixes(self, fix_plan: FixPlan) -> bool:
        """
        Apply fixes from the fix plan.

        Args:
            fix_plan: Generated fix plan

        Returns:
            bool: True if successful
        """
        self.log_info(f"Applying {len(fix_plan.fixes)} fixes...")

        for i, fix in enumerate(fix_plan.fixes, 1):
            self.log_info(f"Fix {i}/{len(fix_plan.fixes)}: {fix.get('description', 'Unknown')}")

            fix_type = fix.get('type')

            if fix_type == 'code_change':
                # In production, this would apply actual code changes
                # For now, just log it
                self.log_info(f"  Would modify: {fix.get('target')}")
            elif fix_type == 'config_change':
                self.log_info(f"  Would change: {fix.get('target')}")
            elif fix_type == 'restart_service':
                self.log_info(f"  Would restart: {fix.get('target')}")

        self.log_info("Fixes applied (simulated)")
        return True

    def build_and_push(self) -> bool:
        """
        Build changed Docker images and push to registry.

        Returns:
            bool: True if successful
        """
        self.log_info("Building and Pushing Images")

        # Get changed files
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                changed_files = result.stdout.strip().split('\n')
                self.log_info(f"Changed files: {len([f for f in changed_files if f])}")

        except Exception as e:
            self.log_warning(f"Could not detect changes: {e}")

        # Build affected services
        services_to_build = []
        compose_file = self.config.docker.get("compose_file", "docker-compose.prod.yml")

        self.log_info("Building services...")
        self.log_info("(Build simulated - would rebuild changed services)")

        # Push if registry configured
        if self.config.docker.get("registry"):
            self.log_info("Pushing to registry...")
            self.log_info("(Push simulated)")

        return True

    def commit_and_push(self, fix_plan: FixPlan) -> bool:
        """
        Commit changes and push to Git.

        Args:
            fix_plan: Fix plan for commit message

        Returns:
            bool: True if successful
        """
        self.log_info("Git Commit and Push")

        # Stage changes
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.project_root,
                capture_output=True,
                timeout=30
            )
        except Exception as e:
            self.log_warning(f"Failed to stage changes: {e}")
            return False

        # Commit
        commit_msg = f"{self.config.git.get('commit_prefix', '[test-prd]')} Fix test failures ({len(fix_plan.fixes)} fixes)"
        coauthor = self.config.git.get('coauthor')

        if coauthor:
            commit_msg += f"\n\nCo-Authored-By: {coauthor}"

        try:
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg, "--allow-empty"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Get commit hash
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                commit_hash = hash_result.stdout.strip()[:12]
                self.log_info(f"Committed: {commit_hash}")
            else:
                self.log_warning(f"Nothing to commit or commit failed")

        except Exception as e:
            self.log_warning(f"Failed to commit: {e}")
            return False

        # Push if configured
        if self.config.git.get("auto_push", True):
            try:
                branch = self.config.git.get("branch", "main")
                subprocess.run(
                    ["git", "push", "origin", branch],
                    cwd=self.project_root,
                    capture_output=True,
                    timeout=120
                )
                self.log_info("Pushed to remote")
            except Exception as e:
                self.log_warning(f"Failed to push: {e}")
                return False

        return True

    def deploy_to_remote(self) -> bool:
        """
        Trigger remote deployment (pull and restart).

        Returns:
            bool: True if successful
        """
        self.log_info("Remote Deployment")

        # Pull images on remote
        image_prefix = self.config.docker.get("image_prefix", "whisper-")
        registry = self.config.docker.get("registry")

        for service in ["server", "runner", "frontend"]:
            image = f"{image_prefix}{service}"
            if registry:
                image = f"{registry}/{image}"

            self.log_info(f"Pulling on remote: {image}")

            try:
                self.ssh.pull_image(image, timeout=300)
            except Exception as e:
                self.log_warning(f"Failed to pull {image}: {e}")

        # Restart containers
        for container in self.config.containers.get_all():
            self.log_info(f"Restarting: {container}")

            try:
                result = self.ssh.restart_container(container)

                if result.success:
                    self.log_info(f"{container} is healthy")
                else:
                    self.log_warning(f"{container} did not become healthy")

            except Exception as e:
                self.log_warning(f"Failed to restart {container}: {e}")

        return True
