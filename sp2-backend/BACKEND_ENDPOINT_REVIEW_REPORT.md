# Backend Endpoint Review Report

## Files checked

- `app/main.py`
- `app/ai_service.py`
- `app/db_service.py`
- `app/run_parser.py`
- `app/config.py`
- `app/uploads/`
- `requirements.txt`
- `.env.example`

## Bugs found

1. `app/main.py` still used the old `save_analysis()` compatibility wrapper instead of calling `save_run()` directly.
2. `app/ai_service.py` used the older default model `gpt-4o-mini`; requirement is `gpt-4.1-mini`.
3. Valid JSON files written by Windows PowerShell could be rejected because `main.py` read uploads as plain `utf-8`, which does not tolerate a UTF-8 BOM.
4. A stale runtime database existed at `app/runs.db`; the required active database location is `sp2-backend/runs.db`.

## Bugs fixed

1. Updated `app/main.py` to import and call:
   - `from app.db_service import DatabaseError, init_db, save_run`
2. Updated `/api/analyze` to call:
   - `save_run(filename, raw_data, parsed_data, analysis)`
3. Added upload-save error handling for `OSError`.
4. Updated JSON reading to `encoding="utf-8-sig"` so normal UTF-8 and BOM-prefixed UTF-8 both work.
5. Updated `app/ai_service.py` default model to `gpt-4.1-mini`.
6. Made `AIServiceError` inherit from `RuntimeError`, so API errors are caught cleanly by the endpoint.
7. Removed stale `app/runs.db` and recreated the active database at `runs.db` in the `sp2-backend` root.
8. Updated `.env.example` and `requirements.txt` for the OpenAI-backed AI module.

## Endpoint test results

TestClient was attempted, but the installed Starlette TestClient requires `httpx2`, which is not installed in this environment. A live uvicorn test was used instead.

Command shape verified:

```powershell
uvicorn app.main:app --reload
```

Results:

- `GET /health` returned `{"status":"ok"}` with HTTP 200.
- `POST /api/analyze` with valid `test_sample_run.json` returned HTTP 200:
  - `success: true`
  - `filename: "test_sample_run.json"`
  - `analysis`: mock analysis text, because no `OPENAI_API_KEY` is configured
  - `run_id: 1`
- `POST /api/analyze` with `test_notes.txt` returned HTTP 400:
  - `{"detail":"Invalid file type. Please upload a JSON file."}`
- `POST /api/analyze` with invalid JSON returned HTTP 400:
  - `{"detail":"Invalid JSON file."}`

## Database test result

Confirmed:

- `runs.db` exists at `C:\Users\24364\sp2_project\sp2-backend\runs.db`.
- Table `runs` exists with:
  - `id`
  - `filename`
  - `raw_json`
  - `parsed_json`
  - `analysis`
  - `created_at`
- One valid endpoint request inserted row:
  - `id = 1`
  - `filename = test_sample_run.json`

## Upload test result

Confirmed uploaded test files were saved under:

`C:\Users\24364\sp2_project\sp2-backend\app\uploads`

## Final status

PASS
