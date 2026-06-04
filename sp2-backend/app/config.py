from __future__ import annotations

from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent
ENV_PATH = BASE_DIR / ".env"

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - keeps imports usable before install.
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(ENV_PATH)

UPLOAD_DIR = APP_DIR / "uploads"
DATABASE_PATH = BASE_DIR / "runs.db"
