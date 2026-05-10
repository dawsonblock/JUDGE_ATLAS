from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routes.ai_correctness import run_incident_check
from app.api.routes.public_events import create_event
from app.schemas.api import EventCreate


def _event_payload() -> EventCreate:
    return EventCreate(
        court_id=1,
        case_id=1,
        primary_location_id=1,
        event_type="sentencing",
        title="Audit fail-closed regression",
        summary="Regression payload",
    )


def test_public_event_create_fails_closed_when_audit_write_fails() -> None:
    db = MagicMock()
    db.get.return_value = object()

    with patch(
        "app.api.routes.public_events.log_mutation",
        side_effect=RuntimeError("audit down"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            create_event(
                payload=_event_payload(),
                request=MagicMock(),
                actor=MagicMock(),
                db=db,
            )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Audit logging failed; mutation aborted"
    db.flush.assert_called_once()
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_ai_correctness_incident_fails_closed_when_audit_write_fails() -> None:
    db = MagicMock()
    db.get.return_value = MagicMock()
    chk = MagicMock(id=7, status="ok")

    with (
        patch(
            "app.api.routes.ai_correctness.check_crime_incident",
            return_value=chk,
        ),
        patch(
            "app.api.routes.ai_correctness.log_mutation",
            side_effect=RuntimeError("audit down"),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            run_incident_check(
                incident_id=42,
                db=db,
                actor=MagicMock(),
            )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Audit logging failed; mutation aborted"
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
