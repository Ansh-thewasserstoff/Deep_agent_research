import logging
import sys
from typing import Optional
from datetime import datetime


class BaseLogger:

    _logger:Optional[logging.Logger] = None

    @classmethod
    def get_logger(cls, name: str = "deep_research", level: str = "INFO") -> logging.Logger:
        """returns a logger instance or create one if not provided"""
        if cls._logger is None:
            cls._logger = logging.getLogger(name)
            cls._setup_logger( level)
        return cls._logger

    @classmethod
    def _setup_logger(cls, level: str = "INFO") -> None:
        """setup the logger"""
        if cls._logger is None:
            return
        cls._logger.handlers.clear()
        cls._logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        cls._logger.addHandler(console_handler)
        cls._logger.propagate = False

    @classmethod
    def log_research_start(cls, query: str, mode: str) -> None:
        """Log research start"""
        logger = cls.get_logger()
        logger.info(f"Starting research - Query: '{query}', Mode: {mode}")

    @classmethod
    def log_research_step(cls, step: int, total: int, description: str) -> None:
        """Log research step"""
        logger = cls.get_logger()
        logger.info(f"Step {step}/{total}: {description}")

    @classmethod
    def log_research_complete(cls, total_sources: int, valid_sources: int) -> None:
        """Log research completion"""
        logger = cls.get_logger()
        logger.info(f"Research complete - Total sources: {total_sources}, Valid: {valid_sources}")

    @classmethod
    def log_error(cls, error: Exception, context: str = "") -> None:
        """Log error with context"""
        logger = cls.get_logger()
        if context:
            logger.error(f"Error in {context}: {str(error)}", exc_info=True)
        else:
            logger.error(f"Error: {str(error)}", exc_info=True)

    @classmethod
    def log_warning(cls, message: str) -> None:
        """Log warning message"""
        logger = cls.get_logger()
        logger.warning(message)

    @classmethod
    def log_debug(cls, message: str) -> None:
        """Log debug message"""
        logger = cls.get_logger()
        logger.debug(message)
