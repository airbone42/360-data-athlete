"""Centralised logging helper for all coach scripts and modules."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

_LOG_FILE = "/tmp/coach_errors.log"
_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure(name: str, level: str = "INFO") -> logging.Logger:
    """Return a logger that writes to stdout and /tmp/coach_errors.log (ERROR+)."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    stream = logging.StreamHandler()
    stream.setLevel(getattr(logging, level.upper(), logging.INFO))
    stream.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))
    logger.addHandler(stream)

    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
