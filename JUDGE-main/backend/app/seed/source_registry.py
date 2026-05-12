"""Seed the source_registry table with known ingestion sources.

Idempotent: skips any row whose source_key already exists.
Fail-closed: all sources default to is_active=False.

Dev override: set JTA_CANADA_FIRST_DEV_ENABLE_SASKATOON=true *and*
APP_ENV=development to activate the saskatoon_crime pipeline locally.

Run standalone:
    python -m app.seed.source_registry
"""

from __future__ import annotations

import json
import os
import pathlib

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import SourceRegistry

# All sources are now defined in canada_saskatchewan_sources.yaml.
# Legacy hardcoded keys have been removed; YAML entries are authoritative.
_SOURCES: list[dict] = []

# ── YAML-driven Canada / Saskatchewan source definitions ─────────────────────
# Sources defined in the YAML override any matching source_key in _SOURCES.

_YAML_PATH = (
    pathlib.Path(__file__).parent.parent
    / "ingestion"
    / "sources"
    / "canada_saskatchewan_sources.yaml"
)

_LIST_FIELDS = ("allowed_domains", "creates")


def _load_yaml_sources() -> list[dict]:
    """Load sources from the YAML config, normalising list fields to JSON strings.

    Returns an empty list if the YAML file is missing (allows the module to
    import cleanly in environments where the file has not been deployed yet).
    """
    if not _YAML_PATH.exists():
        return []
    with _YAML_PATH.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    out: list[dict] = []
    for entry in raw.get("sources", []):
        normalised = dict(entry)
        for field in _LIST_FIELDS:
            val = normalised.get(field)
            if isinstance(val, list):
                normalised[field] = json.dumps(val)
        out.append(normalised)
    return out


def _merged_sources() -> list[dict]:
    """Return the canonical source list, with YAML entries taking precedence."""
    yaml_sources = _load_yaml_sources()
    yaml_keys = {s["source_key"] for s in yaml_sources}
    base = [s for s in _SOURCES if s["source_key"] not in yaml_keys]
    return base + yaml_sources


# Required fields for machine_ingest sources that cannot be None/empty.
_MACHINE_INGEST_REQUIRED: tuple[str, ...] = (
    "parser",
    "parser_version",
    "allowed_domains",
    "source_class",
    "base_url",
    "public_record_authority",
    "requires_manual_review",
    "public_publish_default",
    "terms_url",
    "automation_status",
)

# Fields whose type is boolean — checked with `is None` rather than truthiness
# to avoid flagging a legitimate `False` value as missing.
_BOOL_FIELDS: frozenset[str] = frozenset({"requires_manual_review", "public_publish_default"})


def validate_machine_ingest_source_spec(spec: dict) -> list[str]:
    """Return violation slugs for a source spec that fails machine_ingest contracts.

    Call this during seeding or test assertions to reject incomplete specs
    before they reach the DB.  An empty return list means the spec is valid.

    Only applied when ``spec["source_class"] == "machine_ingest"``.  All other
    source classes are passed through without validation.
    """
    if spec.get("source_class") != "machine_ingest":
        return []

    violations: list[str] = []
    for field in _MACHINE_INGEST_REQUIRED:
        val = spec.get(field)
        # Boolean fields can legitimately be False — check only for None.
        # For all other fields treat an empty-list JSON string ("[]") as missing.
        if field in _BOOL_FIELDS:
            if val is None:
                violations.append(f"missing_{field}")
        elif not val or val == "[]":
            violations.append(f"missing_{field}")
    return violations


def seed_source_registry(db: Session) -> None:
    """Insert source registry rows that do not yet exist (idempotent)."""
    for spec in _merged_sources():
        existing = db.scalar(
            select(SourceRegistry).where(
                SourceRegistry.source_key == spec["source_key"]
            )
        )
        if existing is not None:
            continue
        db.add(SourceRegistry(**spec))
    db.commit()


# Fields whose DB value must match the spec.
# is_active is intentionally excluded — admins manage it via the frontend UI.
# auto_publish_enabled and requires_manual_review are intentionally excluded —
# these are operational flags controlled by operators and should never be
# silently reverted by a seed/repair run.
_REPAIR_FIELDS: tuple[str, ...] = (
    "source_name",
    "source_type",
    "source_tier",
    "fetch_method",
    "update_cadence",
    "country",
    "province_state",
    "city",
    "precision_level",
    # New metadata fields (YAML-sourced)
    "jurisdiction",
    "category",
    "priority",
    "public_record_authority",
    "base_url",
    "allowed_domains",
    "refresh_interval_minutes",
    "parser",
    "license",
    "license_url",
    "terms_url",
    "creates",
    "public_publish_default",
    "source_class",
    "parser_version",
    "automation_status",
)


def repair_canada_first_defaults(db: Session, *, dry_run: bool = False) -> list[str]:
    """Repair existing registry rows that deviate from the current ``_SOURCES`` spec.

    Only the fields listed in :data:`_REPAIR_FIELDS` are checked — ``is_active``
    is intentionally excluded because admins manage it via the frontend UI.

    Args:
        db: SQLAlchemy session.
        dry_run: If *True*, collect diffs but do not write any changes.

    Returns:
        A list of human-readable change descriptions (one per field corrected).
    """
    changes: list[str] = []
    for spec in _merged_sources():
        row = db.scalar(
            select(SourceRegistry).where(
                SourceRegistry.source_key == spec["source_key"]
            )
        )
        if row is None:
            continue  # seed_source_registry handles inserts
        for field_name in _REPAIR_FIELDS:
            if field_name not in spec:
                continue
            current_val = getattr(row, field_name, None)
            spec_val = spec[field_name]
            if current_val != spec_val:
                changes.append(
                    f"{spec['source_key']}.{field_name}: {current_val!r} → {spec_val!r}"
                )
                if not dry_run:
                    setattr(row, field_name, spec_val)
    if not dry_run and changes:
        db.commit()
    return changes


if __name__ == "__main__":
    import argparse

    from app.db.session import SessionLocal

    parser = argparse.ArgumentParser(description="Source registry seed + repair")
    parser.add_argument(
        "--repair", action="store_true", help="Repair stale registry rows"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without applying (implies --repair)",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        seed_source_registry(db)
        print("source_registry seeded")
        if args.repair or args.dry_run:
            changes = repair_canada_first_defaults(db, dry_run=args.dry_run)
            if not changes:
                print("No deviations found.")
            else:
                for msg in changes:
                    print(msg)
                if args.dry_run:
                    print("(dry run — no changes committed)")
                else:
                    print(f"{len(changes)} field(s) repaired.")
