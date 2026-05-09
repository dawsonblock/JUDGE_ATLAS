"""Persist IngestionResult records to the database.

Called from the admin ``/run`` endpoint and Celery tasks after
``adapter.run()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ingestion.adapters import CreatedRecord, CreatedReviewItem, IngestionResult
from app.ingestion.quarantine import quarantine_run
from app.services.constants import AI_PUBLISH_RECOMMENDATIONS
from app.ingestion.statuses import PENDING, QUARANTINED
from app.models.entities import (
    CrimeIncident,
    IngestionRun,
    ReviewItem,
    SourceRegistry,
    SourceSnapshot,
)


@dataclass
class RunPersistSummary:
    persisted_incidents: int = 0
    skipped_duplicates: int = 0
    persisted_review_items: int = 0
    snapshots_written: int = 0
    quarantined_count: int = 0
    failed_records: int = 0
    review_items_skipped: int = 0
    contract_violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Machine-ingest contract ───────────────────────────────────────────────────

# Sources whose ``source_class`` is None are treated as legacy machine_ingest.
_MACHINE_INGEST_CLASSES: frozenset[str | None] = frozenset(["machine_ingest", None])


def _validate_machine_ingest_contract(
    result: IngestionResult,
    source: SourceRegistry,
) -> list[str]:
    """Return a list of contract-violation reason slugs for a machine_ingest run.

    An empty list means the result satisfies every requirement and may be
    persisted.  A non-empty list means the run must be quarantined.

    Requirements for machine_ingest sources:
    - ``result.raw_snapshot_bytes`` must be non-empty (real fetched content)
    - A source URL must be resolvable (``result.fetch_url`` or ``source.base_url``)
    - ``source.parser_version`` must be set (proves the adapter is versioned)
    """
    reasons: list[str] = []

    if not result.raw_snapshot_bytes:
        reasons.append("no_raw_content")

    if not (result.fetch_url or source.base_url):
        reasons.append("no_fetch_url")

    if not source.parser_version:
        reasons.append("no_parser_version")
    elif result.parser_version is None:
        # source declares a required version but the adapter did not report one
        reasons.append("no_parser_version")
    elif result.parser_version != source.parser_version:
        reasons.append("parser_version_mismatch")

    return reasons


def _create_snapshot(
    db: Session,
    source: SourceRegistry,
    run_record: IngestionRun,
    raw_content: bytes | None = None,
    *,
    http_status: int | None = None,
    content_type: str | None = None,
    fetch_url: str | None = None,
) -> SourceSnapshot:
    """Create a SourceSnapshot for this run via the canonical snapshot writer.

    Routes through :func:`app.services.snapshot_writer.write_snapshot` so that
    all hash / integrity / evidence-store logic lives in one place.  When
    *raw_content* is ``None`` (the adapter did not produce raw bytes), an
    empty-bytes placeholder is written so snapshot integrity constraints are
    still satisfied.
    """
    from app.services.snapshot_writer import write_snapshot  # noqa: PLC0415

    content = raw_content if raw_content is not None else b""
    try:
        return write_snapshot(
            db=db,
            source_url=(
                fetch_url
                or source.base_url
                or f"internal://adapter/{source.source_key}"
            ),
            fetched_at=datetime.now(timezone.utc),
            content=content,
            http_status=http_status,
            content_type=content_type,
            ingestion_run_id=run_record.id,
            source_key=source.source_key,
        )
    except ValueError:
        run_record.status = QUARANTINED
        run_record.quarantine_reason = "no_raw_content"
        raise


def _insert_crime_incident(
    db: Session,
    record: CreatedRecord,
    snapshot: SourceSnapshot,
) -> bool:
    """Insert one CrimeIncident row.  Returns False on dedup (no insert)."""
    if record.external_id is not None:
        exists = (
            db.query(CrimeIncident.id)
            .filter(
                CrimeIncident.source_name == record.source_key,
                CrimeIncident.external_id == record.external_id,
            )
            .first()
        )
        if exists is not None:
            return False

    p = record.payload
    incident = CrimeIncident(
        source_id=record.source_key,
        external_id=record.external_id,
        incident_type=p.get("incident_type") or "unknown",
        incident_category=p.get("incident_category") or "other",
        reported_at=p.get("reported_at"),
        occurred_at=p.get("occurred_at"),
        city=p.get("city"),
        province_state=p.get("province_state"),
        country=p.get("country"),
        public_area_label=p.get("public_area_label"),
        latitude_public=p.get("latitude_public"),
        longitude_public=p.get("longitude_public"),
        precision_level=p.get("precision_level") or "general_area",
        source_url=record.source_url or p.get("source_url"),
        source_name=record.source_key,
        verification_status=p.get("verification_status") or "reported",
        is_public=False,
        review_status="pending_review",
        source_snapshot_id=snapshot.id,
    )
    db.add(incident)
    return True


def _summarize_warning_code(summary: RunPersistSummary, warning_code: str) -> None:
    if warning_code not in summary.warnings:
        summary.warnings.append(warning_code)


def _insert_review_item(
    db: Session,
    item: CreatedReviewItem,
    snapshot: SourceSnapshot,
    run_record: IngestionRun,
) -> None:
    recommendation = item.payload.get("publish_recommendation") or "review_required"
    if recommendation not in AI_PUBLISH_RECOMMENDATIONS:
        recommendation = "review_required"
    rv = ReviewItem(
        record_type=item.payload.get("record_type") or "unknown",
        source_snapshot_id=snapshot.id,
        suggested_payload_json=item.payload,
        source_url=item.url,
        source_quality=item.payload.get("source_quality") or "unverified",
        confidence=item.confidence_score,
        privacy_status=item.payload.get("privacy_status") or "unknown",
        publish_recommendation=recommendation,
        public_visibility=False,
        status=PENDING,
        ingestion_run_id=run_record.id,
    )
    db.add(rv)


def persist_ingestion_result(
    db: Session,
    source: SourceRegistry,
    run_record: IngestionRun,
    result: IngestionResult,
) -> RunPersistSummary:
    """Write IngestionResult records to the DB and return summary counts.

    Creates one SourceSnapshot per run, then inserts CrimeIncident rows for
    each CreatedRecord (deduped on source_key + external_id) and ReviewItem
    rows for each CreatedReviewItem.

    The caller is responsible for committing the session after this call.
    """
    summary = RunPersistSummary()

    # ── Machine-ingest structural validation ─────────────────────────────────
    # For machine_ingest (and legacy None) sources, enforce the evidence
    # contract *before* writing anything.  Portal-reference and other classes
    # are not auto-ingested so they skip this gate.
    if source.source_class in _MACHINE_INGEST_CLASSES:
        contract_violations = _validate_machine_ingest_contract(result, source)
        if contract_violations:
            quarantine_run(
                db,
                run_record,
                "; ".join(contract_violations),
            )
            summary.contract_violations = contract_violations
            summary.quarantined_count += 1
            return summary

    # Always create a snapshot when raw bytes exist, even if no records were parsed.
    # A zero-result run is still evidence: we fetched URL X at time Y with HTTP status Z.
    # Skipping the snapshot loses audit information about what the adapter saw.
    has_records = bool(result.created_records or result.review_items)
    has_raw_bytes = bool(result.raw_snapshot_bytes)

    if has_records and not has_raw_bytes:
        summary.warnings.append(
            "raw_snapshot_bytes absent — evidence provenance incomplete"
        )

    if not has_records and not has_raw_bytes:
        # Nothing to persist: no records and no raw evidence bytes.
        return summary

    snapshot = _create_snapshot(
        db,
        source,
        run_record,
        result.raw_snapshot_bytes,
        http_status=result.fetch_http_status,
        content_type=result.fetch_content_type,
        fetch_url=result.fetch_url,
    )
    summary.snapshots_written = 1

    if not has_records:
        # Snapshot-only run: raw bytes preserved, no parsed records.
        # This is valid evidence of a zero-result fetch.
        return summary

    for record in result.created_records:
        try:
            if _insert_crime_incident(db, record, snapshot):
                summary.persisted_incidents += 1
            else:
                summary.skipped_duplicates += 1
                _summarize_warning_code(summary, "duplicate_record_skipped")
        except Exception:
            summary.failed_records += 1
            _summarize_warning_code(summary, "crime_incident_insert_failed")
            continue

    for item in result.review_items:
        try:
            _insert_review_item(db, item, snapshot, run_record)
            summary.persisted_review_items += 1
        except Exception:
            summary.review_items_skipped += 1
            _summarize_warning_code(summary, "review_item_insert_failed")
            continue

    # Reflect actual persist/skip counts back onto the run record before commit
    run_record.persisted_count = summary.persisted_incidents
    run_record.skipped_count = (
        run_record.skipped_count or 0
    ) + summary.skipped_duplicates

    return summary
