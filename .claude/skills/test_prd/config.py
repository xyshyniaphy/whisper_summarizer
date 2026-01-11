"""
Configuration parsing for test_prd skill.

Reads and validates server configuration from prd_server_info file (TOML format).
"""

import toml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class ConfigError(Exception):
    """Configuration error."""
    pass


@dataclass
class ServerConfig:
    """Server connection configuration."""
    host: str
    user: str = "root"
    port: int = 22

@dataclass
class SSHConfig:
    """SSH configuration."""
    key_path: str = "~/.ssh/id_ed25519"
    known_hosts_path: str = "~/.ssh/known_hosts"
    connect_timeout: int = 30
    command_timeout: int = 300

    def expand_key_path(self) -> Path:
        """Expand ~ and return absolute path."""
        return Path(self.key_path).expanduser()

@dataclass
class ContainersConfig:
    """Container names configuration."""
    server: str = "whisper_server_prd"
    runner: str = "whisper_runner_prd"
    frontend: str = "whisper_frontend_prd"

    def get_all(self) -> list:
        """Get all container names."""
        return [self.server, self.runner, self.frontend]

@dataclass
class DockerConfig:
    """Docker configuration."""
    compose_file: str = "docker-compose.prod.yml"
    project_name: str = "whisper"
    image_prefix: str = "whisper-"
    registry: Optional[str] = None

@dataclass
class TestingConfig:
    """Testing configuration."""
    test_compose: str = "tests/docker-compose.test.prd.yml"
    test_timeout: int = 300
    max_retries: int = 3
    test_path: str = "tests/integration"
    pytest_args: str = "-v --tb=short"

@dataclass
class GitConfig:
    """Git configuration."""
    auto_commit: bool = True
    auto_push: bool = True
    commit_prefix: str = "[test-on-remote]"
    branch: str = "main"
    coauthor: str = "Claude <noreply@anthropic.com>"

@dataclass
class UltraThinkConfig:
    """UltraThink configuration."""
    enabled: bool = True
    max_thoughts: int = 10
    timeout: int = 60


@dataclass
class ServerConfigFull:
    """Complete server configuration."""
    server: ServerConfig
    ssh: SSHConfig = field(default_factory=SSHConfig)
    containers: ContainersConfig = field(default_factory=ContainersConfig)
    docker: DockerConfig = field(default_factory=DockerConfig)
    testing: Dict[str, Any] = field(default_factory=lambda: {
        "test_compose": "tests/docker-compose.test.prd.yml",
        "test_timeout": 300,
        "max_retries": 3,
        "test_path": "tests/integration",
        "pytest_args": "-v --tb=short"
    })
    git: Dict[str, Any] = field(default_factory=lambda: {
        "auto_commit": True,
        "auto_push": True,
        "commit_prefix": "[test-on-remote]",
        "branch": "main",
        "coauthor": "Claude <noreply@anthropic.com>"
    })
    ultrathink: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "max_thoughts": 10,
        "timeout": 60
    })


def load_config(config_path: Path) -> ServerConfigFull:
    """
    Load configuration from TOML file.

    Args:
        config_path: Path to prd_server_info file

    Returns:
        ServerConfigFull: Parsed configuration

    Raises:
        ConfigError: If configuration is invalid or missing required fields
    """
    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        data = toml.load(config_path)
    except Exception as e:
        raise ConfigError(f"Failed to parse TOML: {e}")

    # Validate required fields
    if "server" not in data:
        raise ConfigError("Missing required section: [server]")

    server_data = data["server"]
    if "host" not in server_data:
        raise ConfigError("Missing required field: server.host")

    # Parse server config
    server = ServerConfig(
        host=server_data.get("host"),
        user=server_data.get("user", "root"),
        port=server_data.get("port", 22)
    )

    # Parse SSH config
    ssh_data = data.get("ssh", {})
    ssh = SSHConfig(
        key_path=ssh_data.get("key_path", "~/.ssh/id_ed25519"),
        known_hosts_path=ssh_data.get("known_hosts_path", "~/.ssh/known_hosts"),
        connect_timeout=ssh_data.get("connect_timeout", 30),
        command_timeout=ssh_data.get("command_timeout", 300)
    )

    # Parse containers config
    containers_data = data.get("containers", {})
    containers = ContainersConfig(
        server=containers_data.get("server", "whisper_server_prd"),
        runner=containers_data.get("runner", "whisper_runner_prd"),
        frontend=containers_data.get("frontend", "whisper_frontend_prd")
    )

    # Parse docker config
    docker_data = data.get("docker", {})
    docker = DockerConfig(
        compose_file=docker_data.get("compose_file", "docker-compose.prod.yml"),
        project_name=docker_data.get("project_name", "whisper"),
        image_prefix=docker_data.get("image_prefix", "whisper-"),
        registry=docker_data.get("registry")
    )

    # Parse testing config
    testing_data = data.get("testing", {})
    testing = {
        "test_compose": testing_data.get("test_compose", "tests/docker-compose.test.prd.yml"),
        "test_timeout": testing_data.get("test_timeout", 300),
        "max_retries": testing_data.get("max_retries", 3),
        "test_path": testing_data.get("test_path", "tests/integration"),
        "pytest_args": testing_data.get("pytest_args", "-v --tb=short")
    }

    # Parse git config
    git_data = data.get("git", {})
    git = {
        "auto_commit": git_data.get("auto_commit", True),
        "auto_push": git_data.get("auto_push", True),
        "commit_prefix": git_data.get("commit_prefix", "[test-on-remote]"),
        "branch": git_data.get("branch", "main"),
        "coauthor": git_data.get("coauthor", "Claude <noreply@anthropic.com>")
    }

    # Parse ultrathink config
    ultrathink_data = data.get("ultrathink", {})
    ultrathink = {
        "enabled": ultrathink_data.get("enabled", True),
        "max_thoughts": ultrathink_data.get("max_thoughts", 10),
        "timeout": ultrathink_data.get("timeout", 60)
    }

    return ServerConfigFull(
        server=server,
        ssh=ssh,
        containers=containers,
        docker=docker,
        testing=testing,
        git=git,
        ultrathink=ultrathink
    )


def create_default_config(path: Path) -> None:
    """Create a default configuration file."""
    default_content = """# Production Server Configuration for test_prd skill

[server]
# Server IP address or hostname
host = "192.3.249.169"
# SSH username
user = "root"
# SSH port (default: 22)
port = 22

[ssh]
# Path to SSH private key (Ed25519 recommended)
key_path = "~/.ssh/id_ed25519"
# Path to known_hosts file
known_hosts_path = "~/.ssh/known_hosts"
# Connection timeout in seconds
connect_timeout = 30
# Command execution timeout in seconds
command_timeout = 300

[containers]
# Container names on remote server
server = "whisper_server_prd"
runner = "whisper_runner_prd"
frontend = "whisper_frontend_prd"

[docker]
# Main Docker Compose file
compose_file = "docker-compose.prod.yml"
# Docker project name
project_name = "whisper"
# Image name prefix
image_prefix = "whisper-"

[testing]
# Test Docker Compose file (relative to project root)
test_compose = "tests/docker-compose.test.prd.yml"
# Test timeout in seconds
test_timeout = 300
# Maximum fix-verify iterations
max_retries = 3
# Path to tests (relative to project root)
test_path = "tests/integration"
# Default pytest arguments
pytest_args = "-v --tb=short"

[git]
# Automatically commit changes
auto_commit = true
# Automatically push commits
auto_push = true
# Prefix for auto-generated commits
commit_prefix = "[test-on-remote]"
# Branch to commit and push to
branch = "main"
# Co-author for commits
coauthor = "Claude <noreply@anthropic.com>"

[ultrathink]
# Enable UltraThink for intelligent analysis
enabled = true
# Maximum thoughts per analysis
max_thoughts = 10
# Timeout per thought (seconds)
timeout = 60
"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(default_content)
