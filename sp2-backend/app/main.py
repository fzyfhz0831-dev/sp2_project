from __future__ import annotations

import json
import logging
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

logger = logging.getLogger("sp2.api")


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
        "https://spireinsight.uk",
        "https://www.spireinsight.uk",
        "https://sp2-project.pages.dev",
        "https://sp2-project-1.onrender.com",
        "https://sp2-project.onrender.com",
        "http://localhost:5173",
        "http://localhost:4173",
    ],
    allow_credentials=False,
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
    logger.info("Analyzing run: file=%r character=%r floor=%r",
                filename,
                uploaded_data.get("character") or "unknown",
                uploaded_data.get("floor_reached") or uploaded_data.get("floor") or "unknown")

    # ── Parse run data ──────────────────────────────────────────────────
    try:
        parsed_run = parse_run_data(uploaded_data)
    except RunParserError as error:
        logger.warning("Run parse error: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error

    logger.info("Parsed run: character=%r floor=%r",
                parsed_run.get("character"),
                parsed_run.get("floor_reached"))

    # ── Rule-based analysis ─────────────────────────────────────────────
    findings: dict[str, Any] = {
        "problems": [],
        "strengths": [],
        "warnings": [],
        "suggestions": [],
        "run_context": {
            "character": parsed_run.get("character", "Unknown"),
            "floor": parsed_run.get("floor_reached", 0),
            "boss": "Unknown",
            "deck_size": 0,
            "relic_count": 0,
            "victory": None,
        },
        "analysis_quality": "fallback",
    }
    rule_analyzer_failed = False
    try:
        findings = analyze_run_rules(parsed_run)
        logger.info("Rule analysis: %d problems, %d strengths, %d warnings, %d suggestions",
                    len(findings.get("problems", [])),
                    len(findings.get("strengths", [])),
                    len(findings.get("warnings", [])),
                    len(findings.get("suggestions", [])))
    except Exception as exc:
        rule_analyzer_failed = True
        logger.warning("Rule analyzer failed (continuing without): %s", exc)

    # ── Wiki knowledge lookup ───────────────────────────────────────────
    wiki_context: list[str] = []
    if character and death_location and main_problem:
        try:
            wiki_context = _lookup_wiki_knowledge(character, death_location, main_problem)
            logger.info("Wiki knowledge: %d entries matched", len(wiki_context))
        except Exception as exc:
            logger.warning("Wiki knowledge lookup failed (continuing without): %s", exc)

    # ── AI analysis ─────────────────────────────────────────────────────
    analysis: str = ""
    ai_failed = False
    try:
        analysis = analyze_run(parsed_run, findings, wiki_context=wiki_context)
        logger.info("AI analysis success: %d chars", len(analysis))
    except Exception as exc:
        ai_failed = True
        logger.warning("AI analysis failed, falling back to rule analyzer: %s", exc)
        # Build a rule-based fallback summary when AI is unavailable.
        from app.ai_service import _mock_analysis
        try:
            analysis = _mock_analysis(parsed_run, findings)
            logger.info("Fallback analysis generated: %d chars", len(analysis))
        except Exception as fallback_exc:
            logger.error("Even fallback analysis failed: %s", fallback_exc)
            analysis = f"Analysis unavailable. Rule-based findings: {json.dumps(findings, indent=2)}"

    # ── Persist to database ─────────────────────────────────────────────
    run_id: int | None = None
    try:
        run_id = save_run(
            filename=filename,
            raw_data=uploaded_data,
            parsed_data=parsed_run,
            analysis=analysis,
            summary_text=parsed_run.get("summary_text"),
        )
        logger.info("Run saved: id=%s", run_id)
    except DatabaseError as error:
        logger.error("Database error: %s", error)
        raise HTTPException(status_code=500, detail=f"Database error: {error}") from error
    except Exception as exc:
        logger.error("Unexpected database error (continuing without save): %s", exc)
        # Don't fail the entire request if DB save fails unexpectedly.

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
        "fallback_used": ai_failed or rule_analyzer_failed,
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
    logger.info("POST /api/analyze: file=%r character=%r deathLocation=%r mainProblem=%r",
                file.filename, character, deathLocation, mainProblem)

    # ── Validate file type ──────────────────────────────────────────────
    if not file.filename:
        logger.warning("No filename provided")
        raise HTTPException(status_code=400, detail="No file provided.")
    if not file.filename.lower().endswith(".json"):
        logger.warning("Invalid file type: %r", file.filename)
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a JSON file.")

    # ── Save uploaded file ──────────────────────────────────────────────
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    saved_path = UPLOAD_DIR / safe_name

    try:
        with saved_path.open("wb") as output_file:
            shutil.copyfileobj(file.file, output_file)
        logger.info("File saved: %r (%d bytes)", safe_name, saved_path.stat().st_size)
    except OSError as error:
        logger.error("Could not save uploaded file: %s", error)
        raise HTTPException(status_code=500, detail="Could not save uploaded file.") from error
    finally:
        await file.close()

    # ── Parse uploaded JSON ─────────────────────────────────────────────
    try:
        raw_text = saved_path.read_text(encoding="utf-8-sig")
        uploaded_data = json.loads(raw_text)
    except json.JSONDecodeError as error:
        logger.warning("Invalid JSON: %s", error)
        raise HTTPException(status_code=400, detail="Invalid JSON file.") from error
    except OSError as error:
        logger.error("Could not read uploaded file: %s", error)
        raise HTTPException(status_code=500, detail="Could not read uploaded file.") from error

    # ── Analyze (top-level safety net) ──────────────────────────────────
    try:
        return _analyze_and_save_run(
            safe_name,
            uploaded_data,
            character=character,
            death_location=deathLocation,
            main_problem=mainProblem,
        )
    except HTTPException:
        # Re-raise FastAPI HTTP exceptions so they keep their status codes.
        raise
    except Exception as exc:
        logger.exception("Unhandled error in /api/analyze: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during analysis. The service is recovering — please try again.",
        ) from exc

