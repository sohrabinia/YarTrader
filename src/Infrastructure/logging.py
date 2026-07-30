import os
import logging
import sys
from typing import Dict

# Dictionary to cache configured loggers
_production_loggers: Dict[str, logging.Logger] = {}

def get_clean_logger(name: str) -> logging.Logger:
    """Configures and returns a cleanly structured logger writing to stdout."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

def get_production_logger(channel: str) -> logging.Logger:
    """
    Configures and returns a production logger dedicated to a specific channel.
    Supported channels: 'application', 'security', 'errors', 'user_activity', 'ai_operations'
    Writes to both stdout and a dedicated log file under the logs/ directory.
    """
    if channel in _production_loggers:
        return _production_loggers[channel]

    logger = logging.getLogger(f"tradeyar.{channel}")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Avoid duplicate logging up the hierarchy

    # Ensure logs/ directory exists
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)

    # Standard clean formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Stdout stream handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Dedicated file handler
    file_path = os.path.join(logs_dir, f"{channel}.log")
    try:
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        # Graceful fallback if file writing fails due to platform permissions
        pass

    _production_loggers[channel] = logger
    return logger
