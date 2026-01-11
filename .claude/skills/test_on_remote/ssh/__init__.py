"""
SSH module for remote server operations.

Provides SSH client functionality for connecting to and executing
commands on remote production servers.
"""

from .client import (
    RemoteServerClient,
    CommandResult,
    SSHConnectionError,
    SSHCommandError,
)

__all__ = [
    "RemoteServerClient",
    "CommandResult",
    "SSHConnectionError",
    "SSHCommandError",
]
