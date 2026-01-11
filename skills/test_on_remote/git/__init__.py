"""
Git module for version control operations.

Provides Git functionality for committing changes, pushing to
remote, and checking repository status.
"""

from .manager import (
    GitManager,
    GitStatus,
    CommitResult,
)

__all__ = [
    "GitManager",
    "GitStatus",
    "CommitResult",
]
