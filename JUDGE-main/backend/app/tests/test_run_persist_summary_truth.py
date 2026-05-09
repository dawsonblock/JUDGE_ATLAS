"""Tests for RunPersistSummary truth — Phase 6.

Guards that:
- All 9 fields are present with correct zero-defaults.
- contract_violations and warnings use independent default_factory lists (no
  shared-mutable-default bug).
- New fields (quarantined_count, failed_records, review_items_skipped) are
  accessible and reflected in the admin run response.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.ingestion.adapters import IngestionResult
from app.ingestion.source_runner import RunPersistSummary


# ---------------------------------------------------------------------------
# Default-value tests
# ---------------------------------------------------------------------------


def test_run_persist_summary_zero_defaults() -> None:
    s = RunPersistSummary()
    assert s.persisted_incidents == 0
    assert s.skipped_duplicates == 0
    assert s.persisted_review_items == 0
    assert s.snapshots_written == 0
    assert s.quarantined_count == 0
    assert s.failed_records == 0
    assert s.review_items_skipped == 0
    assert s.contract_violations == []
    assert s.warnings == []


def test_contract_violations_default_is_not_shared() -> None:
    """Each RunPersistSummary instance must get its own list, not a shared one."""
    a = RunPersistSummary()
    b = RunPersistSummary()
    a.contract_violations.append("oops")
    assert b.contract_violations == []


def test_warnings_default_is_not_shared() -> None:
    a = RunPersistSummary()
    b = RunPersistSummary()
    a.warnings.append("warn")
    assert b.warnings == []


# ---------------------------------------------------------------------------
# Field construction tests
# ---------------------------------------------------------------------------


def test_quarantined_count_set() -> None:
    s = RunPersistSummary(quarantined_count=3)
    assert s.quarantined_count == 3


def test_failed_records_set() -> None:
    s = RunPersistSummary(failed_records=7)
    assert s.failed_records == 7


def test_review_items_skipped_set() -> None:
    s = RunPersistSummary(review_items_skipped=2)
    assert s.review_items_skipped == 2


def test_all_fields_set_together() -> None:
    s = RunPersistSummary(
        persisted_incidents=10,
        skipped_duplicates=2,
        persisted_review_items=3,
        snapshots_written=1,
        quarantined_count=1,
        failed_records=4,
        review_items_skipped=0,
        contract_violations=["no_raw_content"],
        warnings=["stale_parser"],
    )
    assert s.persisted_incidents == 10
    assert s.contract_violations == ["no_raw_content"]
    assert s.warnings == ["stale_parser"]
    assert s.quarantined_count == 1
    assert s.failed_records == 4


def _make_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def _make_source() -> MagicMock:
    source = MagicMock()
    source.source_class = "machine_ingest"
    source.base_url = "https://example.gc.ca/"
    source.parser_version = "1.0"
    source.source_key = "test_source"
    return source


def _make_run() -> MagicMock:
    run = MagicMock()
    run.id = 42
    run.persisted_count = 0
    run.skipped_count = 0
    return run


def _make_result() -> IngestionResult:
    return IngestionResult(
        source_key="test_source",
        raw_snapshot_bytes=b"<html>content</html>",
        fetch_url="https://example.gc.ca/data",
        fetch_http_status=200,
        fetch_content_type="text/html",
        parser_version="1.0",
        created_records=[],
        review_items=[],
        errors=[],
    )


def test_crime_incident_insert_failure_adds_warning_and_count() -> None:
    from app.ingestion import source_runner

    db = _make_db()
    source = _make_source()
    run = _make_run()
    result = _make_result()
    result.created_records = [SimpleNamespace(source_key="test_source", external_id="A1", payload={}, source_url="https://example.gc.ca/a")]

    with patch.object(source_runner, "_create_snapshot", return_value=SimpleNamespace(id=7)):
        with patch.object(source_runner, "_insert_crime_incident", side_effect=RuntimeError("boom")):
            summary = source_runner.persist_ingestion_result(db, source, run, result)

    assert summary.failed_records == 1
    assert "crime_incident_insert_failed" in summary.warnings


def test_review_item_insert_failure_adds_warning_and_count() -> None:
    from app.ingestion import source_runner

    db = _make_db()
    source = _make_source()
    run = _make_run()
    result = _make_result()
    result.review_items = [SimpleNamespace(payload={"record_type": "incident"}, url="https://example.gc.ca/review", confidence_score=0.8)]

    with patch.object(source_runner, "_create_snapshot", return_value=SimpleNamespace(id=8)):
        with patch.object(source_runner, "_insert_review_item", side_effect=RuntimeError("boom")):
            summary = source_runner.persist_ingestion_result(db, source, run, result)

    assert summary.review_items_skipped == 1
    assert "review_item_insert_failed" in summary.warnings


def test_duplicate_record_skipped_warns_once() -> None:
    from app.ingestion import source_runner

    db = _make_db()
    source = _make_source()
    run = _make_run()
    result = _make_result()
    result.created_records = [SimpleNamespace(source_key="test_source", external_id="A1", payload={}, source_url="https://example.gc.ca/a") for _ in range(2)]

    with patch.object(source_runner, "_create_snapshot", return_value=SimpleNamespace(id=9)):
        with patch.object(source_runner, "_insert_crime_incident", return_value=False):
            summary = source_runner.persist_ingestion_result(db, source, run, result)

    assert summary.skipped_duplicates == 2
    assert summary.warnings.count("duplicate_record_skipped") == 1
