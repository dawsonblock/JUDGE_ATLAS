"""Tamper-detection tests for the persisted AuditLog integrity chain.

Proves that verify_chain() catches:
  1. A clean chain passes without violations.
  2. Payload mutation in a stored row is detected.
  3. A missing row (non-monotonic ID gap) is detected.
  4. Stored entry_hash field mismatch (direct DB tampering) is detected.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.audit.chain_digest import GENESIS_HASH, row_digest
from app.audit.integrity_chain import verify_chain
from app.models.entities import AuditLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(
    row_id: int,
    action: str = "test.action",
    actor_id: str = "admin-1",
    payload: dict | None = None,
    prev_hash: str = GENESIS_HASH,
) -> AuditLog:
    """Build an AuditLog instance with a correct entry_hash for *prev_hash*."""
    row = AuditLog(
        id=row_id,
        action=action,
        entity_type="test",
        entity_id="1",
        actor_id=actor_id,
        actor_type="admin",
        actor_role="admin",
        payload=payload or {},
        created_at=datetime(2026, 1, 1, 0, 0, row_id, tzinfo=timezone.utc),
        previous_entry_hash=prev_hash,
    )
    row.entry_hash = row_digest(row, prev_hash)
    return row


def _mock_db(rows: list[AuditLog]) -> MagicMock:
    db = MagicMock()
    query_mock = MagicMock()
    order_mock = MagicMock()
    order_mock.all.return_value = rows
    query_mock.order_by.return_value = order_mock
    db.query.return_value = query_mock
    return db


def _build_chain(*actions: str) -> list[AuditLog]:
    rows: list[AuditLog] = []
    prev_hash = GENESIS_HASH
    for i, action in enumerate(actions, start=1):
        row = _make_row(i, action=action, prev_hash=prev_hash)
        prev_hash = row.entry_hash  # type: ignore[assignment]
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVerifyChainIntact:
    def test_empty_chain_passes(self):
        db = _mock_db([])
        result = verify_chain(db)
        assert result.ok is True
        assert result.entries_checked == 0
        assert result.violations == []

    def test_valid_chain_passes(self):
        rows = _build_chain("judge.create", "evidence.verify", "graph.edge.create")
        db = _mock_db(rows)
        result = verify_chain(db)
        assert result.ok is True, result.violations
        assert result.entries_checked == 3
        assert result.chain_head == rows[-1].entry_hash


class TestVerifyChainTampering:
    def test_payload_mutation_detected(self):
        """Mutating the payload of a stored row must trigger an entry_hash mismatch."""
        rows = _build_chain("judge.create", "evidence.verify")
        # Tamper: change the payload of the first row AFTER its hash was computed.
        rows[0].payload = {"_tampered": True}
        db = _mock_db(rows)
        result = verify_chain(db)
        assert result.ok is False
        assert any("entry_hash mismatch" in v for v in result.violations)

    def test_non_monotonic_id_detected(self):
        """A non-monotonic row ID (simulating a deleted + re-inserted row) is flagged."""
        rows = _build_chain("judge.create", "evidence.verify", "graph.edge.create")
        # Tamper: reassign second row's id so it is not monotonically increasing.
        rows[1].id = rows[0].id  # duplicate / non-monotonic
        db = _mock_db(rows)
        result = verify_chain(db)
        assert result.ok is False
        assert any("non-monotonic id" in v for v in result.violations)

    def test_direct_hash_field_tampering_detected(self):
        """Directly overwriting entry_hash in the DB row must be caught."""
        rows = _build_chain("judge.create", "evidence.verify")
        # Tamper: overwrite stored hash on first row with a plausible-looking value.
        rows[0].entry_hash = "a" * 64
        db = _mock_db(rows)
        result = verify_chain(db)
        assert result.ok is False
        assert any("entry_hash mismatch" in v for v in result.violations)

    def test_missing_actor_id_detected(self):
        """Rows without actor_id must be flagged as chain violations."""
        rows = _build_chain("judge.create", "evidence.verify")
        rows[1].actor_id = None
        db = _mock_db(rows)
        result = verify_chain(db)
        assert result.ok is False
        assert any("missing actor_id" in v for v in result.violations)
