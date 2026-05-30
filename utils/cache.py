"""
utils/cache.py
--------------
Simple file-based JSON cache with TTL.
Prevents redundant API calls during development and rate-limit safety.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Any

from config.settings import CACHE_DIR, CACHE_TTL_HOURS
from utils.logger import get_logger

logger = get_logger(__name__)


def _cache_path(key: str) -> Path:
    """Convert an arbitrary string key into a safe cache file path."""
    hashed = hashlib.md5(key.encode()).hexdigest()
    return CACHE_DIR / f"{hashed}.json"


def cache_get(key: str) -> Any | None:
    """
    Retrieve a cached value.

    Returns the value if the cache entry exists and hasn't expired,
    otherwise returns None.
    """
    path = _cache_path(key)
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as f:
            entry = json.load(f)

        age_hours = (time.time() - entry["timestamp"]) / 3600
        if age_hours > CACHE_TTL_HOURS:
            path.unlink(missing_ok=True)
            logger.debug("Cache expired for key: %s", key[:60])
            return None

        logger.debug("Cache hit for key: %s", key[:60])
        return entry["value"]

    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Corrupt cache entry, ignoring: %s", exc)
        path.unlink(missing_ok=True)
        return None


def cache_set(key: str, value: Any) -> None:
    """Persist *value* to the cache under *key*."""
    path = _cache_path(key)
    entry = {"timestamp": time.time(), "value": value}
    with path.open("w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)
    logger.debug("Cached key: %s", key[:60])


def cache_clear() -> None:
    """Remove all cache files."""
    removed = 0
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
        removed += 1
    logger.info("Cleared %d cache entries", removed)
