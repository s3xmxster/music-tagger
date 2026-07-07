from __future__ import annotations

import logging
from pathlib import Path

from core.constants import LOGS_DIR, LOG_FILE_NAME


def setup_logger() -> logging.Logger:
    logs_dir = Path(LOGS_DIR)
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("music_tagger")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    file_handler = logging.FileHandler(logs_dir / LOG_FILE_NAME, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger