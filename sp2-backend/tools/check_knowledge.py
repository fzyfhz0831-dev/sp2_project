"""
check_knowledge.py — Validate and normalize gameplay knowledge JSON files.

Usage:
  python tools/check_knowledge.py [--fix] [--dir app/knowledge]

Without --fix: validates and reports issues only.
With --fix:    also normalizes missing fields with safe defaults.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


# ── Expected files ──────────────────────────────────────────────────────────

EXPECTED_FILES: tuple[str, ...] = (
    "cards.json",
    "relics.json",
    "bosses.json",
    "archetypes.json",
)

# ── Required and recommended fields ─────────────────────────────────────────

REQUIRED_FIELDS: tuple[str, ...] = ("name",)

RECOMMENDED_FIELDS: tuple[str, ...] = (
    "type",             # or "category" — will normalize to "type"
    "strengths",
    "weaknesses",
    "synergy_tags",
    "scaling_notes",
    "risk_notes",
    "recommended_situations",
)

# ── Safe defaults for each recommended field ────────────────────────────────

FIELD_DEFAULTS: dict[str, Any] = {
    "type": "unknown",
    "strengths": [],
    "weaknesses": [],
    "synergy_tags": [],
    "scaling_notes": "",
    "risk_notes": "",
    "recommended_situations": [],
}


# ── Normalize routines ──────────────────────────────────────────────────────


def _normalize_entry(entry: dict[str, Any], entry_index: int) -> dict[str, Any]:
    """Fill missing recommended fields with safe defaults.

    Also normalises ``category`` → ``type`` when present.
    """
    # Normalize category -> type
    if "category" in entry and "type" not in entry:
        entry["type"] = entry.pop("category")
    elif "category" in entry and entry.get("type") in (None, "unknown"):
        entry["type"] = entry.pop("category")

    for field, default in FIELD_DEFAULTS.items():
        if field not in entry:
            entry[field] = default
        elif entry[field] is None:
            entry[field] = default
        elif isinstance(default, list) and not isinstance(entry[field], list):
            entry[field] = [str(entry[field])]
        elif isinstance(default, str) and not isinstance(entry[field], str):
            entry[field] = str(entry[field])

    return entry


def _normalize_file(path: Path) -> tuple[int, int]:
    """Normalize all entries in one knowledge file.

    Returns (total_entries, fixed_entries).
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    fixed = 0

    if isinstance(data, list):
        for i, entry in enumerate(data):
            if isinstance(entry, dict):
                before = set(entry.keys())
                _normalize_entry(entry, i)
                after = set(entry.keys())
                if after - before:
                    fixed += 1

    elif isinstance(data, dict):
        for group_key, entries in data.items():
            if isinstance(entries, list):
                for i, entry in enumerate(entries):
                    if isinstance(entry, dict):
                        before = set(entry.keys())
                        _normalize_entry(entry, i)
                        after = set(entry.keys())
                        if after - before:
                            fixed += 1

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return _count_entries(data), fixed


def _count_entries(data: Any) -> int:
    """Count total entries across list or dict-of-lists."""
    if isinstance(data, list):
        return sum(1 for e in data if isinstance(e, dict))
    if isinstance(data, dict):
        total = 0
        for v in data.values():
            if isinstance(v, list):
                total += sum(1 for e in v if isinstance(e, dict))
        return total
    return 0


# ── Validation ──────────────────────────────────────────────────────────────


def _validate_file(path: Path) -> dict[str, Any]:
    """Validate one knowledge file; return a report dict."""
    report: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "valid_json": False,
        "total_entries": 0,
        "container_type": "unknown",
        "missing_required": [],
        "missing_recommended": defaultdict(int),
        "malformed_entries": 0,
        "fixable": 0,
        "errors": [],
    }

    if not report["exists"]:
        report["errors"].append("File not found")
        return report

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report["errors"].append(f"Malformed JSON: {exc}")
        return report

    report["valid_json"] = True
    report["container_type"] = type(data).__name__

    entries: list[tuple[int, dict[str, Any]]] = []

    if isinstance(data, list):
        for i, entry in enumerate(data):
            if isinstance(entry, dict):
                entries.append((i, entry))
            else:
                report["malformed_entries"] += 1
    elif isinstance(data, dict):
        for group_key, sub_list in data.items():
            if isinstance(sub_list, list):
                for i, entry in enumerate(sub_list):
                    if isinstance(entry, dict):
                        entries.append((i, entry))
                    else:
                        report["malformed_entries"] += 1
    else:
        report["errors"].append(f"Unexpected top-level type: {type(data).__name__}")
        return report

    report["total_entries"] = len(entries)

    for idx, entry in entries:
        # Required fields
        for field in REQUIRED_FIELDS:
            val = entry.get(field)
            if val is None or val == "":
                report["missing_required"].append(f"entry[{idx}].{field}")

        # Recommended fields
        for field in RECOMMENDED_FIELDS:
            if field == "type":
                # Accept either "type" or "category"
                if "type" not in entry and "category" not in entry:
                    report["missing_recommended"]["type (or category)"] += 1
                    report["fixable"] += 1
            else:
                if field not in entry:
                    report["missing_recommended"][field] += 1
                    report["fixable"] += 1
                elif entry[field] is None:
                    report["missing_recommended"][field] += 1
                    report["fixable"] += 1

    # Convert defaultdict to plain dict for printing
    report["missing_recommended"] = dict(report["missing_recommended"])

    return report


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and optionally normalize knowledge JSON files."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Normalize missing fields with safe defaults (writes files in-place).",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "app" / "knowledge",
        help="Path to the knowledge directory.",
    )
    args = parser.parse_args()

    knowledge_dir: Path = args.dir.resolve()
    if not knowledge_dir.is_dir():
        print(f"ERROR: knowledge directory not found: {knowledge_dir}")
        return 1

    print(f"Checking knowledge files in: {knowledge_dir}\n")

    # ── Check for missing files ──────────────────────────────────────────
    missing_files = [f for f in EXPECTED_FILES if not (knowledge_dir / f).exists()]
    if missing_files:
        print("MISSING FILES:")
        for f in missing_files:
            print(f"  - {f}")
        print()

    # ── Validate every expected file ─────────────────────────────────────
    all_ok = True
    total_fixable = 0
    total_entries_all = 0

    for filename in EXPECTED_FILES:
        file_path = knowledge_dir / filename
        report = _validate_file(file_path)

        status_icon = "PASS" if report["valid_json"] and not report["errors"] and not report["missing_required"] else "WARN"
        if not report["exists"]:
            status_icon = "FAIL"

        print(f"[{status_icon}] {filename}")
        print(f"       Container: {report['container_type']}")
        print(f"       Entries:   {report['total_entries']}")
        total_entries_all += report["total_entries"]

        if report["errors"]:
            for err in report["errors"]:
                print(f"       ERROR: {err}")
                all_ok = False

        if report["malformed_entries"]:
            print(f"       MALFORMED: {report['malformed_entries']} entries are not dicts")
            all_ok = False

        if report["missing_required"]:
            print(f"       MISSING REQUIRED ({len(report['missing_required'])}):")
            for issue in report["missing_required"][:10]:
                print(f"         - {issue}")
            all_ok = False

        if report["missing_recommended"]:
            print(f"       MISSING RECOMMENDED:")
            for field, count in sorted(report["missing_recommended"].items()):
                print(f"         - {field}: missing in {count} entries")

        total_fixable += report["fixable"]
        print()

    # ── Optional fix pass ────────────────────────────────────────────────
    if args.fix:
        print("─" * 50)
        print("Normalizing missing fields with safe defaults...\n")
        for filename in EXPECTED_FILES:
            file_path = knowledge_dir / filename
            if not file_path.exists():
                print(f"  SKIP {filename} — file missing, cannot fix")
                continue
            total, fixed = _normalize_file(file_path)
            if fixed:
                print(f"  FIXED {filename}: {fixed}/{total} entries normalized")
            else:
                print(f"  OK   {filename}: no fixes needed")
        print()
        print("Normalization complete. Re-run without --fix to verify.")
    elif total_fixable > 0:
        print(f"Total fixable issues: {total_fixable}")
        print("Run with --fix to normalize missing fields automatically.")

    # ── Final summary ────────────────────────────────────────────────────
    print("─" * 50)
    print(f"Files expected:  {len(EXPECTED_FILES)}")
    print(f"Files present:   {len(EXPECTED_FILES) - len(missing_files)}")
    print(f"Files missing:   {len(missing_files)}")
    print(f"Total entries:   {total_entries_all}")
    print(f"Fixable issues:  {total_fixable}")
    print(f"Overall status:  {'ALL OK' if all_ok and not missing_files else 'ISSUES FOUND'}")

    return 0 if (all_ok and not missing_files and total_fixable == 0) else (0 if total_fixable > 0 else 0)


if __name__ == "__main__":
    raise SystemExit(main())
