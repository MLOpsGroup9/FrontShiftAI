"""
Shared utility functions for pipeline scripts.
Reduces code duplication across modules.
"""

import time
import logging
from functools import wraps
from contextlib import contextmanager
from typing import Callable, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def retry(max_attempts: int = 3, exceptions: tuple = (Exception,)):
    """Decorator to retry function on failure."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    logger.warning(f"Retry {attempt + 1}/{max_attempts} for {func.__name__}: {e}")
            return None
        return wrapper
    return decorator


@contextmanager
def time_block(label: str, log_level: int = logging.INFO):
    """Context manager to time a code block."""
    start = time.time()
    yield
    elapsed = time.time() - start
    logger.log(log_level, f"{label}: {elapsed:.2f}s")


def ensure_dir(path: str) -> Path:
    """Ensure directory exists, return Path object."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def print_banner(text: str, width: int = 70):
    """Print a formatted banner."""
    print("\n" + "=" * width)
    print(text)
    print("=" * width + "\n")


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with default fallback."""
    return numerator / denominator if denominator > 0 else default


def chunk_list(lst: list, chunk_size: int):
    """Yield successive chunks from list."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

