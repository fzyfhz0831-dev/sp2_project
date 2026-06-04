# Batch Run Final Report

## Source

Batch run JSON discovery was performed under:

`sp2-automatic/`

Only JSON objects with run-like fields were uploaded. Archived insight payloads, collector outputs, and non-run JSON files were excluded.

## Files uploaded

| File | HTTP status | Result | Run ID |
| --- | ---: | --- | ---: |
| `sp2-automatic/data/normalized_run.json` | 200 | Success | 5 |
| `sp2-automatic/data/player_run.example.json` | 200 | Success | 6 |
| `sp2-automatic/data/player_run.json` | 200 | Success | 7 |

## Summary

- Run JSON files detected: 3
- Upload successes: 3
- Upload failures: 0
- Database rows before batch: 4
- Database rows after batch: 7

## Upload destination

Confirmed saved uploads:

- `sp2-backend/app/uploads/normalized_run.json`
- `sp2-backend/app/uploads/player_run.example.json`
- `sp2-backend/app/uploads/player_run.json`

## Final status

PASS
