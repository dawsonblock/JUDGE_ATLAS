#!/usr/bin/env python3
"""Seed the proof database (artifacts/proof/current/proof.db) with
representative audit and evidence records for meaningful non-empty verification.

This script:
1. Runs Alembic migrations against the proof DB (SQLite).
2. Seeds >= 3 chained AuditLog rows with all chain-v2 hash fields.
3. Seeds >= 3 SourceSnapshot rows (verified, rejected, quarantined).

The release gate must run this BEFORE verify_audit_chain and
verify_evidence_store so that both tools see non-empty data and
entries_checked > 0 / snapshots_checked > 0.

Usage:
    python scripts/prepare_proof_db.py [--proof-db PATH]
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
PROOF_DIR = REPO_ROOT / "artifacts" / "proof" / "current"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

GENESIS_HASH = "GENESIS"


def _sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def _payload_hash(payload: dict | None) -> str:
    canonical = json.dumps(payload or {}, sort_keys=True, default=str)
    return _sha256(canonical.encode())


def _row_digest(row_dict: dict, prev_hash: str) -> str:
    """Compute chain-v2 entry_hash from a row dictionary (mirrors chain_digest.row_digest)."""
    payload_hash = row_dict.get("payload_hash")
    ts = row_dict.get("created_at")
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts = ts.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")
    canonical = json.dumps(
        {
            "id": row_dict["id"],
            "action": row_dict["action"],
            "actor_id": row_dict["actor_id"],
            "actor_role": row_dict.get("actor_role"),
            "actor_auth_method": row_dict.get("actor_auth_method"),
            "entity_type": row_dict.get("entity_type"),
            "entity_id": row_dict.get("entity_id"),
            "payload_hash": payload_hash,
            "before_hash": row_dict.get("before_hash"),
            "after_hash": row_dict.get("after_hash"),
            "created_at": ts,
            "chain_version": row_dict.get("chain_version", 2),
            "prev": prev_hash,
        },
        sort_keys=True,
        default=str,
    )
    return _sha256(canonical.encode())


def _snapshot_hash(content: bytes) -> str:
    return _sha256(content)


def run_migrations(proof_db_url: str) -> int:
    """Apply Alembic migrations to the proof SQLite DB."""
    env = {**os.environ, "JTA_DATABASE_URL": proof_db_url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Migration failed:")
        print(result.stdout)
        print(result.stderr)
    return result.returncode


def seed_audit_chain(db_url: str) -> None:
    """Seed >= 3 chained AuditLog rows using SQLAlchemy."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(db_url, echo=False)
    with Session(engine) as db:
        from app.models.entities import AuditLog

        # Remove any existing seed entries (idempotent)
        db.query(AuditLog).filter(AuditLog.actor_id == "proof-seed").delete()
        db.commit()

        now = datetime.now(timezone.utc)
        prev_hash = GENESIS_HASH
        payloads = [
            {
                "action": "source.created",
                "entity_type": "SourceRegistry",
                "entity_id": "seed-source-001",
                "actor_id": "proof-seed",
                "actor_role": "admin",
                "actor_auth_method": "jwt",
                "payload": {"source_key": "seed-source-001", "source_class": "machine_ingest"},
                "before_hash": None,
                "after_hash": _sha256(b"seed-source-001"),
            },
            {
                "action": "ingestion.run.completed",
                "entity_type": "IngestionRun",
                "entity_id": "ingestion-run-001",
                "actor_id": "proof-seed",
                "actor_role": "system",
                "actor_auth_method": "internal",
                "payload": {"run_id": "ingestion-run-001", "status": "completed", "persisted_count": 1},
                "before_hash": _sha256(b"run-pending"),
                "after_hash": _sha256(b"run-completed"),
            },
            {
                "action": "review.approved",
                "entity_type": "ReviewItem",
                "entity_id": "review-item-001",
                "actor_id": "proof-seed",
                "actor_role": "reviewer",
                "actor_auth_method": "jwt",
                "payload": {"review_id": "review-item-001", "decision": "approved"},
                "before_hash": _sha256(b"review-pending"),
                "after_hash": _sha256(b"review-approved"),
            },
        ]

        for i, p in enumerate(payloads, start=1):
            ph = _payload_hash(p["payload"])
            ts = now + timedelta(seconds=i)
            # Build a temporary dict to compute entry_hash
            row_dict = {
                "id": None,   # placeholder; filled after flush
                "action": p["action"],
                "entity_type": p["entity_type"],
                "entity_id": p["entity_id"],
                "actor_id": p["actor_id"],
                "actor_role": p["actor_role"],
                "actor_auth_method": p["actor_auth_method"],
                "payload_hash": ph,
                "before_hash": p["before_hash"],
                "after_hash": p["after_hash"],
                "created_at": ts,
                "chain_version": 2,
            }

            entry = AuditLog(
                action=p["action"],
                entity_type=p["entity_type"],
                entity_id=p["entity_id"],
                actor_id=p["actor_id"],
                actor_type="user",
                actor_role=p["actor_role"],
                actor_auth_method=p["actor_auth_method"],
                payload=p["payload"],
                created_at=ts,
                payload_hash=ph,
                before_hash=p["before_hash"],
                after_hash=p["after_hash"],
                previous_entry_hash=prev_hash,
                chain_version=2,
            )
            db.add(entry)
            db.flush()  # assign entry.id

            # Now compute entry_hash with real id
            row_dict["id"] = entry.id
            entry.entry_hash = _row_digest(row_dict, prev_hash)
            db.flush()

            prev_hash = entry.entry_hash

        db.commit()
        print(f"  Seeded {len(payloads)} audit chain entries (chain_version=2)")


def seed_evidence_snapshots(db_url: str) -> None:
    """Seed >= 3 SourceSnapshot rows for meaningful evidence verification."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(db_url, echo=False)
    with Session(engine) as db:
        from app.models.entities import SourceSnapshot

        # Idempotent — remove previous seed snapshots
        db.query(SourceSnapshot).filter(
            SourceSnapshot.source_key == "proof-seed"
        ).delete()
        db.commit()

        now = datetime.now(timezone.utc)
        snapshots = [
            {
                "source_key": "proof-seed",
                "source_url": "https://proof.example.local/seed/verified",
                "content": b"Seed verified evidence content for proof gate.",
                "http_status": 200,
                "review_status": "verified",  # publicly visible
            },
            {
                "source_key": "proof-seed",
                "source_url": "https://proof.example.local/seed/rejected",
                "content": b"Seed rejected evidence content for exclusion test.",
                "http_status": 200,
                "review_status": "rejected",  # must be excluded from public
            },
            {
                "source_key": "proof-seed",
                "source_url": "https://proof.example.local/seed/quarantined",
                "content": b"Seed quarantined evidence content for exclusion test.",
                "http_status": 200,
                "review_status": "quarantined",  # must be excluded from public
            },
        ]

        for i, s in enumerate(snapshots, start=1):
            content_bytes = s["content"]
            ch = _snapshot_hash(content_bytes)
            snap = SourceSnapshot(
                source_key=s["source_key"],
                source_url=s["source_url"],
                fetched_at=now + timedelta(seconds=i),
                content_hash=ch,
                original_content_hash=ch,
                stored_content_hash=ch,
                raw_content=content_bytes.decode("utf-8", errors="replace"),
                http_status=s["http_status"],
                content_type="text/plain",
                storage_backend="db",
                content_size_bytes=len(content_bytes),
                stored_size_bytes=len(content_bytes),
                is_truncated=False,
                created_at=now + timedelta(seconds=i),
            )
            db.add(snap)

        db.commit()
        print(f"  Seeded {len(snapshots)} evidence snapshots (verified, rejected, quarantined)")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    # Determine proof DB path
    proof_db_path: Path
    if "--proof-db" in args:
        idx = args.index("--proof-db")
        proof_db_path = Path(args[idx + 1]).resolve()
    else:
        PROOF_DIR.mkdir(parents=True, exist_ok=True)
        proof_db_path = PROOF_DIR / "proof.db"

    proof_db_url = f"sqlite:///{proof_db_path}"
    os.environ["JTA_DATABASE_URL"] = proof_db_url

    print(f"PREPARE PROOF DB: {proof_db_path}")

    # Step 1: run migrations
    print("  Running Alembic migrations...")
    rc = run_migrations(proof_db_url)
    if rc != 0:
        print("RESULT: FAIL migration_failed")
        return 1

    print("  Migrations applied.")

    # Step 2: seed audit chain
    print("  Seeding audit chain...")
    seed_audit_chain(proof_db_url)

    # Step 3: seed evidence snapshots
    print("  Seeding evidence snapshots...")
    seed_evidence_snapshots(proof_db_url)

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
