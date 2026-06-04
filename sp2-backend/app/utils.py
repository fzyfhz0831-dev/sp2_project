from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

try:
    from app.pipeline_config import PIPELINE_LOG_PATH
except ImportError:
    from app.pipeline_config import PIPELINE_LOG_PATH


T = TypeVar("T")


def setup_logger(log_file_path: str) -> logging.Logger:
    """Configure a reusable logger that writes pipeline messages to one file."""
    log_path = Path(log_file_path)

    # Create logs/ automatically before opening the log file.
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("sp2_run_doctor")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid duplicate log lines when several modules import this helper.
    if not logger.handlers:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    return logger


def _default_logger() -> logging.Logger:
    """Return the shared pipeline logger for utility-level error messages."""
    return setup_logger(str(PIPELINE_LOG_PATH))


def save_json(data: Any, path: str | Path) -> None:
    """Save Python data to JSON and log any write errors."""
    output_path = Path(path)
    logger = _default_logger()

    try:
        # Create the parent folder so callers can pass paths inside data/.
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

        logger.info("Saved JSON file: %s", output_path)
    except Exception as error:
        logger.exception("Failed to save JSON file %s: %s", output_path, error)
        raise


def load_json(path: str | Path, default: T) -> T:
    """Load JSON data, returning a default value when the file is missing."""
    input_path = Path(path)

    if not input_path.exists():
        return default

    with input_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def retry(
    func: Callable[..., T],
    retries: int = 3,
    delay: int = 5,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Retry a function when it raises an exception."""
    logger = _default_logger()
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            logger.info("Retryable operation started (attempt %s/%s)", attempt, retries)
            return func(*args, **kwargs)
        except Exception as error:
            last_error = error
            logger.warning(
                "Retryable operation failed (attempt %s/%s): %s",
                attempt,
                retries,
                error,
            )

            if attempt < retries:
                time.sleep(delay)

    logger.error("Retryable operation failed after %s attempts", retries)
    raise RuntimeError(f"Operation failed after {retries} attempts") from last_error
