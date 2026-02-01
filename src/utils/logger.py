"""
Logging configuration with sensitive data filtering
"""

import logging
import sys
import re
from pathlib import Path
from typing import Optional

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


class SensitiveDataFilter(logging.Filter):
    """
    Filter to redact sensitive data from logs
    """
    
    def __init__(self):
        super().__init__()
        # Patterns to redact
        self.patterns = [
            (re.compile(r'\d{10}:\w{35}'), '[BOT_TOKEN]'),  # Bot token
            (re.compile(r'user_id["\']?\s*[:=]\s*\d+'), 'user_id=[REDACTED]'),  # User ID
            (re.compile(r'owner_id["\']?\s*[:=]\s*\d+'), 'owner_id=[REDACTED]'),  # Owner ID
            (re.compile(r'token["\']?\s*[:=]\s*["\']?\w+'), 'token=[REDACTED]'),  # Generic token
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact sensitive data"""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self.patterns:
                record.msg = pattern.sub(replacement, record.msg)
        return True


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True,
    format_str: Optional[str] = None
) -> None:
    """
    Setup logging configuration with sensitive data filtering
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None = no file logging)
        console: Enable console logging
        format_str: Custom format string
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Default format
    if format_str is None:
        format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    
    # Create handlers
    handlers = []
    
    # Console handler with colors
    if console:
        if HAS_COLORLOG:
            console_handler = colorlog.StreamHandler(sys.stdout)
            console_handler.setFormatter(colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            ))
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(
                format_str,
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
        
        console_handler.addFilter(sensitive_filter)
        handlers.append(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_file,
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            format_str,
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        file_handler.addFilter(sensitive_filter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers
    )
    
    # Set level for specific loggers
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={level}, file={log_file}, console={console}")
