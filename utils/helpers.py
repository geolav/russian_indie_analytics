"""
utils/helpers.py
----------------
Reusable helper functions used across the project.
"""

import time
import re
from typing import Any
from functools import wraps

from utils.logger import get_logger

logger = get_logger(__name__)


def retry(times: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Decorator: retry *times* on any of *exceptions* with *delay* seconds between.
    Useful for flaky network calls.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    logger.warning(
                        "%s attempt %d/%d failed: %s",
                        func.__name__, attempt, times, exc,
                    )
                    if attempt < times:
                        time.sleep(delay * attempt)
            raise RuntimeError(f"{func.__name__} failed after {times} attempts")
        return wrapper
    return decorator


def clean_text(text: str) -> str:
    """Strip HTML tags and normalise whitespace from *text*."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_get(d: dict, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dict *d* using *keys*, returning *default* on miss."""
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)  # type: ignore[assignment]
    return d


def ms_to_min(ms: int | float) -> float:
    """Convert milliseconds to minutes, rounded to 2 dp."""
    return round(ms / 60_000, 2)


def slugify(text: str) -> str:
    """Return a filesystem-safe slug of *text*."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")
