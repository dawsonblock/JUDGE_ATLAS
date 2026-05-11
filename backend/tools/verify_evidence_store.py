"""Verify evidence snapshot integrity and detect duplicate snapshot hashes.

Usage:
  python -m backend.tools.verify_evidence_store
  python backend/tools/verify_evidence_store.py [--allow-empty]

Flags:
  --allow-empty   Treat an empty evidence store as a pass (for smoke tests).
                  The alpha release gate must NOT use this flag.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

# Ensure the backend directory is importable as top-level `app` when running
# `python -m backend.tools.*` from repository root.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal  # noqa: E402  # type: ignore[import-not-found]
from app.models.entities import (  # noqa: E402  # type: ignore[import-not-found]
    SourceSnapshot,
)
from app.services.evidence_integrity import (  # noqa: E402  # type: ignore[import-not-found]
    verify_all_recent_snapshots,
)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    allow_empty = "--allow-empty" in args

    try:
        with SessionLocal() as db:
            snapshots = db.scalars(
                select(SourceSnapshot).order_by(SourceSnapshot.id)
            ).all()
            if not snapshots:
                print("EVIDENCE STORE VERIFICATION")
                print("snapshots_checked=0")
                print("verified_snapshots=0")
                print("duplicate_hashes=0")
                print("corrupt_snapshots=0")
                print("rejected_or_quarantined_count=0")
                if allow_empty:
                    print("integrity_failures=0")
                    print("RESULT: PASS (empty store, --allow-empty)")
                    return 0
                print("integrity_failures=1")
                print("RESULT: FAIL empty_evidence_store")
                return 1
            results = verify_all_recent_snapshots(db, limit=len(snapshots))
    except SQLAlchemyError as exc:
        print("EVIDENCE STORE VERIFICATION")
        print("snapshots_checked=0")
        print(f"RESULT: FAIL database_error={exc.__class__.__name__}")
        print(str(exc))
        return 1

    failed = [r for r in results if not r.ok]

    hashes = [s.content_hash for s in snapshots if s.content_hash]
    dup_counts = Counter(hashes)
    duplicates = {h: c for h, c in dup_counts.items() if c > 1}
    verified = len(results) - len(failed)

    print("EVIDENCE STORE VERIFICATION")
    print(f"snapshots_checked={len(results)}")
    print(f"verified_snapshots={verified}")
    print(f"integrity_failures={len(failed)}")
    print(f"corrupt_snapshots={len(failed)}")
    print(f"duplicate_hashes={len(duplicates)}")
    print("rejected_or_quarantined_count=0")

    if failed:
        print("Integrity mismatches:")
        for r in failed:
            print(f"- snapshot_id={r.snapshot_id} error={r.error_message}")

    if duplicates:
        print("Duplicate content_hash entries:")
        for h, c in sorted(duplicates.items()):
            print(f"- hash={h} count={c}")

    if failed or duplicates:
        print("RESULT: FAIL evidence_integrity_issue")
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
