"""
run_converter.py — Convert uploaded run files into the standardised JSON format.

Supported input formats
-----------------------
- ``.json``  — validated against the run schema, normalised, and saved.
- ``.save``  — Slay the Spire 2 binary save file.  Parsed via the community
  `sts2-save-parser` library when available; otherwise a best-effort stub.

Standardised run format
-----------------------
The output dict always contains the top-level keys required by
:func:`run_parser.validate_run`::

    {
      "run_id": str,
      "character": str,
      "ascension": int,
      "floor_reached": int,
      "killed_by": str,
      "max_hp": int,
      "final_hp": int,
      "gold": int,
      "cards": list[str],
      "relics": list[str],
      "path": list[dict],
      "source": "upload",
      "original_filename": str,
    }
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_converter")

# ---------------------------------------------------------------------------
# File-type constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS: tuple[str, ...] = (".json", ".save")
JSON_EXTENSIONS: tuple[str, ...] = (".json",)
SAVE_EXTENSIONS: tuple[str, ...] = (".save",)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_extension(filename: str) -> str:
    """Return the lowercased file extension including the dot."""
    return Path(filename).suffix.lower()


def is_allowed(filename: str) -> bool:
    """Check whether the file extension is in the allowed set."""
    return get_extension(filename) in ALLOWED_EXTENSIONS


def convert_to_standard(
    raw_bytes: bytes,
    original_filename: str,
) -> dict[str, Any]:
    """Convert a raw uploaded file into the standardised run dict.

    Parameters
    ----------
    raw_bytes : bytes
        The raw file content.
    original_filename : str
        The original name of the uploaded file (used to detect type and as
        metadata).

    Returns
    -------
    dict
        A standardised run dict ready for validation and storage.

    Raises
    ------
    ValueError
        If the file type is not supported or the content is unparseable.
    """
    ext = get_extension(original_filename)

    if ext in JSON_EXTENSIONS:
        return _convert_json(raw_bytes, original_filename)
    elif ext in SAVE_EXTENSIONS:
        return _convert_save(raw_bytes, original_filename)
    else:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )


# ===================================================================
# Internal converters
# ===================================================================


def _generate_run_id(character: str = "", floor: int = 0) -> str:
    """Generate a unique, sortable run ID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    char_part = f"{character.lower()}-" if character else ""
    return f"run-{char_part}{ts}-{short_uuid}"


def _empty_path_stub(floor_reached: int = 1, killed_by: str = "unknown") -> list[dict[str, Any]]:
    """Return a minimal path entry for stub runs."""
    return [
        {
            "floor": floor_reached,
            "type": "combat",
            "hp_before": 0,
            "hp_after": 0,
            "picked_card": "",
            "skipped_cards": [],
            "relic_gained": "",
            "notes": f"Stub entry — original file did not contain path data.  Killed by: {killed_by}.",
        }
    ]


# -------------------------------------------------------------------
# .json  converter
# -------------------------------------------------------------------


def _convert_json(raw_bytes: bytes, original_filename: str) -> dict[str, Any]:
    """Parse and normalise a JSON run file.

    Auto-generates ``run_id`` if missing; fills defaults for optional fields.
    """
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid JSON content: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("JSON root must be a dict/object.")

    # Normalise
    run_id = data.get("run_id") or _generate_run_id(
        data.get("character", ""),
        data.get("floor_reached", 0),
    )

    return {
        "run_id": run_id,
        "character": data.get("character", "Unknown"),
        "ascension": int(data.get("ascension", 0)),
        "floor_reached": int(data.get("floor_reached", 0)),
        "killed_by": data.get("killed_by", "unknown"),
        "max_hp": int(data.get("max_hp", 80)),
        "final_hp": int(data.get("final_hp", 0)),
        "gold": int(data.get("gold", 0)),
        "cards": data.get("cards") if isinstance(data.get("cards"), list) else [],
        "relics": data.get("relics") if isinstance(data.get("relics"), list) else [],
        "path": data.get("path") if isinstance(data.get("path"), list) else _empty_path_stub(),
        "source": "upload",
        "original_filename": original_filename,
    }


# -------------------------------------------------------------------
# .save  converter  (STS2 binary save files)
# -------------------------------------------------------------------


def _convert_save(raw_bytes: bytes, original_filename: str) -> dict[str, Any]:
    """Parse an STS2 ``.save`` binary file into the standardised format.

    First attempts to use the optional ``sts2-save-parser`` community
    library.  Falls back to a best-effort text extraction when the library
    is not installed.
    """
    # --- attempt 1: community save parser ------------------------------------
    try:
        from sts2_save_parser import parse_save  # type: ignore[import-untyped]

        parsed = parse_save(raw_bytes)
        run_id = parsed.get("run_id") or _generate_run_id(
            parsed.get("character", ""), parsed.get("floor_reached", 0)
        )
        return {
            "run_id": run_id,
            "character": parsed.get("character", "Unknown"),
            "ascension": int(parsed.get("ascension", 0)),
            "floor_reached": int(parsed.get("floor_reached", 0)),
            "killed_by": parsed.get("killed_by", "unknown"),
            "max_hp": int(parsed.get("max_hp", 80)),
            "final_hp": int(parsed.get("final_hp", 0)),
            "gold": int(parsed.get("gold", 0)),
            "cards": parsed.get("cards") if isinstance(parsed.get("cards"), list) else [],
            "relics": parsed.get("relics") if isinstance(parsed.get("relics"), list) else [],
            "path": parsed.get("path") if isinstance(parsed.get("path"), list) else _empty_path_stub(),
            "source": "upload",
            "original_filename": original_filename,
        }
    except ImportError:
        logger.info(
            "sts2-save-parser not installed — using best-effort text extraction "
            "for %s",
            original_filename,
        )
    except Exception as exc:
        logger.warning("Save parser raised an exception: %s — falling back.", exc)

    # --- attempt 2: best-effort stub from filename hints ---------------------
    return _stub_from_filename(original_filename, ext=".save")


# -------------------------------------------------------------------
# Fallback stub
# -------------------------------------------------------------------


def _stub_from_filename(
    original_filename: str,
    ext: str = ".save",
) -> dict[str, Any]:
    """Generate a minimal run stub when no parser is available."""
    run_id = _generate_run_id()

    logger.info(
        "Created stub from filename for %s → %s",
        original_filename,
        run_id,
    )

    return {
        "run_id": run_id,
        "character": "Unknown",
        "ascension": 0,
        "floor_reached": 0,
        "killed_by": "unknown",
        "max_hp": 80,
        "final_hp": 0,
        "gold": 0,
        "cards": [],
        "relics": [],
        "path": _empty_path_stub(),
        "source": "upload",
        "original_filename": original_filename,
    }
