from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.config import DATABASE_PATH


class DatabaseError(Exception):
    """Raised when a SQLite operation fails."""


def init_db() -> None:
    """Create the runs table when it does not already exist."""
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    raw_json TEXT,
                    parsed_json TEXT,
                    summary_text TEXT,
                    analysis TEXT,
                    created_at TEXT
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(runs)").fetchall()
            }
            if "summary_text" not in columns:
                connection.execute("ALTER TABLE runs ADD COLUMN summary_text TEXT")
    except sqlite3.Error as error:
        raise DatabaseError(str(error)) from error


def save_run(
    filename: str,
    raw_data: Any,
    parsed_data: Any,
    analysis: str,
    summary_text: str | None = None,
) -> int:
    """Save one analyzed run and return the inserted row ID."""
    init_db()

    raw_json = json.dumps(raw_data, ensure_ascii=False)
    parsed_json = json.dumps(parsed_data, ensure_ascii=False)
    if summary_text is None and isinstance(parsed_data, dict):
        summary_text = parsed_data.get("summary_text")
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.execute(
                """
                INSERT INTO runs (filename, raw_json, parsed_json, summary_text, analysis, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (filename, raw_json, parsed_json, summary_text, analysis, created_at),
            )
            return int(cursor.lastrowid)
    except sqlite3.Error as error:
        raise DatabaseError(str(error)) from error


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    """Return recent analyzed runs without loading full raw JSON blobs."""
    init_db()
    safe_limit = max(1, min(int(limit), 200))

    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, filename, summary_text, analysis, created_at
                FROM runs
                ORDER BY id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
    except sqlite3.Error as error:
        raise DatabaseError(str(error)) from error

    return [dict(row) for row in rows]


def get_run(run_id: int) -> dict[str, Any] | None:
    """Return one analyzed run with decoded raw and parsed JSON fields."""
    init_db()

    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT id, filename, raw_json, parsed_json, summary_text, analysis, created_at
                FROM runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
    except sqlite3.Error as error:
        raise DatabaseError(str(error)) from error

    if row is None:
        return None

    run = dict(row)
    for field in ("raw_json", "parsed_json"):
        value = run.get(field)
        if isinstance(value, str):
            try:
                run[field] = json.loads(value)
            except json.JSONDecodeError:
                pass

    return run
