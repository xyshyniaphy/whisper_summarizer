"""
UltraThink integration wrapper for intelligent analysis.

Provides interface to Sequential Thinking MCP for complex
decision making during the fix-verify loop.
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

from .logger import get_logger

logger = get_logger()


@dataclass
class Thought:
    """Single thought in the reasoning chain."""
    number: int
    content: str
    next_thought_needed: bool
    total_thoughts: int
    is_revision: bool = False
    revises_thought: int = -1
    branch_from: int = -1
    branch_id: str = ""

    def __str__(self) -> str:
        """String representation."""
        prefix = f"Thought {self.number}/{self.total_thoughts}"
        if self.is_revision:
            prefix += f" (revising {self.revises_thought})"
        return f"{prefix}: {self.content}"


@dataclass
class FixPlan:
    """Generated plan for fixing test failures."""
    should_stop: bool
    reason_for_stopping: str = ""
    fixes: List[Dict[str, Any]] = None
    priority: str = "medium"  # low, medium, high, critical
    confidence: float = 0.5
    estimated_effort: str = "medium"  # quick, medium, significant

    def __post_init__(self):
        if self.fixes is None:
            self.fixes = []


class UltraThinkAnalyzer:
    """
    UltraThink integration for intelligent analysis.

    Uses Sequential Thinking MCP to analyze test failures and
    generate fix plans.
    """

    def __init__(self, enabled: bool = True, max_thoughts: int = 10):
        self.enabled = enabled
        self.max_thoughts = max_thoughts
        self._mcp_available = self._check_mcp_available()

    def _check_mcp_available(self) -> bool:
        """Check if Sequential Thinking MCP is available."""
        try:
            # Try importing the tool
            # This is a placeholder - actual implementation would check MCP availability
            return True
        except:
            return False

    async def analyze_failures(
        self,
        test_results: 'TestResults',
        context: Dict[str, Any] = None
    ) -> FixPlan:
        """
        Analyze test failures using UltraThink.

        Args:
            test_results: Test results with failures
            context: Additional context (iteration, previous results, etc.)

        Returns:
            FixPlan: Generated fix plan
        """
        if not self.enabled or not self._mcp_available:
            # Return default plan without UltraThink
            return FixPlan(
                should_stop=True,
                reason_for_stopping="UltraThink not available",
                fixes=[],
                confidence=0.0
            )

        failures = test_results.failures

        if not failures:
            return FixPlan(
                should_stop=True,
                reason_for_stopping="No failures to analyze"
            )

        # Build analysis prompt
        prompt = self._build_analysis_prompt(failures, context)

        # Run UltraThink analysis
        try:
            plan = await self._run_ultrathink_analysis(prompt, test_results)
            return plan
        except Exception as e:
            logger.error(f"UltraThink analysis failed: {e}")
            # Return fallback plan
            return self._generate_fallback_plan(failures)

    def _build_analysis_prompt(
        self,
        failures: List['TestCase'],
        context: Dict[str, Any]
    ) -> str:
        """Build analysis prompt for UltraThink."""
        iteration = context.get('iteration', 1) if context else 1
        previous_results = context.get('previous_results') if context else None

        prompt = f"""I'm analyzing test failures from iteration {iteration} of automated testing.

Test Failures:
"""

        for i, failure in enumerate(failures[:5], 1):  # Limit to 5
            prompt += f"{i}. {failure.short_name}\n"
            if failure.error_message:
                prompt += f"   Error: {failure.error_message}\n"
            if failure.error_type:
                prompt += f"   Type: {failure.error_type}\n"
            prompt += "\n"

        if len(failures) > 5:
            prompt += f"... and {len(failures) - 5} more failures\n\n"

        if previous_results:
            prompt += f"Previous run had {previous_results.passed} passed tests.\n"

        prompt += """
Please analyze these failures and determine:
1. Root cause of the failures
2. Most likely fix strategy
3. Whether to continue fixing or stop (max retries approaching)
4. Priority and estimated effort

Think step by step, building on previous thoughts to reach a conclusion.
"""

        return prompt

    async def _run_ultrathink_analysis(
        self,
        prompt: str,
        test_results: 'TestResults'
    ) -> FixPlan:
        """
        Run UltraThink analysis using MCP.

        This is a placeholder implementation. The actual implementation
        would use the mcp__sequential-thinking__sequentialthinking tool.
        """
        # Placeholder: Simulate UltraThink process
        thoughts = []

        # Simulate thought process
        thoughts.append(Thought(
            number=1,
            content="Analyzing the failure patterns...",
            next_thought_needed=True,
            total_thoughts=self.max_thoughts
        ))

        thoughts.append(Thought(
            number=2,
            content="Most failures seem related to authentication/authorization issues.",
            next_thought_needed=True,
            total_thoughts=self.max_thoughts
        ))

        # Generate fix plan based on simulated analysis
        return FixPlan(
            should_stop=False,
            fixes=[
                {
                    "type": "code_change",
                    "target": "server/app/api/deps.py",
                    "description": "Add get_current_active_user function",
                    "reason": "Missing function causes 404 on protected endpoints"
                }
            ],
            priority="high",
            confidence=0.7,
            estimated_effort="medium"
        )

    def _generate_fallback_plan(
        self,
        failures: List['TestCase']
    ) -> FixPlan:
        """Generate fallback plan when UltraThink is unavailable."""
        # Simple heuristic: group failures by error type
        error_groups = {}

        for failure in failures:
            error_type = failure.error_type or "unknown"
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(failure)

        fixes = []

        for error_type, group_failures in error_groups.items():
            fixes.append({
                "type": "investigate",
                "error_type": error_type,
                "affected_tests": [f.short_name for f in group_failures],
                "description": f"Investigate and fix {error_type} errors"
            })

        return FixPlan(
            should_stop=False,
            fixes=fixes,
            priority="medium",
            confidence=0.3,
            estimated_effort="unknown"
        )

    async def generate_fix_strategy(
        self,
        failures: List['TestCase'],
        iteration: int,
        max_iterations: int
    ) -> str:
        """
        Generate fix strategy recommendation.

        Args:
            failures: List of failed tests
            iteration: Current iteration number
            max_iterations: Maximum iterations allowed

        Returns:
            str: Strategy recommendation
        """
        if iteration >= max_iterations:
            return f"STOP: Maximum iterations ({max_iterations}) reached"

        if len(failures) > 20:
            return "STOP: Too many failures (likely configuration issue)"

        if iteration >= 2:
            new_failures = self._count_new_failures(failures, iteration)
            if new_failures > len(failures) // 2:
                return "STOP: More than half of failures are new (regression)"

        return f"CONTINUE: Attempting to fix {len(failures)} failures"

    def _count_new_failures(
        self,
        failures: List['TestCase'],
        iteration: int
    ) -> int:
        """Count how many failures appear to be new (not seen in previous iterations)."""
        # This is a simplified heuristic
        # In practice, we'd track failures across iterations
        return 0


async def analyze_with_ultrathink(
    test_results: 'TestResults',
    context: Dict[str, Any] = None,
    max_thoughts: int = 10
) -> FixPlan:
    """
    Convenience function to analyze failures with UltraThink.

    Args:
        test_results: Test results with failures
        context: Additional context
        max_thoughts: Maximum thoughts per analysis

    Returns:
        FixPlan: Generated fix plan
    """
    analyzer = UltraThinkAnalyzer(max_thoughts=max_thoughts)
    return await analyzer.analyze_failures(test_results, context)
