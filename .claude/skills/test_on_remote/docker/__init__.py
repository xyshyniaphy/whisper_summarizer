"""
Docker module for local container operations.

Provides Docker and Docker Compose functionality for building and
managing local test containers.
"""

from .manager import (
    DockerManager,
    BuildResult,
    ContainerStatus,
)

__all__ = [
    "DockerManager",
    "BuildResult",
    "ContainerStatus",
]
