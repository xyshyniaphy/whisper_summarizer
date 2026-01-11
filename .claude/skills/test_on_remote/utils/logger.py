"""
Logging utilities for test_on_remote skill.

Provides colored console output and file logging support.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Console formatter with ANSI colors."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }

    def __init__(self, fmt: str = None, datefmt: str = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            levelname = record.levelname
            record.levelname = f"{self.COLORS.get(levelname, '')}{levelname}{self.COLORS['RESET']}"
        return super().format(record)


class SkillLogger:
    """
    Logger for test_on_remote skill.

    Provides both console and file logging with color support.
    """

    def __init__(
        self,
        name: str = "test_on_remote",
        level: int = logging.INFO,
        log_file: Optional[Path] = None
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers.clear()

        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = ColoredFormatter(
            fmt='%(levelname)s: %(message)s',
            use_colors=True
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler (optional)
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def debug(self, msg: str):
        """Log debug message."""
        self.logger.debug(msg)

    def info(self, msg: str):
        """Log info message."""
        self.logger.info(msg)

    def warning(self, msg: str):
        """Log warning message."""
        self.logger.warning(msg)

    def error(self, msg: str):
        """Log error message."""
        self.logger.error(msg)

    def critical(self, msg: str):
        """Log critical message."""
        self.logger.critical(msg)

    def success(self, msg: str):
        """Log success message (info level with [SUCCESS] prefix)."""
        self.logger.info(f"[SUCCESS] {msg}")

    def set_level(self, level: int):
        """Set logging level."""
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)


# Global logger instance
_global_logger: Optional[SkillLogger] = None


def get_logger(log_file: Optional[Path] = None) -> SkillLogger:
    """
    Get or create global logger instance.

    Args:
        log_file: Optional path to log file

    Returns:
        SkillLogger: Logger instance
    """
    global _global_logger

    if _global_logger is None:
        _global_logger = SkillLogger(log_file=log_file)

    return _global_logger


def log_section(title: str, logger: SkillLogger = None):
    """Log a section header."""
    if logger is None:
        logger = get_logger()

    logger.info(f"{'=' * 60}")
    logger.info(f"  {title}")
    logger.info(f"{'=' * 60}")


def log_subsection(title: str, logger: SkillLogger = None):
    """Log a subsection header."""
    if logger is None:
        logger = get_logger()

    logger.info(f"-- {title} --")
