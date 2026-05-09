"""Record human review decisions on ReviewItem rows."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.entities import ReviewItem

APPROVED = "approved"
REJECTED = "rejected"
FLAGGED = "flagged"
VALID_DECISIONS = frozenset({APPROVED, REJECTED, FLAGGED})


@dataclass
class ReviewDecisionResult:
    ok: bool
    item_id: int
    new_status: str
    reason: str | None = None


def record_decision(
    db: Session,
    item_id: int,
    *,
    decision: str,
    reviewer_id: str,
    notes: str | None = None,
) -> ReviewDecisionResult:
    """Apply *decision* to a ReviewItem and flush (caller commits).

    Returns ReviewDecisionResult with ok=False if item not found or decision invalid.
    """
    if decision not in VALID_DECISIONS:
        return ReviewDecisionResult(
            ok=False, item_id=item_id, new_status="", reason=f"invalid_decision: {decision}"
        )

    item = db.query(ReviewItem).filter(ReviewItem.id == item_id).first()
    if item is None:
        return ReviewDecisionResult(ok=False, item_id=item_id, new_status="", reason="not_found")

    item.status = decision
    item.reviewer_id = reviewer_id
    item.reviewer_notes = notes
    item.reviewed_at = datetime.now(timezone.utc)

    if decision == APPROVED:
        item.public_visibility = True

    db.flush()

    return ReviewDecisionResult(ok=True, item_id=item_id, new_status=decision)
