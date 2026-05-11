#!/usr/bin/env python3
"""Reset local demo data by removing the isolated demo database file."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DB_PATH = REPO_ROOT / "demo" / "demo.sqlite3"
DEFAULT_URL = f"sqlite:///{DEMO_DB_PATH}"


def _path_from_sqlite_url(url: str) -> Path:
    if not url.startswith("sqlite:///"):
        raise ValueError("reset_demo_data.py only supports sqlite:/// URLs")
    db_path = Path(url.replace("sqlite:///", "", 1)).resolve()
    demo_root = (REPO_ROOT / "demo").resolve()
    allow_any_delete = os.environ.get("JTA_DEMO_ALLOW_DB_DELETE", "0") == "1"

    if not allow_any_delete:
        try:
            db_path.relative_to(demo_root)
        except ValueError as exc:
            raise ValueError(
                f"refusing to delete non-demo database path: {db_path}. "
                "Set JTA_DEMO_ALLOW_DB_DELETE=1 to override explicitly."
            ) from exc
    return db_path


def main() -> int:
    db_url = os.environ.get("JTA_DATABASE_URL", DEFAULT_URL)
    db_path = _path_from_sqlite_url(db_url)

    if db_path.exists():
        db_path.unlink()
        print(f"Removed demo database: {db_path}")
    else:
        print(f"Demo database not found (already reset): {db_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
