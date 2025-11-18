"""Central logging setup for chat_pipeline."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DEFAULT_LOG_DIR_ENV = "CHAT_PIPELINE_LOG_DIR"


def setup_logging(
    *,
    level: Optional[str] = None,
    to_file: bool = False,
    log_dir: Optional[Path] = None,
) -> logging.Logger:
    """Configure root logging once; return the root logger."""

    root = logging.getLogger()
    if root.handlers:
        return root

    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    root.setLevel(log_level)

    formatter = logging.Formatter(DEFAULT_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if to_file:
        env_dir = os.getenv(DEFAULT_LOG_DIR_ENV)
        target_dir = log_dir or (Path(env_dir) if env_dir else Path.cwd() / "logs")
        target_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(target_dir / "chat_pipeline.log")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    return root


__all__ = ["setup_logging"]
