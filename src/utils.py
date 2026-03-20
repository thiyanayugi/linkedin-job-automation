"""
Utility Functions Module

Provides reusable helper functions for the LinkedIn Job Automation project,
including logging setup, retry mechanisms, rate limiting, and text processing.
"""

import logging
import time
from functools import wraps
from typing import Callable, Any
import colorlog

def setup_logger(name: str, log_file: str = None, level: str = "INFO") -> logging.Logger:
    """
    Set up a colored console logger with an optional rotating file handler.
    
    Console output uses colorlog to visually distinguish log levels:
    DEBUG=cyan, INFO=green, WARNING=yellow, ERROR/CRITICAL=red.
    File output writes the same messages in plain text without ANSI color codes.
    Parent directories for the log file are created automatically if missing.
    
    Args:
        name: Logger name, typically passed as __name__ by the calling module.
        log_file: Absolute or relative path for persisting logs to disk. If
                  omitted, only the console handler is attached.
        level: Minimum logging level string (DEBUG, INFO, WARNING, ERROR,
               CRITICAL). Defaults to 'INFO'.
    
    Returns:
        A fully configured logging.Logger instance ready for use.
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
                        # Pause before the next attempt
                        time.sleep(current_delay)
                        # Exponential backoff: multiply the delay by the backoff
                        # factor so each subsequent retry waits progressively longer
                        current_delay *= backoff
                    else:
                        logger = logging.getLogger(__name__)
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            
            raise last_exception
        
        return wrapper
    return decorator


def rate_limit(calls: int = 1, period: float = 1.0) -> Callable:
    """
    Decorator to rate limit function calls to prevent API throttling.
    
    This decorator ensures that a function is called at most 'calls' times
    within a 'period' second window, adding delays as necessary.
    
    Args:
        calls: Number of calls allowed within the period
        period: Time period in seconds for the rate limit window
    
    Returns:
        Decorated function with rate limiting applied
        
    Example:
        @rate_limit(calls=10, period=60.0)  # Max 10 calls per minute
        def api_call():
            pass
    """
    min_interval = period / calls
    last_called = [0.0]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Calculate how much time has passed since the last call
            elapsed = time.time() - last_called[0]
            # Compute remaining wait time to honor the minimum interval
            left_to_wait = min_interval - elapsed
            
            # If the minimum interval hasn't elapsed yet, sleep for the remainder
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            
            result = func(*args, **kwargs)
            # Record the call timestamp AFTER the function returns so that
            # the measured interval begins from the end of the function, not
            # the start; this avoids drift accumulation in tight call loops
            last_called[0] = time.time()
            return result
        
        return wrapper
    return decorator


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be used as a safe filesystem filename.
    
    Removes invalid characters that are not allowed in Windows/Unix filenames,
    replaces spaces with underscores, and enforces a maximum length.
    
    Args:
        filename: Original filename string to sanitize
    
    Returns:
        Sanitized filename safe for filesystem operations
        
    Note:
        - Removes: < > : " / \ | ? *
        - Replaces spaces with underscores
        - Maximum length: 200 characters
    """
    import re
    # Remove invalid characters for cross-platform compatibility
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces with underscores for better compatibility
    filename = filename.replace(' ', '_')
    # Limit length to prevent filesystem issues
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def parse_time_string(time_str: str) -> tuple:
    """
    Parse a time string in HH:MM format and validate the values.
    
    Args:
        time_str: Time string in 24-hour format (e.g., "17:00", "09:30")
    
    Returns:
        Tuple of (hour, minute) as integers
        
    Raises:
        ValueError: If the time format is invalid or values are out of range
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
    Shorten a string to at most max_length characters.
    
    If the text is already within the limit it is returned unchanged.
    When truncation is needed the suffix (default '...') is appended so
    the total length still does not exceed max_length.
    
    Args:
        text: Input string to potentially shorten.
        max_length: Maximum allowed character count including the suffix.
        suffix: String appended when truncation occurs (default: '...').
    
    Returns:
        Original text if within limit, otherwise a truncated version with
        the suffix appended.
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
        Cleaned text with normalized whitespace
    """
    import re
    # Remove extra whitespace (\\s+ matches one or more whitespace characters)
    # This includes spaces, tabs, newlines, and carriage returns
    text = re.sub(r'\s+', ' ', html_text)
    # Remove leading/trailing whitespace from the entire string
    text = text.strip()
    return text


def format_job_url(job_id: str) -> str:
    """
    Construct a canonical LinkedIn job posting URL from a numeric job ID.
    
    Useful for generating consistent, trackable links that avoid session-
    specific query parameters returned by the search results page.
    
    Args:
        job_id: LinkedIn's numeric job identifier, typically extracted
                from the job posting page or its URL.
    
    Returns:
        Absolute LinkedIn job URL in the format:
        https://www.linkedin.com/jobs/view/<job_id>
    """
    return f"https://www.linkedin.com/jobs/view/{job_id}"


def extract_job_id_from_url(url: str) -> str:
    """
    Parse the numeric job ID out of a LinkedIn job posting URL.
    
    Uses a regex to locate the first sequence of digits that follows
    '/jobs/view/' in the URL. This handles both clean canonical URLs
    and URLs with extra query parameters or trailing slashes.
    
    Args:
        url: A LinkedIn job posting URL, e.g.
             'https://www.linkedin.com/jobs/view/1234567890'
    
    Returns:
        The extracted job ID string, or an empty string if not found.
    """
    import re
    match = re.search(r'/jobs/view/(\d+)', url)
    if match:
        return match.group(1)
    return ""


def validate_config(config: dict, required_keys: list) -> bool:
    """
    Verify that all mandatory keys are present and non-empty in a config dict.
    
    Iterates over required_keys and collects any that are absent from config
    or whose value is falsy (None, empty string, 0, etc.). Raises a descriptive
    ValueError listing every missing key at once.
    
    Args:
        config: A dictionary of configuration values to validate.
        required_keys: List of key names that must exist and be truthy.
    
    Returns:
        True if all required keys are present and non-empty.
    
    Raises:
        ValueError: If one or more required keys are missing or empty,
                    with the offending key names listed in the message.
    """
    missing_keys = [key for key in required_keys if key not in config or not config[key]]
    if missing_keys:
        raise ValueError(f"Missing required configuration keys: {', '.join(missing_keys)}")
    return True
