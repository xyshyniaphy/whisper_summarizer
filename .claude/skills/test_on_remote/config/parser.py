"""
Configuration parser for prd_server_info file.

Supports TOML format with validation.
"""

import json
import toml
from pathlib import Path
from typing import Union
from .models import TestOnRemoteConfig, ServerInfoFile


class ConfigParseError(Exception):
    """Raised when configuration parsing fails."""
    pass


class ConfigNotFoundError(Exception):
    """Raised when prd_server_info file is not found."""
    pass


class ConfigValidator:
    """Validates configuration before use."""

    @staticmethod
    def validate_ssh_key(config: TestOnRemoteConfig) -> tuple[bool, str]:
        """Validate SSH key exists and is readable."""
        key_path = config.ssh.expand_key_path()
        if not key_path.exists():
            return False, f"SSH key not found: {key_path}"
        if not key_path.is_file():
            return False, f"SSH key is not a file: {key_path}"
        if not oct(key_path.stat().st_mode)[-3:].startswith('0') and not oct(key_path.stat().st_mode)[-3:] == '600':
            return False, f"SSH key has incorrect permissions: {key_path} (should be 600)"
        return True, "OK"

    @staticmethod
    def validate_project_structure(config: TestOnRemoteConfig) -> tuple[bool, str]:
        """Validate required files exist in project."""
        issues = []

        # Check main compose file
        main_compose = config.docker.get_compose_path(config.project_root)
        if not main_compose.exists():
            issues.append(f"Main compose file not found: {main_compose}")

        # Check test compose file
        test_compose = config.testing.get_test_compose_path(config.project_root)
        if not test_compose.exists():
            issues.append(f"Test compose file not found: {test_compose}")

        # Check test directory
        test_dir = config.project_root / config.testing.test_path
        if not test_dir.exists():
            issues.append(f"Test directory not found: {test_dir}")

        if issues:
            return False, "; ".join(issues)
        return True, "OK"

    @staticmethod
    def validate_all(config: TestOnRemoteConfig) -> list[str]:
        """Validate all configuration aspects and return list of errors."""
        errors = []

        # Validate SSH key
        ssh_ok, ssh_msg = ConfigValidator.validate_ssh_key(config)
        if not ssh_ok:
            errors.append(f"SSH: {ssh_msg}")

        # Validate project structure
        struct_ok, struct_msg = ConfigValidator.validate_project_structure(config)
        if not struct_ok:
            errors.append(f"Project: {struct_msg}")

        return errors


class ConfigParser:
    """Parse and validate prd_server_info configuration file."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.config_path = self.project_root / "prd_server_info"

    def parse(self, file_path: Path = None) -> TestOnRemoteConfig:
        """
        Parse prd_server_info file and return validated configuration.

        Args:
            file_path: Optional custom path to config file

        Returns:
            TestOnRemoteConfig: Validated configuration

        Raises:
            ConfigNotFoundError: If config file doesn't exist
            ConfigParseError: If config is invalid
        """
        config_file = file_path or self.config_path

        if not config_file.exists():
            raise ConfigNotFoundError(
                f"Configuration file not found: {config_file}\n"
                f"Please create a prd_server_info file in your project root."
            )

        # Determine file format by extension
        suffix = config_file.suffix.lower()

        try:
            if suffix == '.toml':
                return self._parse_toml(config_file)
            elif suffix == '.json':
                return self._parse_json(config_file)
            else:
                # Try TOML first, then JSON
                try:
                    return self._parse_toml(config_file)
                except Exception:
                    return self._parse_json(config_file)

        except Exception as e:
            raise ConfigParseError(f"Failed to parse configuration file: {e}")

    def _parse_toml(self, file_path: Path) -> TestOnRemoteConfig:
        """Parse TOML format configuration."""
        data = toml.load(file_path)
        server_info = ServerInfoFile(**data)
        config = server_info.to_config()
        config.project_root = self.project_root
        return self._validate(config)

    def _parse_json(self, file_path: Path) -> TestOnRemoteConfig:
        """Parse JSON format configuration."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        server_info = ServerInfoFile(**data)
        config = server_info.to_config()
        config.project_root = self.project_root
        return self._validate(config)

    def _validate(self, config: TestOnRemoteConfig) -> TestOnRemoteConfig:
        """Validate configuration and return errors if any."""
        errors = ConfigValidator.validate_all(config)

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ConfigParseError(error_msg)

        return config

    def create_default_config(self) -> Path:
        """
        Create a default prd_server_info file.

        Returns:
            Path: Path to created config file
        """
        default_config = """
[server]
host = "192.3.249.169"
user = "root"

[ssh]
key_path = "~/.ssh/id_ed25519"

[containers]
server = "whisper_server_prd"
runner = "whisper_runner_prd"
frontend = "whisper_frontend_prd"

[docker]
compose_file = "docker-compose.prod.yml"
project_name = "whisper"

[testing]
test_compose = "tests/docker-compose.test.prd.yml"
test_timeout = 300
max_retries = 3

[git]
auto_commit = true
auto_push = true
commit_prefix = "[test-on-remote]"

[ultrathink]
enabled = true
"""

        self.config_path.write_text(default_config.strip())
        return self.config_path


def load_config(project_root: Path = None, config_path: Path = None) -> TestOnRemoteConfig:
    """
    Convenience function to load and validate configuration.

    Args:
        project_root: Project root directory (defaults to cwd)
        config_path: Optional custom config file path

    Returns:
        TestOnRemoteConfig: Validated configuration

    Raises:
        ConfigNotFoundError: If config file doesn't exist
        ConfigParseError: If config is invalid
    """
    parser = ConfigParser(project_root)
    return parser.parse(config_path)
