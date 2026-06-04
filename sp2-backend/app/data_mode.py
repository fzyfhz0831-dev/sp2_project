"""
data_mode.py — Track and manage the application's data mode.

The service operates in one of three modes:

===========  ===============================================================
mock         Only mock runs are available (default).
real         Real player runs have reached the threshold (>= 20), and the
             service prioritises real-run analysis.
mixed        Both mock and real runs exist, but the real count is below the
             threshold — serves both while collecting more real data.
===========  ===============================================================

Mode is persisted as a small JSON file so it survives restarts.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("data_mode")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODE_FILE = Path(__file__).resolve().parents[1] / "data" / "mode.json"
_REAL_RUNS_DIR = Path(__file__).resolve().parents[1] / "data" / "processed_runs"
_REAL_MODE_THRESHOLD = 20

Mode = Literal["mock", "real", "mixed"]

# ---------------------------------------------------------------------------
# Low-level persistence
# ---------------------------------------------------------------------------


def _read_mode_file() -> dict[str, Any]:
    """Return the contents of the mode file, or a safe default."""
    if not _MODE_FILE.is_file():
        return {"mode": "mock", "real_run_count": 0}
    try:
        return json.loads(_MODE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Corrupt mode file — resetting to defaults.  %s", exc)
        return {"mode": "mock", "real_run_count": 0}


def _write_mode_file(data: dict[str, Any]) -> None:
    """Atomically write the mode dict to disk."""
    _MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _MODE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_MODE_FILE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_mode() -> Mode:
    """Return the current data mode.

    Returns
    -------
    str
        One of ``"mock"``, ``"real"``, ``"mixed"``.
    """
    data = _read_mode_file()
    mode: str = data.get("mode", "mock")
    if mode not in ("mock", "real", "mixed"):
        logger.warning("Unknown mode '%s' — falling back to 'mock'.", mode)
        return "mock"
    return mode  # type: ignore[return-value]


def get_real_run_count() -> int:
    """Return the number of real processed runs on disk."""
    if not _REAL_RUNS_DIR.is_dir():
        return 0
    return len(list(_REAL_RUNS_DIR.glob("*.json")))


def refresh_mode() -> Mode:
    """Recalculate the mode based on the current real-run count.

    This should be called whenever a new real run is added or removed.

    Rules
    -----
    - 0 real runs → ``"mock"``
    - 1–19 real runs → ``"mixed"``
    - ≥ 20 real runs → ``"real"``

    Returns
    -------
    str
        The new (current) mode.
    """
    real_count = get_real_run_count()
    data = _read_mode_file()

    if real_count >= _REAL_MODE_THRESHOLD:
        new_mode: Mode = "real"
    elif real_count > 0:
        new_mode = "mixed"
    else:
        new_mode = "mock"

    old_mode = data.get("mode", "mock")
    data["mode"] = new_mode
    data["real_run_count"] = real_count
    _write_mode_file(data)

    if old_mode != new_mode:
        logger.info(
            "Mode switched: %s → %s  (real runs: %d, threshold: %d)",
            old_mode,
            new_mode,
            real_count,
            _REAL_MODE_THRESHOLD,
        )
    else:
        logger.info(
            "Mode: %s  (real runs: %d, threshold: %d)",
            new_mode,
            real_count,
            _REAL_MODE_THRESHOLD,
        )

    return new_mode


def is_real_mode_active() -> bool:
    """Return True when real-run analysis should be the primary path.

    True for ``"real"`` mode; in ``"mixed"`` mode we still serve mock data
    alongside real data, so this returns False.
    """
    return get_mode() == "real"
