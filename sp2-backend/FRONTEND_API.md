# SP2 Backend — Frontend API Reference

**For:** Vue frontend integration (`sp2-frontend/`)  
**Base URL:** `http://localhost:8000` (dev)  
**CORS origins:** `http://localhost:5173`, `http://127.0.0.1:5173`

---

## Endpoints

### `GET /health`

Health check. Use this to verify the backend is reachable before sending analysis requests.

**Request**

```
GET /health
```

No parameters, no body.

**Response `200 OK`**

```json
{
  "status": "ok"
}
```

---

### `POST /api/analyze`

Upload a Slay the Spire 2 run file (JSON) and receive AI-powered analysis. The run is parsed, analyzed, persisted to SQLite, and the result is returned.

**Request**

```
POST /api/analyze
Content-Type: multipart/form-data
```

| Field  | Type | Required | Description                    |
|--------|------|----------|--------------------------------|
| `file` | file | yes      | A `.json` run file to analyze. |

The uploaded file **must** have a `.json` extension and contain a single JSON object. The parser accepts multiple key-name conventions so most STS2 run exports should work without reformatting.

**Recognised JSON keys** (any one of each group is sufficient)

| Group         | Accepted keys                                      |
|---------------|----------------------------------------------------|
| character     | `character`, `player_class`, `class`               |
| floor         | `floor_reached`, `floor`, `floor_num`              |
| victory       | `victory`, `won`, `is_victory`                     |
| cards / deck  | `cards`, `deck`, `master_deck`                     |
| relics        | `relics`, `relic_names`                            |
| damage        | `damage_taken`, `damage`, `damage_log`             |
| path / route  | `path`, `floor_path`, `route`                      |
| score         | `score`, `final_score`                             |
| boss          | `bosses`, `boss_relics`, `boss`, `killed_by`, `final_boss` |

**Example minimal upload**

```json
{
  "character": "Ironclad",
  "floor_reached": 33,
  "victory": false,
  "cards": ["Strike", "Defend", "Bash", "Clothesline"],
  "relics": ["Burning Blood"],
  "path": [
    { "floor": 1, "type": "combat" },
    { "floor": 2, "type": "rest" },
    { "floor": 3, "type": "elite" }
  ]
}
```

**Success response `200 OK`**

```json
{
  "success": true,
  "filename": "my-run.json",
  "analysis": "<multi-line AI analysis string>",
  "run_id": 1
}
```

| Field      | Type    | Description                                    |
|------------|---------|------------------------------------------------|
| `success`  | boolean | Always `true` on success.                      |
| `filename` | string  | Sanitised original filename.                   |
| `analysis` | string  | AI-generated review (or mock placeholder).     |
| `run_id`   | integer | Auto-increment ID of the saved database row.   |

The `analysis` string contains four labelled sections:

1. **Reason for success/failure**
2. **3 key mistakes**
3. **3 improvement suggestions**
4. **Short summary**

When no `OPENAI_API_KEY` is configured the response is a mock placeholder with the same structure.

**Error responses**

| Status | Trigger                                    | Body                                              |
|--------|--------------------------------------------|---------------------------------------------------|
| 400    | File extension is not `.json`              | `{"detail":"Invalid file type. Please upload a JSON file."}` |
| 400    | File contains invalid JSON                 | `{"detail":"Invalid JSON file."}`                 |
| 400    | JSON is valid but not a run object         | `{"detail":"Uploaded JSON must contain one JSON object."}` |
| 422    | No `file` field in the multipart request   | FastAPI validation detail (automatic).            |
| 500    | Could not save or read the uploaded file   | `{"detail":"Could not save uploaded file."}` etc. |
| 500    | Database write failed                      | `{"detail":"Database error: …"}`                  |
| 502    | AI provider returned an error              | `{"detail":"AI API error: …"}`                    |

---

## CORS

The backend allows requests from the Vite dev server. If your frontend runs on a different origin, update `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Vue / Axios Usage

### Health check

```js
import axios from 'axios'

const API = axios.create({ baseURL: 'http://localhost:8000' })

async function checkHealth() {
  try {
    const { data } = await API.get('/health')
    console.log('Backend status:', data.status) // "ok"
    return data.status === 'ok'
  } catch (err) {
    console.error('Backend unreachable:', err.message)
    return false
  }
}
```

### Upload and analyze a run

```js
async function analyzeRun(file) {
  const form = new FormData()
  form.append('file', file)

  try {
    const { data } = await API.post('/api/analyze', form)
    // data: { success, filename, analysis, run_id }
    return data
  } catch (err) {
    if (err.response) {
      const { status, data } = err.response
      if (status === 400) {
        // Invalid file — show data.detail to the user
        console.warn('Bad request:', data.detail)
      } else if (status === 422) {
        console.warn('Missing file field.')
      } else if (status === 502) {
        console.error('AI service error:', data.detail)
      } else {
        console.error('Server error:', data.detail)
      }
    } else {
      console.error('Network error:', err.message)
    }
    throw err
  }
}
```

### File input wiring (Vue 3 SFC)

```vue
<template>
  <input type="file" accept=".json" @change="onFileChange" />
</template>

<script setup>
import { ref } from 'vue'

const selectedFile = ref(null)

function onFileChange(event) {
  selectedFile.value = event.target.files[0]
}

async function submit() {
  if (!selectedFile.value) return
  const result = await analyzeRun(selectedFile.value)
  // Use result.analysis, result.run_id, etc.
}
</script>
```

---

## Local Development

```bash
# Terminal 1 — backend (from sp2-backend/)
uvicorn app.main:app --reload

# Terminal 2 — frontend (from sp2-frontend/)
npm run dev
```

- Backend listens on `http://localhost:8000`
- Frontend (Vite) runs on `http://localhost:5173`
- CORS is pre-configured for this pairing.
- Interactive API docs are available at `http://localhost:8000/docs`.

---

## Database

Runs are persisted to `sp2-backend/runs.db` (SQLite). The schema is auto-created on first request:

```sql
CREATE TABLE IF NOT EXISTS runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    filename   TEXT    NOT NULL,
    raw_json   TEXT,
    parsed_json TEXT,
    analysis   TEXT,
    created_at TEXT
);
```

No frontend interaction with the database is needed — all access goes through the API.
