# ============================================================================
# PRITHU BACKEND - LOGGING MODULE
# ============================================================================
# Centralized logging configuration with structured logging
# ============================================================================

import logging
import logging.handlers
from typing import Optional
from app.core.config import Config


class LoggerSetup:
    """Setup and manage application logging."""

    _instance = None
    _loggers: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize logging configuration."""
        self._setup_root_logger()

    @staticmethod
    def _setup_root_logger() -> None:
        """Setup root logger with file and console handlers."""
        root_logger = logging.getLogger()
        root_logger.setLevel(Config.LOG_LEVEL)

        # ====================================================================
        # CONSOLE HANDLER
        # ====================================================================

        console_handler = logging.StreamHandler()
        console_handler.setLevel(Config.LOG_LEVEL)
        console_formatter = logging.Formatter(Config.LOG_FORMAT)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # ====================================================================
        # FILE HANDLER (if configured)
        # ====================================================================

        if Config.LOG_FILE:
            try:
                file_handler = logging.handlers.RotatingFileHandler(
                    Config.LOG_FILE,
                    maxBytes=10485760,  # 10MB
                    backupCount=5
                )
                file_handler.setLevel(Config.LOG_LEVEL)
                file_formatter = logging.Formatter(Config.LOG_FORMAT)
                file_handler.setFormatter(file_formatter)
                root_logger.addHandler(file_handler)
            except Exception as e:
                root_logger.warning(f"Failed to setup file logging: {e}")

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get logger instance for a module.

        Args:
            name: Module name (__name__)

        Returns:
            logging.Logger: Configured logger instance
        """
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        return cls._loggers[name]


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get logger.

    Args:
        name: Module name

    Returns:
        logging.Logger: Logger instance
    """
    return LoggerSetup.get_logger(name)


# Initialize logging on module import
_logger_setup = LoggerSetup()
