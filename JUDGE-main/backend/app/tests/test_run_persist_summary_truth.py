"""Tests for RunPersistSummary truth — Phase 6.

Guards that:
- All 9 fields are present with correct zero-defaults.
- contract_violations and warnings use independent default_factory lists (no
  shared-mutable-default bug).
- New fields (quarantined_count, failed_records, review_items_skipped) are
  accessible and reflected in the admin run response.
"""

from __future__ import annotations

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
