# sp2-backend

FastAPI backend for the Slay the Spire analytics platform.

## Quick start

1. `python -m venv .venv && source .venv/bin/activate`  (or `.venv\Scripts\Activate.ps1` on Windows)
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and fill in your keys
4. `uvicorn app.main:app --reload`

## Structure

- `app/main.py`        — entry point
- `app/ai_service.py`   — LLM calls
- `app/db_service.py`   — persistence
- `app/run_parser.py`   — run-file ingestion
- `app/config.py`       — env-based settings
- `uploads/`            — user-uploaded run files
