"""
utils/logger.py
---------------
Centralised logging factory.  Import `get_logger` everywhere instead of
calling logging.getLogger directly so all loggers share the same format.
"""

import logging
import sys
from config.settings import LOG_LEVEL, LOG_FORMAT


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for *name*."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    return logger
