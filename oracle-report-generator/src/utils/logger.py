from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_file: Path) -> None:
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

def log_event(message: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info(message)

def log_error(message: str, exc: Exception) -> None:
    logger = logging.getLogger(__name__)
    logger.error("%s: %s", message, exc)