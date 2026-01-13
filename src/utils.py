"""
Utility functions for the LinkedIn Job Automation project.
"""

import logging
import time
from functools import wraps
from typing import Callable, Any
import colorlog

def setup_logger(name: str, log_file: str = None, level: str = "INFO") -> logging.Logger:
    """
    Set up a colored logger with file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (optional)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler with colors
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    
    console_format = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (if log_file specified)
    if log_file:
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0) -> Callable:
    """
    Decorator to retry a function on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (must be >= 0)
        delay: Initial delay between retries in seconds (must be > 0)
        backoff: Multiplier for delay after each retry (must be >= 1.0)
    
    Returns:
        Decorated function with retry logic applied
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger = logging.getLogger(__name__)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger = logging.getLogger(__name__)
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            
            raise last_exception
        
        return wrapper
    return decorator


def rate_limit(calls: int = 1, period: float = 1.0):
    """
    Decorator to rate limit function calls.
    
    Args:
        calls: Number of calls allowed
        period: Time period in seconds
    
    Returns:
        Decorated function
    """
    min_interval = period / calls
    last_called = [0.0]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        
        return wrapper
    return decorator


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def parse_time_string(time_str: str) -> tuple:
    """
    Parse a time string in HH:MM format.
    
    Args:
        time_str: Time string (e.g., "17:00")
    
    Returns:
        Tuple of (hour, minute)
    """
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time range")
        return hour, minute
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM (e.g., 17:00)")


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_html_text(html_text: str) -> str:
    """
    Clean HTML text by removing extra whitespace and newlines.
    
    Args:
        html_text: HTML text to clean
    
    Returns:
        Cleaned text
    """
    import re
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', html_text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def format_job_url(job_id: str) -> str:
    """
    Format a LinkedIn job URL from a job ID.
    
    Args:
        job_id: LinkedIn job ID
    
    Returns:
        Full job URL
    """
    return f"https://www.linkedin.com/jobs/view/{job_id}"


def extract_job_id_from_url(url: str) -> str:
    """
    Extract job ID from a LinkedIn job URL.
    
    Args:
        url: LinkedIn job URL
    
    Returns:
        Job ID
    """
    import re
    match = re.search(r'/jobs/view/(\d+)', url)
    if match:
        return match.group(1)
    return ""


def validate_config(config: dict, required_keys: list) -> bool:
    """
    Validate that a configuration dictionary has all required keys.
    
    Args:
        config: Configuration dictionary
        required_keys: List of required keys
    
    Returns:
        True if valid, raises ValueError otherwise
    """
    missing_keys = [key for key in required_keys if key not in config or not config[key]]
    if missing_keys:
        raise ValueError(f"Missing required configuration keys: {', '.join(missing_keys)}")
    return True
