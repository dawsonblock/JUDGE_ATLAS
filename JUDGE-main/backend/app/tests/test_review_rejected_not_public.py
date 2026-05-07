"""Tests that a rejected review decision sets public_visibility=False.

Uses dependency_overrides to bypass real auth.  Verifies the entity is not
publicly visible after a 'reject' decision, regardless of its prior state.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.actor import AdminActor
from app.auth.admin import require_admin_review
from app.db.session import SessionLocal
from app.main import app
from app.models.entities import CrimeIncident, Event
from app.serializers.public import entity_public_visibility


REVIEWER_ACTOR = AdminActor(
    actor_id="ci-reviewer@test.example",
    actor_type="user",
    role="reviewer",
    auth_method="jwt",
    email="ci-reviewer@test.example",
)


@pytest.fixture()
def client_as_reviewer():
    app.dependency_overrides[require_admin_review] = lambda: REVIEWER_ACTOR
    yield TestClient(app)
    app.dependency_overrides.pop(require_admin_review, None)


class TestRejectedEntityNotPublic:
    """A rejected decision must make the entity non-public."""

    def test_rejected_crime_incident_not_visible(
        self, client_as_reviewer: TestClient
    ) -> None:
        with SessionLocal() as db:
            incident = db.scalar(
                select(CrimeIncident).order_by(CrimeIncident.id).limit(1)
            )
            if incident is None:
                pytest.skip("No CrimeIncident in test DB.")
            entity_id = str(incident.id)

        resp = client_as_reviewer.post(
            f"/api/admin/review-queue/crime_incident/{entity_id}/decision",
            json={"decision": "reject", "notes": "rejected-visibility-test"},
        )
        assert resp.status_code == 200, resp.text

        with SessionLocal() as db:
            refreshed = db.get(CrimeIncident, int(entity_id))
            assert refreshed is not None
            assert entity_public_visibility(refreshed) is False, (
                "Rejected entity must not be publicly visible"
            )

    def test_rejected_event_not_visible(
        self, client_as_reviewer: TestClient
    ) -> None:
        with SessionLocal() as db:
            event = db.scalar(select(Event).order_by(Event.id).limit(1))
            if event is None:
                pytest.skip("No Event in test DB.")
            # Events use event_id (string) for external routing but integer id for db
            db_id = str(event.id)

        resp = client_as_reviewer.post(
            f"/api/admin/review-queue/event/{db_id}/decision",
            json={"decision": "reject", "notes": "event-rejected-visibility-test"},
        )
        assert resp.status_code == 200, resp.text

        with SessionLocal() as db:
            refreshed = db.get(Event, int(db_id))
            assert refreshed is not None
            assert entity_public_visibility(refreshed) is False, (
                "Rejected event must not be publicly visible"
            )

    def test_approved_entity_is_visible(
        self, client_as_reviewer: TestClient
    ) -> None:
        """Sanity check: approved decision makes entity visible."""
        with SessionLocal() as db:
            incident = db.scalar(
                select(CrimeIncident).order_by(CrimeIncident.id).limit(1)
            )
            if incident is None:
                pytest.skip("No CrimeIncident in test DB.")
            entity_id = str(incident.id)

        resp = client_as_reviewer.post(
            f"/api/admin/review-queue/crime_incident/{entity_id}/decision",
            json={"decision": "approve"},
        )
        assert resp.status_code == 200, resp.text

        with SessionLocal() as db:
            refreshed = db.get(CrimeIncident, int(entity_id))
            assert refreshed is not None
            assert entity_public_visibility(refreshed) is True
