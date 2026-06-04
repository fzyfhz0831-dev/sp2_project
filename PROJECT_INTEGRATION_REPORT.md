# Project Integration Report

Generated: 2026-06-04

Final status: PARTIAL

The backend and automation pipeline are wired and verified. The frontend source is wired to the backend and the Vue file compiles with the available Vue compiler, but frontend dependency install/build could not complete because DNS resolution failed for npm registries.

## Relevant Directory Tree

```text
C:\Users\24364\sp2_project
|-- README.md
|-- PROJECT_INTEGRATION_REPORT.md
|-- sp2-backend
|   |-- .env
|   |-- .env.example
|   |-- requirements.txt
|   |-- sample_run.json
|   |-- runs.db
|   |-- app
|   |   |-- main.py
|   |   |-- config.py
|   |   |-- db_service.py
|   |   |-- ai_service.py
|   |   |-- run_parser.py
|   |   |-- pipeline_config.py
|   |   |-- uploads
|   |   |   |-- sample_run.json
|   |   |   |-- normalized_run.json
|   |   |   |-- player_run.json
|   |   |   |-- player_run.example.json
|   |   |   |-- runs
|   |-- data
|   |   |-- processed_runs
|   |-- logs
|   |   |-- uvicorn_stderr.log
|   |   |-- uvicorn_stdout.log
|   |-- mock_data
|       |-- runs
|       |-- knowledge_base
|-- sp2-frontend
|   |-- backup_old_frontend
|   |-- sp2-frontend-main
|       |-- .env.example
|       |-- .env.local
|       |-- package.json
|       |-- package-lock.json
|       |-- vite.config.js
|       |-- index.html
|       |-- public
|       |   |-- data
|       |   |   |-- run_insights.json
|       |-- src
|           |-- main.js
|           |-- App.vue
|           |-- style.css
|           |-- router
|           |   |-- index.js
|           |-- services
|           |   |-- insightsApi.js
|           |-- views
|               |-- HomePage.vue
|               |-- GuidesPage.vue
|               |-- NotFound.vue
|-- sp2-automatic
    |-- pipeline_runner.py
    |-- test_pipeline.py
    |-- run_full_check.py
    |-- batch_analyze.py
    |-- run_batch_analyze.ps1
    |-- run_pipeline.ps1
    |-- data
    |   |-- player_run.json
    |   |-- player_run.example.json
    |   |-- normalized_run.json
    |   |-- latest_insights.json
    |   |-- loss_classification.json
    |   |-- run_analysis.json
    |   |-- run_analysis.txt
    |   |-- run_recommendations.json
    |-- logs
    |   |-- pipeline.log
    |   |-- batch_analyze.log
    |   |-- batch_analyze_summary.json
    |   |-- batch_analyze_manual.log
    |-- archive
```

Large preserved folders are intentionally omitted from the detailed tree: `sp2-frontend\backup_old_frontend\node_modules`, generated frontend `dist`, Python `__pycache__`, and the many historical automation archives.

## Files Changed

- `README.md`
- `PROJECT_INTEGRATION_REPORT.md`
- `sp2-backend\app\config.py`
- `sp2-backend\app\db_service.py`
- `sp2-backend\app\main.py`
- `sp2-backend\app\pipeline_config.py`
- `sp2-backend\app\run_parser.py`
- `sp2-frontend\sp2-frontend-main\.env.example`
- `sp2-frontend\sp2-frontend-main\.env.local`
- `sp2-frontend\sp2-frontend-main\src\services\insightsApi.js`
- `sp2-frontend\sp2-frontend-main\src\views\HomePage.vue`
- `sp2-frontend\sp2-frontend-main\src\style.css`
- `sp2-automatic\pipeline_runner.py`
- `sp2-automatic\test_pipeline.py`
- `sp2-automatic\run_full_check.py`
- `sp2-automatic\batch_analyze.py`
- `sp2-automatic\run_batch_analyze.ps1`

Runtime/generated items touched by verification:

- `sp2-backend\runs.db`
- `sp2-backend\app\uploads\sample_run.json`
- `sp2-backend\app\uploads\normalized_run.json`
- `sp2-backend\app\uploads\player_run.json`
- `sp2-backend\app\uploads\player_run.example.json`
- `sp2-automatic\data\normalized_run.json`
- `sp2-automatic\data\loss_classification.json`
- `sp2-automatic\data\run_analysis.json`
- `sp2-automatic\data\run_analysis.txt`
- `sp2-automatic\data\run_recommendations.json`
- `sp2-automatic\logs\batch_analyze.log`
- `sp2-automatic\logs\batch_analyze_summary.json`

## Backend

Entry point:

```powershell
sp2-backend\app\main.py
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Available endpoints:

- `GET /health`
- `POST /api/analyze`
- `GET /api/runs`
- `GET /api/runs/{run_id}`

Backend changes:

- Added `.env` loading through `app\config.py`.
- Kept upload storage at `sp2-backend\app\uploads`.
- Added non-destructive SQLite migration for `summary_text`.
- New `/api/analyze` responses include `summary_text`.
- Added read-only run list/detail endpoints.
- Preserved mock AI fallback when `OPENAI_API_KEY` is missing or unusable.

Database:

- Active DB: `sp2-backend\runs.db`
- Current row count after verification: 12
- Latest rows include `summary_text`.

AI setup:

- `OPENAI_API_KEY` is present in `.env`, but it does not look like a usable `sk-...` key.
- Backend used mock AI successfully.
- Add a real `OPENAI_API_KEY` to use real AI.

## Frontend

Framework and package manager:

- Vue 3
- Vite
- npm

Active frontend:

```powershell
sp2-frontend\sp2-frontend-main
```

API config:

```powershell
sp2-frontend\sp2-frontend-main\.env.local
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Frontend integration changes:

- `src\services\insightsApi.js` now exports `analyzeRunFile(file)`.
- `HomePage.vue` keeps the teammate UI and adds a JSON file input.
- Submit posts multipart form data to `POST /api/analyze`.
- UI displays upload status, backend analysis result, saved run ID, and error messages.
- Existing local insights helpers were left in place.

Frontend verification:

- `node --check src\main.js`: passed.
- `node --check src\services\insightsApi.js`: passed.
- `node --check src\router\index.js`: passed.
- `HomePage.vue` parsed and compiled with the available Vue compiler from `backup_old_frontend\node_modules`: passed.
- `npm install`: failed because DNS could not resolve npm registries.
- `npm run build`: failed because `vite` was not installed after the incomplete npm install.

Frontend blocker:

```text
registry.npmmirror.com: getaddrinfo ENOTFOUND
registry.npmjs.org: name resolution failed
```

Manual fix needed:

```powershell
cd C:\Users\24364\sp2_project\sp2-frontend\sp2-frontend-main
npm config get registry
npm config set registry https://registry.npmjs.org/
npm install
npm run build
npm run dev
```

If npmjs is also unreachable on your network, use any reachable npm registry.

## Automation

Main runnable pipeline:

```powershell
sp2-automatic\pipeline_runner.py
```

Windows wrapper:

```powershell
sp2-automatic\run_pipeline.ps1
```

Batch backend upload test:

```powershell
sp2-automatic\batch_analyze.py
sp2-automatic\run_batch_analyze.ps1
```

Automation integration changes:

- `sp2-automatic` now imports consolidated backend modules from `sp2-backend\app`.
- `SP2_PIPELINE_ROOT` lets automation keep outputs under `sp2-automatic\data`, `logs`, and `archive`.
- `app.run_parser.run()` now normalizes `data\player_run.json` into `data\normalized_run.json`.
- `batch_analyze.py` discovers run-like JSON files and posts them to `POST /api/analyze`.
- Batch logs are written to `sp2-automatic\logs`.

Automation verification:

- `python pipeline_runner.py`: passed.
- `python test_pipeline.py`: passed, 11 modules OK, 0 module failures, 5 skipped for missing credentials.
- `python batch_analyze.py --api-base-url http://127.0.0.1:8000 --limit 3`: passed, 3 succeeded, 0 failed.
- `.\run_batch_analyze.ps1 -ApiBaseUrl http://127.0.0.1:8000 -Limit 1`: passed, 1 succeeded, 0 failed.

Automation manual setup still needed:

- Reddit credentials: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`.
- Steam credential: `STEAM_API_KEY`.

Without those values, collectors are skipped and logged. The rest of the pipeline continues.

## Verification Commands Run

Backend:

```powershell
python -m pip install -r requirements.txt
python -c "import fastapi, uvicorn, dotenv, multipart, openai; print('backend dependencies import ok')"
python -m pip check
python -m compileall app
python -c "from app.main import app; print(app.title)"
```

Live backend:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
GET http://127.0.0.1:8000/health
POST http://127.0.0.1:8000/api/analyze with sp2-backend\sample_run.json
GET http://127.0.0.1:8000/api/runs?limit=1
GET http://127.0.0.1:8000/api/runs/{run_id}
```

Observed live backend result:

```json
{
  "health_status": 200,
  "analyze_status": 200,
  "analyze_success": true,
  "run_id": 8,
  "summary_text_present": true,
  "analysis_contains_mock": true,
  "row_count_delta": 1,
  "uploaded_file_exists": true,
  "runs_status": 200,
  "detail_status": 200
}
```

Frontend:

```powershell
npm install
npm run build
node --check src\main.js
node --check src\services\insightsApi.js
node --check src\router\index.js
```

Automation:

```powershell
python -m py_compile pipeline_runner.py test_pipeline.py run_full_check.py batch_analyze.py
python pipeline_runner.py
python test_pipeline.py
python batch_analyze.py --api-base-url http://127.0.0.1:8000 --limit 3
.\run_batch_analyze.ps1 -ApiBaseUrl http://127.0.0.1:8000 -Limit 1
```

## Exact Commands To Run Next

Terminal 1, backend:

```powershell
cd C:\Users\24364\sp2_project\sp2-backend
if (!(Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2, frontend:

```powershell
cd C:\Users\24364\sp2_project\sp2-frontend\sp2-frontend-main
npm install
npm run dev
```

Terminal 3, automation batch test:

```powershell
cd C:\Users\24364\sp2_project\sp2-automatic
.\run_batch_analyze.ps1 -ApiBaseUrl http://127.0.0.1:8000 -Limit 3
```

Manual browser test:

```powershell
http://127.0.0.1:5173
```

Upload:

```powershell
C:\Users\24364\sp2_project\sp2-backend\sample_run.json
```

Verify database rows:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/runs?limit=5
```

Verify uploaded file:

```powershell
Get-ChildItem C:\Users\24364\sp2_project\sp2-backend\app\uploads\sample_run.json
```

## Passed

- Backend dependency install/import check after installing requirements.
- Backend `pip check`.
- Backend compile.
- Backend startup on `127.0.0.1:8000`.
- `GET /health`.
- `POST /api/analyze` with `sample_run.json`.
- Upload saved under `app\uploads`.
- SQLite row inserted and `summary_text` stored for new rows.
- `GET /api/runs`.
- `GET /api/runs/{id}`.
- Mock AI fallback.
- Automation main pipeline.
- Automation validation script.
- Automation Python and PowerShell batch upload tests.
- Frontend JS syntax checks.
- `HomePage.vue` parse/template compile check with available Vue compiler.

## Failed

- Frontend `npm install` failed due DNS/network resolution for npm registries.
- Frontend `npm run build` failed because `vite` was unavailable after incomplete dependency install.
- Frontend dev server was not started because dependencies are incomplete.

## Manual Setup Needed

- Fix npm registry/DNS/network, then rerun frontend `npm install`.
- Add a real `OPENAI_API_KEY` in `sp2-backend\.env` for real AI.
- Add Reddit and Steam credentials if collector data should be live instead of skipped.

## Status

PARTIAL

Backend and automation are integrated and verified. Frontend code is wired to the backend, but final frontend install/build/dev-server verification is blocked by npm registry DNS failure.
