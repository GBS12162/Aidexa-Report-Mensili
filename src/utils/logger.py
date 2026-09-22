"""Logging configuration helpers."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_file: Path) -> None:
    """Configure file and console logging for the application."""

    log_file.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.handlers.clear()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def add_file_handler(log_file: Path) -> None:
    """Add an extra file handler without removing the existing logging setup."""

    log_file.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    resolved_path = str(log_file.resolve())
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == resolved_path:
            return

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    root_logger.addHandler(file_handler)
