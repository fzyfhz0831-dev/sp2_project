# SP2 Full-Stack Project

This workspace connects:

- FastAPI backend: `sp2-backend`
- Vue/Vite frontend: `sp2-frontend\sp2-frontend-main`
- Automation pipeline: `sp2-automatic`

## Backend

```powershell
cd C:\Users\24364\sp2_project\sp2-backend

if (!(Test-Path .venv)) {
  python -m venv .venv
}

.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend URLs:

- Health: `http://127.0.0.1:8000/health`
- API docs: `http://127.0.0.1:8000/docs`
- Analyze: `POST http://127.0.0.1:8000/api/analyze`
- Runs: `GET http://127.0.0.1:8000/api/runs`

## Frontend

```powershell
cd C:\Users\24364\sp2_project\sp2-frontend\sp2-frontend-main
npm install
npm run dev
```

The frontend uses:

```powershell
VITE_API_BASE_URL=http://127.0.0.1:8000
```

This is already set in `.env.local` for local development.

If npm cannot resolve the configured registry, fix network/DNS or set a reachable registry, then rerun `npm install`:

```powershell
npm config get registry
npm config set registry https://registry.npmjs.org/
npm install
```

## Automation

Run the main pipeline:

```powershell
cd C:\Users\24364\sp2_project\sp2-automatic
python pipeline_runner.py
```

Or use the PowerShell wrapper:

```powershell
cd C:\Users\24364\sp2_project\sp2-automatic
.\run_pipeline.ps1
```

Run the backend batch upload test while the backend is running:

```powershell
cd C:\Users\24364\sp2_project\sp2-automatic
.\run_batch_analyze.ps1 -ApiBaseUrl http://127.0.0.1:8000 -Limit 3
```

## Full System Test

1. Start the backend in Terminal 1:

```powershell
cd C:\Users\24364\sp2_project\sp2-backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

2. Start the frontend in Terminal 2:

```powershell
cd C:\Users\24364\sp2_project\sp2-frontend\sp2-frontend-main
npm install
npm run dev
```

3. Open the frontend URL printed by Vite, usually:

```powershell
http://127.0.0.1:5173
```

4. Upload a run JSON, for example:

```powershell
C:\Users\24364\sp2_project\sp2-backend\sample_run.json
```

5. Verify the API result and saved database row:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/runs?limit=5
```

6. Verify the uploaded file exists:

```powershell
Get-ChildItem C:\Users\24364\sp2_project\sp2-backend\app\uploads\sample_run.json
```

## API Keys

Backend AI settings live in:

```powershell
C:\Users\24364\sp2_project\sp2-backend\.env
```

If `OPENAI_API_KEY` is missing or not a usable `sk-...` key, the backend safely returns mock analysis. Add a real key to use real AI.

Automation collectors also need optional Reddit and Steam credentials. Without them, those collectors are skipped and logged, while the rest of the pipeline continues.
