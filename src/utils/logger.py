"""Logging configuration helpers."""

from __future__ import annotations

import logging
from pathlib import Path

from config import get_config


def setup_logging(log_file: Path, *, console: bool = True) -> None:
    """Configure file and console logging for the application."""

    log_file.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.handlers.clear()

    cfg = get_config()
    handlers: list[logging.Handler] = [logging.FileHandler(log_file, encoding="utf-8")]
    if console:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=getattr(logging, cfg.logging_level, logging.INFO),
        format=cfg.logging_format,
        handlers=handlers,
    )
