"""
Centralized logging configuration for the RAG application.
Provides structured logging with rotation and multiple handlers.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure application-wide logging with console and file handlers.
    In Lambda environment, uses CloudWatch-compatible stdout logging only.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    # Check if running in Lambda
    is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None

    # Create main application logger
    logger = logging.getLogger("rag_app")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Prevent duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    if is_lambda:
        # Lambda environment: Use stdout only (CloudWatch captures this)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    else:
        # Local environment: Use console + file handlers
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Console Handler - outputs to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # File Handler - main application log with rotation
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10_000_000,  # 10 MB per file
            backupCount=5,         # Keep 5 backup files
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Capture everything in file

        # Error Handler - separate file for errors only
        error_handler = RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=5_000_000,   # 5 MB per file
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)

        # Formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Apply formatters
        console_handler.setFormatter(simple_formatter)
        file_handler.setFormatter(detailed_formatter)
        error_handler.setFormatter(detailed_formatter)

        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)

    # Suppress overly verbose loggers from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("pinecone").setLevel(logging.WARNING)

    return logger


def get_logger(name: str = "rag_app") -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (usually __name__ from the calling module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
