"""
Configuration data models for test_on_remote skill.

Uses Pydantic for validation and type safety.
"""

from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class ServerConfig(BaseModel):
    """Remote server connection configuration."""
    host: str = Field(..., description="Server IP address or hostname")
    user: str = Field(default="root", description="SSH username")
    port: int = Field(default=22, description="SSH port")

    @validator('host')
    def validate_host(cls, v):
        if not v:
            raise ValueError("Server host cannot be empty")
        return v


class SSHConfig(BaseModel):
    """SSH authentication configuration."""
    key_path: str = Field(default="~/.ssh/id_ed25519", description="Path to SSH private key")
    known_hosts_path: str = Field(default="~/.ssh/known_hosts", description="Path to known_hosts file")
    connect_timeout: int = Field(default=30, description="Connection timeout in seconds")
    command_timeout: int = Field(default=300, description="Command execution timeout")

    def expand_key_path(self) -> Path:
        """Expand ~ and return absolute path."""
        return Path(self.key_path).expanduser()

    def expand_known_hosts_path(self) -> Path:
        """Expand ~ and return absolute path."""
        return Path(self.known_hosts_path).expanduser()


class ContainersConfig(BaseModel):
    """Container names on remote server."""
    server: str = Field(default="whisper_server_prd")
    runner: str = Field(default="whisper_runner_prd")
    frontend: str = Field(default="whisper_frontend_prd")
    postgres: Optional[str] = Field(default=None)

    def get_all(self) -> List[str]:
        """Get all container names."""
        containers = [self.server, self.runner, self.frontend]
        if self.postgres:
            containers.append(self.postgres)
        return [c for c in containers if c]


class DockerConfig(BaseModel):
    """Docker configuration."""
    compose_file: str = Field(default="docker-compose.prod.yml")
    project_name: str = Field(default="whisper")
    registry: Optional[str] = Field(default=None, description="Docker registry for pushing images")
    image_prefix: str = Field(default="", description="Prefix for image names")

    def get_compose_path(self, project_root: Path) -> Path:
        """Get absolute path to compose file."""
        return project_root / self.compose_file


class TestingConfig(BaseModel):
    """Testing configuration."""
    test_compose: str = Field(default="tests/docker-compose.test.prd.yml")
    test_timeout: int = Field(default=300, description="Test timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum fix-verify iterations")
    test_path: str = Field(default="tests/integration", description="Path to tests")
    pytest_args: str = Field(default="-v --tb=short", description="Default pytest arguments")

    def get_test_compose_path(self, project_root: Path) -> Path:
        """Get absolute path to test compose file."""
        return project_root / self.test_compose


class GitConfig(BaseModel):
    """Git configuration."""
    auto_commit: bool = Field(default=True, description="Automatically commit changes")
    auto_push: bool = Field(default=True, description="Automatically push commits")
    commit_prefix: str = Field(default="[test-on-remote]", description="Prefix for auto-generated commits")
    branch: str = Field(default="main", description="Branch to commit and push to")
    coauthor: str = Field(default="Claude <noreply@anthropic.com>", description="Co-author for commits")


class UltraThinkConfig(BaseModel):
    """UltraThink integration configuration."""
    enabled: bool = Field(default=True, description="Enable UltraThink for analysis")
    max_thoughts: int = Field(default=10, description="Maximum thoughts per analysis")
    timeout: int = Field(default=60, description="UltraThink timeout per thought")


class TestOnRemoteConfig(BaseModel):
    """Complete configuration for test_on_remote skill."""

    server: ServerConfig
    ssh: SSHConfig = Field(default_factory=SSHConfig)
    containers: ContainersConfig = Field(default_factory=ContainersConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    testing: TestingConfig = Field(default_factory=TestingConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    ultrathink: UltraThinkConfig = Field(default_factory=UltraThinkConfig)

    # Project root (derived)
    project_root: Path = Field(default_factory=lambda: Path.cwd())

    class Config:
        """Pydantic config."""
        validate_assignment = True

    def get_ssh_connection_string(self) -> str:
        """Get SSH connection string."""
        return f"{self.server.user}@{self.server.host}"

    def validate_ssh_key_exists(self) -> bool:
        """Check if SSH key exists."""
        return self.ssh.expand_key_path().exists()

    def validate_compose_files_exist(self) -> bool:
        """Check if compose files exist."""
        main_compose = self.docker.get_compose_path(self.project_root)
        test_compose = self.testing.get_test_compose_path(self.project_root)
        return main_compose.exists() and test_compose.exists()

    def get_project_name(self) -> str:
        """Get Docker project name."""
        return self.docker.project_name


class ServerInfoFile(BaseModel):
    """Raw server info file format (for parsing)."""

    server: dict
    ssh: Optional[dict] = None
    containers: Optional[dict] = None
    docker: Optional[dict] = None
    testing: Optional[dict] = None
    git: Optional[dict] = None
    ultrathink: Optional[dict] = None

    def to_config(self) -> TestOnRemoteConfig:
        """Convert to TestOnRemoteConfig."""
        return TestOnRemoteConfig(
            server=ServerConfig(**self.server),
            ssh=SSHConfig(**(self.ssh or {})),
            containers=ContainersConfig(**(self.containers or {})),
            docker=DockerConfig(**(self.docker or {})),
            testing=TestingConfig(**(self.testing or {})),
            git=GitConfig(**(self.git or {})),
            ultrathink=UltraThinkConfig(**(self.ultrathink or {}))
        )
