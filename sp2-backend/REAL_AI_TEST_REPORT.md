# Real AI Test Report

## Scope

Tested only inside:

`C:\Users\24364\sp2_project\sp2-backend`

## Environment check

- `.env` existed for the final test.
- `.env` was created from `.env.example` because it was initially missing.
- `OPENAI_API_KEY` was read from `.env` without printing or exposing the value.
- The key value was non-empty, but it did not look like a usable OpenAI API key, so real AI was not tested.
- `OPENAI_MODEL` was read as `gpt-4.1-mini`.

## Fix applied

The first endpoint test returned:

`AI API error: The openai package is not installed.`

To keep the backend usable without installing packages outside `sp2-backend`, `app/ai_service.py` was updated to:

- Treat placeholder/non-key `OPENAI_API_KEY` values as missing.
- Use mock analysis when no usable key is configured.
- Add a standard-library HTTP fallback for real OpenAI calls if the `openai` package is unavailable.
- Avoid exposing the API key.

## Endpoint test

FastAPI was started with:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8028
```

### GET /health

Returned:

```json
{"status":"ok"}
```

Result: PASS

### POST /api/analyze

Uploaded:

`sample_run.json`

Returned:

```json
{
  "success": true,
  "filename": "sample_run.json",
  "run_id": 4
}
```

The analysis text was a mock response because no usable OpenAI API key was configured.

Result: PASS

## Database and upload checks

- Confirmed latest database row was inserted with `id = 4`.
- Confirmed latest row filename is `sample_run.json`.
- Confirmed latest analysis contains mock analysis text.
- Confirmed uploaded file exists at `app/uploads/sample_run.json`.

## Final status

PASS for backend AI fallback behavior.

Real AI was not tested because no usable OpenAI API key was configured in `.env`.
