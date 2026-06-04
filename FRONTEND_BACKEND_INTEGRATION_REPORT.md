# Frontend Backend Integration Report

Generated at: 2026-06-04 12:05 Asia/Shanghai

## 1. README Summary

Read source: `C:\Users\24364\sp2_project\sp2-frontend\README.md`

- The frontend is `SP2-Frontend`, a SpireInsight MVP built with Vue 3 and Vite.
- It supports two insight data modes through Vite environment variables.
- Local mode is the default and reads `/data/run_insights.json`.
- Remote mode fetches from `VITE_INSIGHTS_API_URL` and falls back to local JSON if the remote request fails.
- README environment variables:
  - `VITE_INSIGHTS_API_MODE=local`
  - `VITE_INSIGHTS_API_URL=`
  - remote example: `VITE_INSIGHTS_API_MODE=remote`, `VITE_INSIGHTS_API_URL=https://your-api.example.com/insights`
- No real API URL is hardcoded for the README-described insights mode.

## 2. Actual Frontend Project

- Actual frontend directory: `C:\Users\24364\sp2_project\sp2-frontend`
- Actual entry files:
  - `index.html`
  - `vite.config.js`
  - `src\main.js`
  - `src\App.vue`
- Framework type: Vue 3 + Vite.
- Vite confirmed by `package.json` scripts and `vite.config.js`.
- Nested directory found: `C:\Users\24364\sp2_project\sp2-frontend\SP2-Frontend`
- Nested directory status: empty / no project files found by `rg --files`.
- True runnable frontend: `C:\Users\24364\sp2_project\sp2-frontend`

## 3. Frontend Startup And API Configuration

- Dependency install command: `npm install`
- Dev command: `npm run dev`
- Build command: `npm run build`
- Preview command: `npm run preview`
- API base config file: `C:\Users\24364\sp2_project\sp2-frontend\.env.local`
- Current API base config:
  - `VITE_API_BASE_URL=http://127.0.0.1:8000`
- API base is read in `src\services\insightsApi.js`:
  - `import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'`
- Upload function:
  - `src\services\insightsApi.js`
  - `analyzeRunFile(file)` posts multipart form data to `${API_BASE_URL}/api/analyze`.
- Upload page/component:
  - `src\views\HomePage.vue`
  - File input accepts `.json,application/json`.
  - Submit button calls `analyzeRun()`, which calls `analyzeRunFile(file)`.

## 4. Frontend Expected Backend Interfaces

From current frontend source:

- `POST /api/analyze`
  - Request: `multipart/form-data`, field name `file`
  - Response fields consumed by frontend:
    - `success`
    - `filename`
    - `summary_text`
    - `analysis`
    - `run_id`

Other frontend data paths:

- `/data/run_insights.json` for local README-described insights mode.
- Optional `VITE_INSIGHTS_API_URL` for remote insights mode, separate from upload analysis.

## 5. Backend Confirmation

- User-mentioned backend path `C:\Users\24364\sp2_project\backend` was not the actual backend directory.
- Actual backend directory: `C:\Users\24364\sp2_project\sp2-backend`
- FastAPI app: `sp2-backend\app\main.py`
- Existing uvicorn listener found on `127.0.0.1:8000`, process command line uses `python -m uvicorn app.main:app`.

Backend endpoints confirmed in code:

- `GET /health`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `POST /api/analyze`

CORS confirmed in code and runtime:

- Allowed origins:
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
- Runtime OPTIONS test returned:
  - `access-control-allow-origin: http://127.0.0.1:5173`
  - allowed methods include `POST`

Upload/save behavior:

- `POST /api/analyze` saves uploaded JSON into `sp2-backend\app\uploads`.
- Test upload saved/updated `sp2-backend\app\uploads\sample_run.json`.
- Analysis results are persisted to `sp2-backend\runs.db`.

## 6. Automation / Scripts / Pipeline

Automation directory found:

- `C:\Users\24364\sp2_project\sp2-automatic`

Existing automation files confirmed:

- `batch_analyze.py`
- `run_batch_analyze.ps1`
- `pipeline_runner.py`
- `test_pipeline.py`
- `run_pipeline.ps1`
- `schedule_pipeline.ps1`
- `setup_windows_task.ps1`

Existing runtime folders:

- `sp2-automatic\logs` exists.
- `sp2-automatic\archive` exists and contains many archived insight JSON/ZIP files.
- `sp2-backend\logs` exists.
- `sp2-backend\archive` exists but is empty.

Batch backend upload support:

- `sp2-automatic\batch_analyze.py` checks `GET /health`.
- It discovers run-like JSON files.
- It uploads files to `POST /api/analyze`.
- It writes `sp2-automatic\logs\batch_analyze_summary.json`.

No new automation script was needed.

## 7. Files Modified

Source/UI changes:

- No frontend UI files were modified.
- No frontend source files were modified.
- No backend source files were modified.
- No automation source files were modified.

Created report:

- `C:\Users\24364\sp2_project\FRONTEND_BACKEND_INTEGRATION_REPORT.md`

Runtime files changed by validation:

- `sp2-backend\runs.db` received new analyzed run rows.
- `sp2-backend\app\uploads\sample_run.json` was written by upload validation.
- `sp2-automatic\logs\batch_analyze.log` was appended.
- `sp2-automatic\logs\batch_analyze_summary.json` was updated.

## 8. Tests Run

Backend:

- `python -c "import fastapi, uvicorn, multipart; ..."`
  - Result: PASS
- `GET http://127.0.0.1:8000/health`
  - Result: PASS
  - Response: `{"status":"ok"}`
- `POST http://127.0.0.1:8000/api/analyze` with `sp2-backend\sample_run.json`
  - Result: PASS
  - Response included `success: true`, `filename`, `summary_text`, `analysis`, `run_id: 13`
- `OPTIONS http://127.0.0.1:8000/api/analyze` with Vite origin
  - Result: PASS
  - CORS response allowed `http://127.0.0.1:5173`
- `GET http://127.0.0.1:8000/api/runs?limit=5`
  - Result: PASS
  - Latest rows included uploaded run IDs 14, 15, 16 and direct test run ID 13.

Automation:

- `python batch_analyze.py --api-base-url http://127.0.0.1:8000 --limit 3`
  - Result: PASS
  - Summary: 3 succeeded, 0 failed
  - Uploaded:
    - `normalized_run.json` as `run_id=14`
    - `player_run.example.json` as `run_id=15`
    - `player_run.json` as `run_id=16`

Frontend:

- `npm ls --depth=0`
  - Initial result: FAIL, dependencies missing.
- `npm install`
  - Result: FAIL
  - Cause: npm registry DNS/network failure.
  - Default registry attempt failed against `registry.npmmirror.com` with `ENOTFOUND`.
  - Official registry attempt with `--registry=https://registry.npmjs.org/` also failed with `ENOTFOUND`.
- `Resolve-DnsName registry.npmjs.org`
  - Result: timed out.
- `Resolve-DnsName registry.npmmirror.com`
  - Result: timed out.
- `npm ping`
  - Result: timed out.
- `npm run dev -- --host 127.0.0.1 --port 5173`
  - Result: FAIL
  - Error: `'vite' is not recognized as an internal or external command`
  - Cause: required frontend dependencies could not be installed.
- `npm run build`
  - Result: FAIL
  - Error: `'vite' is not recognized as an internal or external command`
  - Cause: required frontend dependencies could not be installed.

## 9. Successes And Failures

Success:

- Actual frontend entry directory identified.
- Vite/Vue project confirmed.
- Nested `SP2-Frontend` directory identified as non-runnable/empty.
- Existing frontend upload flow already points to `POST /api/analyze`.
- `.env.local` already points to `http://127.0.0.1:8000`.
- Backend `/health` works.
- Backend `/api/analyze` works.
- Backend CORS works for Vite dev origin.
- Uploaded JSON file is saved.
- Analysis JSON shape matches what `HomePage.vue` formats and displays.
- Automation batch upload to backend works.

Failure / incomplete:

- Frontend dependency installation could not complete because npm registry DNS/network resolution failed.
- Because dependencies could not be installed, local `npm run dev` failed before starting Vite, so browser-level frontend/backend connection validation was not completed.

## 10. Next Commands For User

After DNS/network access to npm registry works:

```powershell
cd C:\Users\24364\sp2_project\sp2-frontend
npm install --registry=https://registry.npmjs.org/
npm run dev
```

In another terminal, if backend is not already running:

```powershell
cd C:\Users\24364\sp2_project\sp2-backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open:

```text
http://127.0.0.1:5173
```

For batch validation:

```powershell
cd C:\Users\24364\sp2_project\sp2-automatic
python batch_analyze.py --api-base-url http://127.0.0.1:8000 --limit 3
```

## 11. Final Status

PARTIAL

Reason: backend integration and automation upload are working, and frontend source/config already targets the backend correctly. The only incomplete part is runtime frontend verification because npm dependencies could not be installed due DNS/network failure to npm registries.
