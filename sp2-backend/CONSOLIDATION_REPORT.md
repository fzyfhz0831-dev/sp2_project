# SP2 Backend Consolidation Report

**Date:** 2026-06-03  
**Task:** Consolidate all backend files into `sp2-backend/`

---

## 1. Final Folder Structure

```
sp2-backend/
├── app/                          # All Python modules (the backend package)
│   ├── __init__.py               # Package marker
│   ├── main.py                   # FastAPI entry point (uvicorn app.main:app)
│   ├── config.py                 # App-level config (BASE_DIR, UPLOAD_DIR, DATABASE_PATH)
│   ├── pipeline_config.py        # Pipeline config (was backend/config.py, renamed)
│   ├── ai_service.py             # AI analysis service (mock)
│   ├── db_service.py             # SQLite database operations
│   ├── run_parser.py             # API run parser (parse_run_data)
│   ├── run_parser_full.py        # Full run parser (was backend/run_parser.py, renamed)
│   ├── alerts.py                 # Alert/email notifications
│   ├── collect_data.py           # Data collection orchestrator
│   ├── data_cleaner.py           # Data cleaning & archiving
│   ├── data_mode.py              # Data mode tracker (mock/real/mixed)
│   ├── generate_mock_runs.py     # Mock run generator
│   ├── health_check.py           # Pipeline health checks
│   ├── log_analyzer.py           # Log analysis utilities
│   ├── loss_classifier.py        # Run loss classifier
│   ├── mock_ai_analyzer.py       # Mock AI analyzer
│   ├── official_news_collector.py
│   ├── prompt_builder.py         # AI prompt builder
│   ├── recommendation_generator.py
│   ├── reddit_collector.py       # Reddit data collector
│   ├── reddit_comments_collector.py
│   ├── report_generator.py       # Report generation
│   ├── run_analyzer.py           # Run analysis engine
│   ├── run_converter.py          # Upload format converter
│   ├── self_check.py             # Self-check script
│   ├── steam_collector.py        # Steam data collector
│   ├── steam_news_collector.py
│   ├── steam_reviews_collector.py
│   ├── utils.py                  # Shared utilities (logging, JSON, retry)
│   └── wiki_scraper.py           # Wiki data scraper
├── data/                         # Runtime data
│   ├── mode.json
│   └── processed_runs/           # Processed player runs
├── mock_data/                    # Mock run fixtures
│   ├── knowledge_base/           # Cards, relics, characters, status effects
│   └── runs/                     # 10 mock run scenarios
├── archive/                      # Archive storage
├── logs/                         # Log output directory
├── uploads/                      # Uploaded run files
│   ├── sample.json
│   ├── .gitkeep
│   └── runs/                     # Raw uploaded files
├── runs.db                       # SQLite database
├── requirements.txt
├── .env.example
└── README.md
```

---

## 2. Files Moved

### 2.1 Copied from `backend/` → `sp2-backend/app/` (non-conflicting)
| Source | Destination |
|---|---|
| `backend/__init__.py` | `app/__init__.py` |
| `backend/alerts.py` | `app/alerts.py` |
| `backend/collect_data.py` | `app/collect_data.py` |
| `backend/data_cleaner.py` | `app/data_cleaner.py` |
| `backend/data_mode.py` | `app/data_mode.py` |
| `backend/generate_mock_runs.py` | `app/generate_mock_runs.py` |
| `backend/health_check.py` | `app/health_check.py` |
| `backend/log_analyzer.py` | `app/log_analyzer.py` |
| `backend/loss_classifier.py` | `app/loss_classifier.py` |
| `backend/mock_ai_analyzer.py` | `app/mock_ai_analyzer.py` |
| `backend/official_news_collector.py` | `app/official_news_collector.py` |
| `backend/prompt_builder.py` | `app/prompt_builder.py` |
| `backend/recommendation_generator.py` | `app/recommendation_generator.py` |
| `backend/reddit_collector.py` | `app/reddit_collector.py` |
| `backend/reddit_comments_collector.py` | `app/reddit_comments_collector.py` |
| `backend/report_generator.py` | `app/report_generator.py` |
| `backend/run_analyzer.py` | `app/run_analyzer.py` |
| `backend/run_converter.py` | `app/run_converter.py` |
| `backend/self_check.py` | `app/self_check.py` |
| `backend/steam_collector.py` | `app/steam_collector.py` |
| `backend/steam_news_collector.py` | `app/steam_news_collector.py` |
| `backend/steam_reviews_collector.py` | `app/steam_reviews_collector.py` |
| `backend/utils.py` | `app/utils.py` |
| `backend/wiki_scraper.py` | `app/wiki_scraper.py` |

### 2.2 Renamed to avoid conflicts
| Source | Destination | Reason |
|---|---|---|
| `backend/config.py` | `app/pipeline_config.py` | Conflicts with `app/config.py` (different purposes) |
| `backend/run_parser.py` | `app/run_parser_full.py` | Conflicts with `app/run_parser.py` (different APIs) |
| `backend/main.py` | *(not copied)* | Duplicate API server; `app/main.py` is the canonical entry point |

### 2.3 Data directories moved from `backend/` → `sp2-backend/`
| Source | Destination |
|---|---|
| `backend/data/` | `sp2-backend/data/` |
| `backend/mock_data/` | `sp2-backend/mock_data/` |
| `backend/uploads/runs/` | `sp2-backend/uploads/runs/` |
| `backend/archive/` | `sp2-backend/archive/` |
| `backend/logs/` | `sp2-backend/logs/` |

### 2.4 Deleted duplicates
| File/Directory | Reason |
|---|---|
| `backend/` (entire directory) | All files consolidated into `sp2-backend/app/` |
| `api_server.py` (root) | Older API server; replaced by `app/main.py` |
| `sp2-backend/sp2_backend.sqlite` | Replaced by `sp2-backend/runs.db` |

---

## 3. Import Path Changes

### Pattern: `from backend.xxx import ...` → `from app.xxx import ...`

| Old Import | New Import | Files Affected |
|---|---|---|
| `from backend.config import ...` | `from app.pipeline_config import ...` | 16 files (all pipeline modules) |
| `from backend.utils import ...` | `from app.utils import ...` | 16 files |
| `from backend.alerts import ...` | `from app.alerts import ...` | 11 files |
| `from backend.run_parser import ...` | `from app.run_parser_full import ...` | 3 files (mock_ai_analyzer, prompt_builder, self_check) |

### Fallback import fixes (bare → app-prefixed)
| Old Fallback | New Fallback | Files Affected |
|---|---|---|
| `from config import ...` | `from app.pipeline_config import ...` | 16 files |
| `from utils import ...` | `from app.utils import ...` | 16 files |
| `from alerts import ...` | `from app.alerts import ...` | 11 files |
| `from run_parser import ...` | `from app.run_parser_full import ...` | 3 files |
| `from data_mode import ...` | `from app.data_mode import ...` | 1 file (main.py old) |
| `from mock_ai_analyzer import ...` | `from app.mock_ai_analyzer import ...` | 1 file (main.py old) |
| `from run_converter import ...` | `from app.run_converter import ...` | 1 file (main.py old) |

### Path reference fixes (non-import structural fixes)
| File | Old | New |
|---|---|---|
| `app/data_mode.py` | `Path(__file__).resolve().parent / "data"` | `Path(__file__).resolve().parents[1] / "data"` |
| `app/run_parser_full.py` | `Path(__file__).resolve().parent / "mock_data"` | `Path(__file__).resolve().parents[1] / "mock_data"` |
| `app/config.py` | `DATABASE_PATH = BASE_DIR / "sp2_backend.sqlite"` | `DATABASE_PATH = BASE_DIR / "runs.db"` |

---

## 4. Potential Import Conflicts & Notes

### 4.1 Two config modules
- **`app/config.py`** — Lightweight app config: `BASE_DIR`, `UPLOAD_DIR`, `DATABASE_PATH`
- **`app/pipeline_config.py`** — Full pipeline config: `PROJECT_ROOT`, `DATA_DIR`, `LOGS_DIR`, `PIPELINE_LOG_PATH`, API keys, thresholds, etc.
- Both use `parents[1]` → resolve to `sp2-backend/` ✓
- No import conflict; modules import from the correct config based on their needs

### 4.2 Two run_parser modules
- **`app/run_parser.py`** — API-oriented: `parse_run_data()` used by `app/main.py`
- **`app/run_parser_full.py`** — Analysis-oriented: `load_run()`, `validate_run()`, `summarize_run()` used by pipeline modules
- Different function signatures; kept as separate files to avoid breaking either consumer

### 4.3 `self_check.py` has hardcoded `backend.` references (non-import)
- Line 9: docstring example `python backend/self_check.py`
- Line 41: `_BACKEND = _PROJECT / "backend"` (path variable)
- Line 441: subprocess call `uvicorn backend.main:app`
- These are runtime/documentation references, not import paths. They were left as-is per the constraint. The self-check script will need updating if run from the new structure.

### 4.4 Root-level files preserved
- `Dockerfile` — kept at project root
- `self_check_run_review.py` — standalone, no backend imports
- `frontend/` — old frontend directory (separate from `sp2-frontend/`)

---

## 5. Verification Results

### 5.1 App Import
```bash
$ cd sp2-backend && python -c "from app.main import app; print(app.title)"
SP2 Backend
```
✅ Pass

### 5.2 `/health` Endpoint
```bash
$ curl http://127.0.0.1:8000/health
{"status":"ok"}
```
✅ HTTP 200

### 5.3 `/api/analyze` Endpoint
```bash
$ curl -X POST http://127.0.0.1:8000/api/analyze \
  -F "file=@uploads/sample.json;type=application/json"
{
  "success": true,
  "filename": "sample.json",
  "analysis": "Ironclad reached floor 12 against Guardian. ...",
  "run_id": 1
}
```
✅ HTTP 200 — analysis returned, run saved to `runs.db`

### 5.4 Database
- **Location:** `sp2-backend/runs.db` ✅
- **Schema:** Created by `app/db_service.py` on first `.save_analysis()` call

### 5.5 Run Command
```bash
uvicorn app.main:app --reload
```
✅ Works from `sp2-backend/` directory

---

## 6. `sp2-frontend` Status

The `sp2-frontend/` directory is preserved separately at the project root level:
```
sp2-frontend/
├── dist/
├── src/
│   ├── App.vue
│   ├── main.js
│   └── views/
├── index.html
├── package.json
├── package-lock.json
└── vite.config.js
```
Ready for future Vue integration. Not modified during consolidation.
