from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def find_project_root() -> Path:
    current = Path(__file__).resolve().parent

    for path in (current, *current.parents):
        if (path / "backend").is_dir() or (path / "frontend").is_dir():
            return path

    return current.parent


def main() -> int:
    print("[INFO] Starting automation program...")

    project_root = find_project_root()
    backend_script = project_root / "backend" / "collect_data.py"
    frontend_dir = project_root / "frontend"
    generated_json = project_root / "run_insights.json"
    frontend_json = frontend_dir / "run_insights.json"

    print("[INFO] Checking project structure...")
    if not backend_script.is_file():
        print("[ERROR] backend/collect_data.py not found")
        return 1

    if not frontend_dir.is_dir():
        print("[ERROR] frontend directory not found")
        return 1

    print("[INFO] Running backend data script...")
    result = subprocess.run(
        [sys.executable, str(backend_script)],
        cwd=project_root,
        check=False,
    )
    if result.returncode != 0:
        print("[ERROR] backend data script failed")
        return 1

    print("[INFO] Checking generated JSON...")
    if not generated_json.is_file():
        print("[ERROR] run_insights.json not generated")
        return 1

    print("[INFO] Copying JSON to frontend...")
    shutil.copy2(generated_json, frontend_json)

    print("[SUCCESS] Automation pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
