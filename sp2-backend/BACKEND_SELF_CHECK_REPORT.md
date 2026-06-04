# Backend Self Check Report

## Scope

Checked backend from:

`C:\Users\24364\sp2_project\sp2-backend`

## FastAPI startup

Started FastAPI with:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8027
```

Result: PASS

## Endpoint checks

### GET /health

Response:

```json
{"status":"ok"}
```

Result: PASS

### POST /api/analyze

Uploaded:

`sample_run.json`

Response:

```json
{
  "success": true,
  "filename": "sample_run.json",
  "run_id": 2
}
```

The response included an analysis string. `OPENAI_API_KEY` was not configured, so the backend returned the expected mock AI analysis.

Result: PASS

## Upload check

Confirmed uploaded file exists:

`app/uploads/sample_run.json`

Result: PASS

## Database check

Confirmed database exists:

`runs.db`

Newest row:

- `id`: 2
- `filename`: `sample_run.json`
- `raw_json`: present, contains uploaded run data
- `parsed_json`: present, includes `summary_text`
- `analysis`: present, contains mock analysis
- `created_at`: present

Result: PASS

## Final status

PASS
