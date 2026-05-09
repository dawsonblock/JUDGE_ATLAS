"""Gate that must pass before any record can be set is_public=True."""
from __future__ import annotations

from app.models.entities import CrimeIncident, ReviewItem


class PublicationBlockedError(ValueError):
    """Raised when a record cannot be published due to unmet requirements."""


def assert_publication_ready(incident: CrimeIncident) -> None:
    """Raise PublicationBlockedError if the incident may not be published.

    Requirements:
    - review_status must be 'approved'
    - source_snapshot_id must be set (evidence link)
    - verification_status must not be 'unverified'
    """
    if incident.review_status != "approved":
        raise PublicationBlockedError(
            f"Incident {incident.id} review_status='{incident.review_status}' "
            f"— must be 'approved' before publication"
        )
    if not incident.source_snapshot_id:
        raise PublicationBlockedError(
            f"Incident {incident.id} has no source_snapshot_id — evidence link required"
        )
    if incident.verification_status == "unverified":
        raise PublicationBlockedError(
            f"Incident {incident.id} verification_status='unverified' — cannot publish"
        )


def assert_review_item_publication_ready(item: ReviewItem) -> None:
    """Raise PublicationBlockedError if the ReviewItem has not been approved."""
    if item.status != "approved":
        raise PublicationBlockedError(
            f"ReviewItem {item.id} status='{item.status}' — must be 'approved'"
        )
    if not item.source_snapshot_id:
        raise PublicationBlockedError(
            f"ReviewItem {item.id} has no source_snapshot_id — evidence link required"
        )
