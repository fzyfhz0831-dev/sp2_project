## Self-Check Report

**Run date:** 2026-06-03 09:16:16 UTC
**Result:** ✅ ALL PASSED

| Category       | Count |
|----------------|-------|
| ✅ Passed       | 51 |
| ❌ Failed       | 0 |
| 🔧 Fixed        | 0 |
| ❓ Manual check | 0 |

### ✅ Passed
- Valid JSON: mock_data/runs/mock-001-low-hp-elite.json
- Valid JSON: mock_data/runs/mock-002-thick-deck.json
- Valid JSON: mock_data/runs/mock-003-poor-defense.json
- Valid JSON: mock_data/runs/mock-004-low-scaling.json
- Valid JSON: mock_data/runs/mock-005-potion-unused.json
- Valid JSON: mock_data/runs/mock-006-boss-strategy.json
- Valid JSON: mock_data/runs/mock-007-greedy-path.json
- Valid JSON: mock_data/runs/mock-008-wrong-upgrade.json
- Valid JSON: mock_data/runs/mock-009-relic-synergy.json
- Valid JSON: mock_data/runs/mock-010-energy-curve.json
- Checked 10 mock run file(s)
- Valid JSON: knowledge_base/cards.json  (566 entries)
- Valid JSON: knowledge_base/characters.json  (5 entries)
- Valid JSON: knowledge_base/relics.json  (278 entries)
- Valid JSON: knowledge_base/status_effects.json  (257 entries)
- Checked 4 knowledge base file(s)
- knowledge_base/cards.json exists and is valid JSON
- knowledge_base/relics.json exists and is valid JSON
- knowledge_base/status_effects.json exists and is valid JSON
- knowledge_base/characters.json exists and is valid JSON
- wiki_scraper.py check complete
- generate_mock_runs.py produced 10 mock run file(s)
- Validated: mock-001-low-hp-elite.json
- Validated: mock-002-thick-deck.json
- Validated: mock-003-poor-defense.json
- Validated: mock-004-low-scaling.json
- Validated: mock-005-potion-unused.json
- Validated: mock-006-boss-strategy.json
- Validated: mock-007-greedy-path.json
- Validated: mock-008-wrong-upgrade.json
- Validated: mock-009-relic-synergy.json
- Validated: mock-010-energy-curve.json
- generate_mock_runs.py check complete
- run_parser.py CLI executed successfully
- prompt_builder.py CLI executed successfully with all keys
- mock_ai_analyzer.py CLI executed successfully with all keys
- Individual module CLI tests complete
- FastAPI server started
- GET /health → 200  {'status': 'ok'}
- GET /mode → 200  mode=mixed, real_run_count=5
- GET /mock-runs → 200  (10 runs)
- GET /analyze-mock-run/mock-001-low-hp-elite → 200 with analysis
- GET /analyze-mock-run/nonexistent → 404 (correct)
- FastAPI basic endpoint tests complete
- POST /upload-run → 200  run_id=run-ironclad-20260603-091627-6c8aef09
- POST /upload-run with .exe → 400 (correctly rejected)
- Upload sample real run check complete
- GET /real-runs → 200  (6 run(s))
- GET /analyze-real-run/run-ironclad-20260603-091627-6c8aef09 → 200  analyzer=mock
- GET /analyze-real-run/nonexistent → 404 (correct)
- Analyze real run endpoint check complete
