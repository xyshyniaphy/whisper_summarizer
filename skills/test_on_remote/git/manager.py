"""
Git manager for version control operations.

Handles Git operations including committing changes, pushing to
remote, and checking repository status.
"""

import subprocess
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

try:
    from git import Repo, GitCommandError
    GITPYTHON_AVAILABLE = True
except ImportError:
    GITPYTHON_AVAILABLE = False
    Repo = None

from ..config import TestOnRemoteConfig

logger = logging.getLogger(__name__)


@dataclass
class GitStatus:
    """Git repository status."""
    branch: str
    has_changes: bool
    staged_files: List[str]
    unstaged_files: List[str]
    untracked_files: List[str]
    ahead_of_remote: bool = False
    behind_remote: bool = False

    @property
    def clean(self) -> bool:
        """Check if working directory is clean."""
        return not self.has_changes


@dataclass
class CommitResult:
    """Result of a commit operation."""
    success: bool
    commit_hash: str
    message: str
    files_changed: int
    insertions: int
    deletions: int


class GitManager:
    """
    Git operations manager.

    Handles:
    - Repository status checking
    - Change detection
    - Commit creation with conventional messages
    - Push operations
    - Branch management
    """

    def __init__(self, config: TestOnRemoteConfig):
        self.config = config
        self.project_root = config.project_root
        self._repo = None

        if GITPYTHON_AVAILABLE:
            try:
                self._repo = Repo(self.project_root)
            except Exception as e:
                logger.warning(f"GitPython unavailable: {e}")

    def _git(self, *args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
        """Run git command."""
        cmd = ["git"] + list(args)

        logger.debug(f"Running: {' '.join(cmd)}")

        return subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=capture,
            text=True,
            check=check
        )

    def get_status(self) -> GitStatus:
        """
        Get current Git status.

        Returns:
            GitStatus: Repository status
        """
        # Get branch
        result = self._git("rev-parse", "--abbrev-ref", "HEAD", check=False)
        branch = result.stdout.strip()

        # Get status
        result = self._git("status", "--porcelain", check=False)
        status_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []

        staged_files = []
        unstaged_files = []
        untracked_files = []

        for line in status_lines:
            if not line:
                continue
            status_code = line[:2]
            file_path = line[3:]
            if status_code[0] in 'MADRC':
                staged_files.append(file_path)
            if status_code[1] in 'M':
                unstaged_files.append(file_path)
            if status_code == '??':
                untracked_files.append(file_path)

        has_changes = bool(staged_files or unstaged_files or untracked_files)

        # Check ahead/behind
        result = self._git("rev-list", "--left-right", "--count", f"origin/{branch}...HEAD", check=False)

        ahead_of_remote = False
        behind_remote = False

        if result.returncode == 0:
            counts = result.stdout.strip().split('\t')
            if len(counts) == 2:
                ahead_of_remote = int(counts[0]) > 0
                behind_remote = int(counts[1]) > 0

        return GitStatus(
            branch=branch,
            has_changes=has_changes,
            staged_files=staged_files,
            unstaged_files=unstaged_files,
            untracked_files=untracked_files,
            ahead_of_remote=ahead_of_remote,
            behind_remote=behind_remote
        )

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        status = self.get_status()
        return status.has_changes

    def add_files(self, files: List[str] = None) -> bool:
        """
        Stage files for commit.

        Args:
            files: List of files to stage (None = all changes)

        Returns:
            bool: True if successful
        """
        try:
            if files is None:
                # Add all changes
                self._git("add", "-A")
            else:
                for file in files:
                    self._git("add", file)
            return True
        except Exception as e:
            logger.error(f"Failed to add files: {e}")
            return False

    def commit(
        self,
        message: str,
        coauthor: str = None
    ) -> CommitResult:
        """
        Create commit with conventional message.

        Args:
            message: Commit message (without conventional prefix)
            coauthor: Co-author string (e.g., "Claude <noreply@anthropic.com>")

        Returns:
            CommitResult: Commit result
        """
        if not self.has_uncommitted_changes():
            logger.warning("No changes to commit")
            return CommitResult(
                success=False,
                commit_hash="",
                message=message,
                files_changed=0,
                insertions=0,
                deletions=0
            )

        # Add conventional prefix
        full_message = f"{self.config.git.commit_prefix} {message}"

        # Add co-author if specified
        if coauthor:
            full_message += f"\n\nCo-Authored-By: {coauthor}"

        try:
            # Commit
            result = self._git("commit", "-m", full_message, "--allow-empty")

            # Get commit hash
            hash_result = self._git("rev-parse", "HEAD")
            commit_hash = hash_result.stdout.strip()

            # Get stats
            stats_result = self._git("show", "--stat", "--format=", commit_hash, check=False)
            stats_output = stats_result.stdout

            # Parse stats
            files_changed = 0
            insertions = 0
            deletions = 0

            for line in stats_output.split('\n'):
                if 'file changed' in line:
                    parts = line.split(',')
                    if parts:
                        main_part = parts[0]
                        if 'file changed' in main_part:
                            files_changed = int(main_part.split()[0])
                        if len(parts) > 1:
                            for part in parts[1:]:
                                if 'insertion' in part:
                                    insertions += int(part.split()[0])
                                elif 'deletion' in part:
                                    deletions += int(part.split()[0])

            logger.info(f"Committed: {commit_hash[:12]} - {full_message.split(chr(10))[0]}")

            return CommitResult(
                success=True,
                commit_hash=commit_hash,
                message=full_message,
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions
            )

        except subprocess.CalledProcessError as e:
            # Check if it was because nothing to commit
            if "nothing to commit" in e.stderr.lower():
                logger.info("Nothing to commit")
                return CommitResult(
                    success=False,
                    commit_hash="",
                    message=message,
                    files_changed=0,
                    insertions=0,
                    deletions=0
                )

            logger.error(f"Failed to commit: {e}")
            return CommitResult(
                success=False,
                commit_hash="",
                message=message,
                files_changed=0,
                insertions=0,
                deletions=0
            )

    def push(self, branch: str = None, force: bool = False) -> bool:
        """
        Push commits to remote repository.

        Args:
            branch: Branch to push (default from config)
            force: Whether to force push

        Returns:
            bool: True if successful
        """
        branch = branch or self.config.git.branch

        logger.info(f"Pushing to {branch}...")

        try:
            args = ["push", "origin", branch]
            if force:
                args.append("--force")

            self._git(*args, timeout=300)

            logger.info(f"Pushed to {branch}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to push: {e}")
            return False

    def get_changed_files(self, since: str = None) -> List[str]:
        """
        Get list of changed files.

        Args:
            since: Git revision to compare against (default: HEAD~1)

        Returns:
            List of changed file paths
        """
        if not since:
            since = "HEAD~1"

        try:
            result = self._git("diff", "--name-only", since, check=False)
            return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return []

    def get_current_branch(self) -> str:
        """Get current branch name."""
        result = self._git("rev-parse", "--abbrev-ref", "HEAD", check=False)
        return result.stdout.strip()

    def is_on_main_branch(self) -> bool:
        """Check if on main branch."""
        branch = self.get_current_branch()
        return branch in ["main", "master"]

    def create_branch(self, branch_name: str, from_branch: str = None) -> bool:
        """
        Create and checkout new branch.

        Args:
            branch_name: New branch name
            from_branch: Base branch (default: current)

        Returns:
            bool: True if successful
        """
        try:
            base = from_branch or self.get_current_branch()
            self._git("checkout", "-b", branch_name, base)
            logger.info(f"Created branch: {branch_name} from {base}")
            return True
        except Exception as e:
            logger.error(f"Failed to create branch: {e}")
            return False

    def stash_changes(self) -> bool:
        """
        Stash uncommitted changes.

        Returns:
            bool: True if successful
        """
        try:
            self._git("stash", "push", "-m", "test-on-remote: auto-stash")
            logger.info("Stashed changes")
            return True
        except Exception as e:
            logger.error(f"Failed to stash: {e}")
            return False

    def pop_stash(self) -> bool:
        """
        Pop stashed changes.

        Returns:
            bool: True if successful
        """
        try:
            self._git("stash", "pop")
            logger.info("Popped stash")
            return True
        except Exception as e:
            logger.error(f"Failed to pop stash: {e}")
            return False

    def get_latest_commit(self) -> dict:
        """
        Get information about latest commit.

        Returns:
            dict with keys: hash, author, message, date
        """
        try:
            result = self._git("log", "-1", "--pretty=%H%n%an%n%s%n%ci")
            lines = result.stdout.strip().split('\n')

            return {
                "hash": lines[0] if len(lines) > 0 else "",
                "author": lines[1] if len(lines) > 1 else "",
                "message": lines[2] if len(lines) > 2 else "",
                "date": lines[3] if len(lines) > 3 else ""
            }
        except Exception as e:
            logger.error(f"Failed to get latest commit: {e}")
            return {}

    def has_remote(self) -> bool:
        """Check if remote repository exists."""
        try:
            result = self._git("remote", "-v")
            return "origin" in result.stdout
        except:
            return False

    def pull(self, branch: str = None) -> bool:
        """
        Pull latest changes from remote.

        Args:
            branch: Branch to pull (default from config)

        Returns:
            bool: True if successful
        """
        branch = branch or self.config.git.branch

        logger.info(f"Pulling {branch}...")

        try:
            self._git("pull", "origin", branch)
            logger.info(f"Pulled {branch}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull: {e}")
            return False

    def get_diff(self, files: List[str] = None) -> str:
        """
        Get diff of changes.

        Args:
            files: Specific files to diff (None = all)

        Returns:
            str: Diff output
        """
        try:
            if files:
                return self._git("diff", "--", *files, check=False).stdout
            else:
                return self._git("diff", check=False).stdout
        except Exception as e:
            logger.error(f"Failed to get diff: {e}")
            return ""
