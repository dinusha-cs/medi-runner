"""
Logging utilities for the robot server.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

try:
    from config import LOGGING
except ImportError:
    # Default logging config if config is not available
    LOGGING = {
        'LEVEL': 'INFO',
        'FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'FILE': 'robot.log',
        'MAX_FILE_SIZE': 10 * 1024 * 1024,
        'BACKUP_COUNT': 3
    }


def setup_logger(name: str, level: str = None) -> logging.Logger:
    """
    Set up a logger with console and file output.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Configured logger instance
    """
    # Use config level if not specified
    if level is None:
        level = LOGGING['LEVEL']
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(LOGGING['FORMAT'])
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    try:
        log_file = Path(LOGGING['FILE'])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LOGGING['MAX_FILE_SIZE'],
            backupCount=LOGGING['BACKUP_COUNT']
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    except Exception as e:
        # If file logging fails, continue with console only
        logger.warning(f"Could not set up file logging: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a new one.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
