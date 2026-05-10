from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routes.ai_correctness import run_incident_check
from app.api.routes.admin_ingestion import retry_ingestion_run
from app.api.routes.ingestion import import_crime_incidents_manual_csv
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


@pytest.mark.asyncio
async def test_manual_csv_import_fails_closed_when_audit_write_fails() -> None:
    db = MagicMock()
    actor = MagicMock(auth_method="jwt")
    result = SimpleNamespace(
        read_count=2,
        persisted_count=1,
        skipped_count=1,
        error_count=0,
        errors=[],
    )
    settings = SimpleNamespace(max_csv_upload_size=1024)

    with (
        patch("app.api.routes.ingestion.get_settings", return_value=settings),
        patch(
            "app.api.routes.ingestion.read_upload_file_limited",
            new=AsyncMock(
                return_value=b"source_id,external_id,incident_type,incident_category,reported_at,occurred_at,city,province_state,country,public_area_label,latitude_public,longitude_public,precision_level,source_url,source_name,verification_status,notes\n"
            ),
        ),
        patch(
            "app.ingestion.crime_sources.manual_csv.import_crime_incidents_csv",
            return_value=result,
        ),
        patch(
            "app.api.routes.ingestion.log_mutation",
            side_effect=RuntimeError("audit down"),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await import_crime_incidents_manual_csv(
                file=MagicMock(),
                db=db,
                actor=actor,
            )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Audit logging failed; mutation aborted"
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_ingestion_retry_fails_closed_when_audit_write_fails() -> None:
    db = MagicMock()
    actor = MagicMock(auth_method="jwt")
    existing_run = SimpleNamespace(id=11, source_name="demo_source", status="completed")
    source = SimpleNamespace(
        source_key="demo_source", source_class="machine_ingest", parser="demo"
    )
    result = SimpleNamespace(
        success=True,
        records_fetched=3,
        records_skipped=0,
        created_records=[],
        review_items=[],
        errors=[],
    )
    summary = SimpleNamespace(
        persisted_incidents=1,
        persisted_review_items=1,
        skipped_duplicates=0,
    )

    first_query = MagicMock()
    first_filter = first_query.filter.return_value
    first_filter.first.return_value = existing_run

    second_query = MagicMock()
    second_filter = second_query.filter.return_value
    second_filter.first.return_value = source

    db.query.side_effect = [first_query, second_query]

    with (
        patch("app.services.source_control.require_source_enabled"),
        patch(
            "app.ingestion.source_adapter_factory.build_adapter"
        ) as build_adapter_mock,
        patch(
            "app.ingestion.source_runner.persist_ingestion_result",
            return_value=summary,
        ),
        patch("app.ingestion.source_registry_ctl.update_source_health"),
        patch(
            "app.api.routes.admin_ingestion.log_mutation",
            side_effect=RuntimeError("audit down"),
        ),
        patch("app.core.config.get_settings", return_value=SimpleNamespace()),
    ):
        adapter = MagicMock()
        adapter.run.return_value = result
        build_adapter_mock.return_value = adapter

        with pytest.raises(HTTPException) as exc_info:
            retry_ingestion_run(
                run_id=11,
                request=MagicMock(),
                db=db,
                actor=actor,
            )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Audit logging failed; mutation aborted"
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_ingestion_retry_adapter_failure_writes_audit_before_commit() -> None:
    db = MagicMock()
    actor = MagicMock(auth_method="jwt")
    existing_run = SimpleNamespace(id=21, source_name="demo_source", status="completed")
    source = SimpleNamespace(
        source_key="demo_source", source_class="machine_ingest", parser="demo"
    )

    first_query = MagicMock()
    first_filter = first_query.filter.return_value
    first_filter.first.return_value = existing_run

    second_query = MagicMock()
    second_filter = second_query.filter.return_value
    second_filter.first.return_value = source

    db.query.side_effect = [first_query, second_query]

    with (
        patch("app.services.source_control.require_source_enabled"),
        patch(
            "app.ingestion.source_adapter_factory.build_adapter"
        ) as build_adapter_mock,
        patch("app.ingestion.source_registry_ctl.update_source_health"),
        patch("app.api.routes.admin_ingestion.log_mutation") as log_mutation_mock,
        patch("app.core.config.get_settings", return_value=SimpleNamespace()),
    ):
        adapter = MagicMock()
        adapter.run.side_effect = RuntimeError("adapter exploded")
        build_adapter_mock.return_value = adapter

        with pytest.raises(HTTPException) as exc_info:
            retry_ingestion_run(
                run_id=21,
                request=MagicMock(),
                db=db,
                actor=actor,
            )

    assert exc_info.value.status_code == 500
    assert "Adapter error:" in exc_info.value.detail
    assert log_mutation_mock.call_args.kwargs["action"] == "ingestion_run.retry_failed"
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_ingestion_retry_adapter_failure_audit_failure_rolls_back() -> None:
    db = MagicMock()
    actor = MagicMock(auth_method="jwt")
    existing_run = SimpleNamespace(id=22, source_name="demo_source", status="completed")
    source = SimpleNamespace(
        source_key="demo_source", source_class="machine_ingest", parser="demo"
    )

    first_query = MagicMock()
    first_filter = first_query.filter.return_value
    first_filter.first.return_value = existing_run

    second_query = MagicMock()
    second_filter = second_query.filter.return_value
    second_filter.first.return_value = source

    db.query.side_effect = [first_query, second_query]

    with (
        patch("app.services.source_control.require_source_enabled"),
        patch(
            "app.ingestion.source_adapter_factory.build_adapter"
        ) as build_adapter_mock,
        patch("app.ingestion.source_registry_ctl.update_source_health"),
        patch(
            "app.api.routes.admin_ingestion.log_mutation",
            side_effect=RuntimeError("audit down"),
        ),
        patch("app.core.config.get_settings", return_value=SimpleNamespace()),
    ):
        adapter = MagicMock()
        adapter.run.side_effect = RuntimeError("adapter exploded")
        build_adapter_mock.return_value = adapter

        with pytest.raises(HTTPException) as exc_info:
            retry_ingestion_run(
                run_id=22,
                request=MagicMock(),
                db=db,
                actor=actor,
            )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Audit logging failed; mutation aborted"
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
