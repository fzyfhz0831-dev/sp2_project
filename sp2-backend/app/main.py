from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.ai_service import analyze_run
from app.config import APP_DIR, UPLOAD_DIR
from app.db_service import DatabaseError, get_run, init_db, list_runs, save_run
from app.rule_analyzer import analyze_run_rules
from app.run_parser import RunParserError, parse_run_data


# ---------------------------------------------------------------------------
# Wiki knowledge — loaded once at startup and reused across requests.
# ---------------------------------------------------------------------------

_WIKI_KNOWLEDGE_PATH = APP_DIR.parent / "data" / "wiki_knowledge.json"

_wiki_knowledge_cache: dict[str, Any] | None = None


def _load_wiki_knowledge() -> dict[str, Any]:
    """Load wiki_knowledge.json from the data directory, caching in memory."""
    global _wiki_knowledge_cache
    if _wiki_knowledge_cache is not None:
        return _wiki_knowledge_cache
    try:
        raw = _WIKI_KNOWLEDGE_PATH.read_text(encoding="utf-8")
        _wiki_knowledge_cache = json.loads(raw)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        _wiki_knowledge_cache = {}
    return _wiki_knowledge_cache


def _lookup_wiki_knowledge(character: str, death_location: str, main_problem: str) -> list[str]:
    """Return related knowledge entries matching the given triple."""
    wiki = _load_wiki_knowledge()
    knowledge_map: list[dict[str, Any]] = wiki.get("knowledge_map", [])
    for entry in knowledge_map:
        if (
            entry.get("character") == character
            and entry.get("deathLocation") == death_location
            and entry.get("mainProblem") == main_problem
        ):
            return entry.get("relatedKnowledge", [])
    return []



app = FastAPI(title="SP2 Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sp2-project-1.onrender.com",
        "https://sp2-project.onrender.com",
        "http://localhost:5173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _analyze_and_save_run(
    filename: str,
    uploaded_data: dict[str, Any],
    character: str = "",
    death_location: str = "",
    main_problem: str = "",
) -> dict[str, Any]:
    try:
        parsed_run = parse_run_data(uploaded_data)
    except RunParserError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    # Rule-based analysis — runs before AI to get structured findings.
    findings = analyze_run_rules(parsed_run)

    # Look up wiki knowledge if the frontend provided selections.
    wiki_context: list[str] = []
    if character and death_location and main_problem:
        wiki_context = _lookup_wiki_knowledge(character, death_location, main_problem)

    try:
        analysis = analyze_run(parsed_run, findings, wiki_context=wiki_context)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=f"AI API error: {error}") from error

    try:
        run_id = save_run(
            filename=filename,
            raw_data=uploaded_data,
            parsed_data=parsed_run,
            analysis=analysis,
            summary_text=parsed_run.get("summary_text"),
        )
    except DatabaseError as error:
        raise HTTPException(status_code=500, detail=f"Database error: {error}") from error

    return {
        "success": True,
        "filename": filename,
        "summary_text": parsed_run.get("summary_text"),
        "analysis": analysis,
        "run_id": run_id,
        "findings": findings,
        "character": character or None,
        "deathLocation": death_location or None,
        "mainProblem": main_problem or None,
        "wikiContext": wiki_context or None,
    }


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/runs")
def runs(limit: int = 50) -> dict[str, Any]:
    try:
        return {"success": True, "runs": list_runs(limit)}
    except DatabaseError as error:
        raise HTTPException(status_code=500, detail=f"Database error: {error}") from error


@app.get("/api/runs/{run_id}")
def run_detail(run_id: int) -> dict[str, Any]:
    try:
        run = get_run(run_id)
    except DatabaseError as error:
        raise HTTPException(status_code=500, detail=f"Database error: {error}") from error

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    return {"success": True, "run": run}


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    character: str = Form(""),
    deathLocation: str = Form(""),
    mainProblem: str = Form(""),
) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JSON file.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    saved_path = UPLOAD_DIR / safe_name

    try:
        with saved_path.open("wb") as output_file:
            shutil.copyfileobj(file.file, output_file)
    except OSError as error:
        raise HTTPException(status_code=500, detail="Could not save uploaded file.") from error
    finally:
        await file.close()

    try:
        raw_text = saved_path.read_text(encoding="utf-8-sig")
        uploaded_data = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=400, detail="Invalid JSON file.") from error
    except OSError as error:
        raise HTTPException(status_code=500, detail="Could not read uploaded file.") from error

    return _analyze_and_save_run(
        safe_name,
        uploaded_data,
        character=character,
        death_location=deathLocation,
        main_problem=mainProblem,
    )

