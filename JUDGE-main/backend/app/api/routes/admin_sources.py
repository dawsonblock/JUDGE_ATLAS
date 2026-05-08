"""Admin source registry management endpoints.

Manage ingestion sources: enable/disable, configure rate limits,
view health status, and control trust tiers.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.auth.admin import require_admin_token, require_source_admin, log_mutation
from app.auth.actor import AdminActor
from app.core.rate_limit import rate_limit_admin
from app.db.session import get_db
from app.models.entities import IngestionRun, SourceRegistry
from app.ingestion.statuses import COMPLETED, COMPLETED_WITH_ERRORS, COMPLETED_WITH_WARNINGS, FAILED, RUNNING, PENDING, QUARANTINED
from app.ingestion.source_registry_ctl import update_source_health

router = APIRouter(prefix="/api/admin/sources", tags=["admin"])


class SourceUpdateRequest(BaseModel):
    """Request to update source configuration."""

    is_active: bool | None = None
    rate_limit_rpm: int | None = Field(None, ge=1, le=10000)
    source_tier: str | None = Field(
        None,
        pattern=r"^(court_record|official_police_open_data|official_government_statistics|verified_news_context|news_only_context)$",
    )
    admin_notes: str | None = None
    config_json: str | None = None
    auto_publish_enabled: bool | None = None
    requires_manual_review: bool | None = None
    # New Canada-first metadata fields
    priority: int | None = Field(None, ge=1, le=100)
    base_url: str | None = Field(None, max_length=2048)
    allowed_domains: str | None = None  # JSON array
    refresh_interval_minutes: int | None = Field(None, ge=1)
    parser: str | None = Field(None, max_length=120)
    parser_version: str | None = Field(None, max_length=32)
    automation_status: str | None = Field(None, max_length=64)


class SourceHealthMetrics(BaseModel):
    """Health metrics for a source."""

    health_score: float  # 0.0-1.0
    last_successful_fetch: datetime | None
    last_error: str | None
    last_error_at: datetime | None
    last_ingested_at: datetime | None
    recent_run_count: int
    recent_error_count: int


class SourceResponse(BaseModel):
    """Source registry entry response."""

    id: int
    source_key: str
    source_name: str
    source_type: str
    country: str | None
    province_state: str | None
    city: str | None
    source_tier: str
    is_active: bool
    rate_limit_rpm: int | None
    health_score: float
    last_successful_fetch: datetime | None
    last_ingested_at: datetime | None
    admin_notes: str | None
    auto_publish_enabled: bool
    requires_manual_review: bool
    created_at: datetime
    updated_at: datetime
    # Canada-first metadata fields
    jurisdiction: str | None = None
    category: str | None = None
    priority: int = 50
    enabled_default: bool = False
    public_record_authority: str = "unknown"
    base_url: str | None = None
    allowed_domains: str | None = None
    refresh_interval_minutes: int | None = None
    parser: str | None = None
    creates: str | None = None
    public_publish_default: bool = False
    terms_url: str | None = None
    source_class: str | None = None
    parser_version: str | None = None
    automation_status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class IngestionRunSummary(BaseModel):
    """Summary of an ingestion run."""

    id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    fetched_count: int
    parsed_count: int
    persisted_count: int
    error_count: int

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[SourceResponse])
def list_sources(
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
    is_active: bool | None = Query(None, description="Filter by active status"),
    source_type: str | None = Query(None, description="Filter by source type"),
    country: str | None = Query(None, description="Filter by country"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[SourceRegistry]:
    """List all ingestion sources with optional filters."""
    query = db.query(SourceRegistry)

    if is_active is not None:
        query = query.filter(SourceRegistry.is_active == is_active)
    if source_type:
        query = query.filter(SourceRegistry.source_type == source_type)
    if country:
        query = query.filter(SourceRegistry.country == country)

    sources = query.order_by(SourceRegistry.source_name).offset(skip).limit(limit).all()
    return sources


@router.get("/{source_key}", response_model=SourceResponse)
def get_source(
    source_key: str,
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
) -> SourceRegistry:
    """Get detailed information about a specific source."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    return source


@router.patch(
    "/{source_key}",
    response_model=SourceResponse,
    dependencies=[Depends(rate_limit_admin)],
)
def update_source(
    source_key: str,
    update: SourceUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin),
) -> SourceRegistry:
    """Update source configuration (enable/disable, rate limit, tier, notes).

    Applies strict validation to allowed_domains, base_url, parser, and
    config_json before storing.  Rejects unsafe values (localhost, private IPs,
    unknown parsers, malformed JSON objects).
    """
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    # Strict config validation — reject before any mutation
    from app.ingestion.source_config_validator import validate_source_update
    validation = validate_source_update(
        allowed_domains=update.allowed_domains,
        base_url=update.base_url,
        parser=update.parser,
        config_json=update.config_json,
    )
    if not validation.ok:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Source configuration validation failed.",
                "errors": validation.to_dict()["errors"],
            },
        )

    # Guard: only machine_ingest sources may be activated
    if update.is_active is True:
        source_class = getattr(source, "source_class", None)
        if source_class != "machine_ingest":
            next_action = _SOURCE_CLASS_NEXT_ACTION.get(
                source_class, "Classify this source before enabling."
            )
            raise HTTPException(
                status_code=422,
                detail=f"Source '{source_key}' has class {source_class!r} and cannot be "
                       f"activated. {next_action}",
            )

    # Apply updates
    if update.is_active is not None:
        source.is_active = update.is_active
    if update.rate_limit_rpm is not None:
        source.rate_limit_rpm = update.rate_limit_rpm
    if update.source_tier is not None:
        source.source_tier = update.source_tier
    if update.admin_notes is not None:
        source.admin_notes = update.admin_notes
    if update.config_json is not None:
        source.config_json = update.config_json
    if update.auto_publish_enabled is not None:
        source.auto_publish_enabled = update.auto_publish_enabled
    if update.requires_manual_review is not None:
        source.requires_manual_review = update.requires_manual_review
    if update.priority is not None:
        source.priority = update.priority
    if update.base_url is not None:
        source.base_url = update.base_url
    if update.allowed_domains is not None:
        source.allowed_domains = update.allowed_domains
    if update.refresh_interval_minutes is not None:
        source.refresh_interval_minutes = update.refresh_interval_minutes
    if update.parser is not None:
        source.parser = update.parser
    if update.parser_version is not None:
        source.parser_version = update.parser_version
    if update.automation_status is not None:
        source.automation_status = update.automation_status

    source.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(source)

    # Log the mutation
    log_mutation(
        action="source.update",
        entity_type="source_registry",
        entity_id=source.source_key,
        payload=update.model_dump(exclude_unset=True),
        request=request,
        actor=actor,
    )

    return source


@router.post(
    "/{source_key}/enable",
    response_model=SourceResponse,
    dependencies=[Depends(rate_limit_admin)],
)
def enable_source(
    source_key: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin),
) -> SourceRegistry:
    """Enable a source for ingestion."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    source_class = getattr(source, "source_class", None)
    if source_class != "machine_ingest":
        next_action = _SOURCE_CLASS_NEXT_ACTION.get(
            source_class, "Classify this source before enabling."
        )
        raise HTTPException(
            status_code=422,
            detail=f"Source '{source_key}' has class {source_class!r} and cannot be "
                   f"enabled for automated ingestion. {next_action}",
        )

    source.is_active = True
    source.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(source)

    # Log the mutation
    log_mutation(
        action="source.enable",
        entity_type="source_registry",
        entity_id=source.source_key,
        payload={"is_active": True},
        request=request,
        actor=actor,
    )

    return source


@router.post(
    "/{source_key}/disable",
    response_model=SourceResponse,
    dependencies=[Depends(rate_limit_admin)],
)
def disable_source(
    source_key: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin),
) -> SourceRegistry:
    """Disable a source (stops active crawls)."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    source.is_active = False
    source.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(source)

    # Log the mutation
    log_mutation(
        action="source.disable",
        entity_type="source_registry",
        entity_id=source.source_key,
        payload={"is_active": False},
        request=request,
        actor=actor,
    )

    return source


@router.get("/{source_key}/health", response_model=SourceHealthMetrics)
def get_source_health(
    source_key: str,
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
    days: int = Query(7, ge=1, le=90, description="Lookback period in days"),
) -> dict[str, Any]:
    """Get health metrics for a source."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    # Calculate recent run metrics
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    run_stats = (
        db.query(
            func.count(IngestionRun.id).label("total_runs"),
            func.sum(IngestionRun.error_count).label("total_errors"),
        )
        .filter(
            IngestionRun.source_name == source_key, IngestionRun.started_at >= cutoff
        )
        .first()
    )

    return {
        "health_score": source.health_score,
        "last_successful_fetch": source.last_successful_fetch,
        "last_error": source.last_error,
        "last_error_at": source.last_error_at,
        "last_ingested_at": source.last_ingested_at,
        "recent_run_count": run_stats.total_runs or 0,
        "recent_error_count": run_stats.total_errors or 0,
    }


class RunResult(BaseModel):
    """Result of a synchronous ingestion run.

    The run is executed synchronously in the request thread and the response
    is returned only after the run completes (or fails).  There is no
    background job queue; job_id is always None.
    """

    run_id: int | None  # database ID of the IngestionRun record
    job_id: str | None = None  # always None — no async job queue
    run_mode: str = "synchronous"
    source_key: str
    status: str  # completed / completed_with_errors / quarantined / failed
    records_fetched: int = 0
    records_skipped: int = 0
    adapter_records: int = 0
    created_records: int = 0
    duplicates_skipped: int = 0
    persisted_incidents: int = 0
    persisted_review_items: int = 0
    snapshots_written: int = 0
    pipeline_stage: str = ""
    contract_violations: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    success: bool = False


_SOURCE_CLASS_NEXT_ACTION: dict[str | None, str] = {
    "portal_reference": "Configure a supported machine-readable endpoint and adapter before enabling runs.",
    "manual_reference": "Use as manual reference evidence only.",
    "requires_api_key": "Configure the required API key before enabling machine ingestion.",
    "disabled_stub": "Implement and test the adapter before marking this source runnable.",
    "needs_endpoint_configuration": "Set an exact machine-readable endpoint before enabling runs.",
    None: "Source class is not set; classify this source before running.",
}


@router.post(
    "/{source_key}/run",
    response_model=RunResult,
    dependencies=[Depends(rate_limit_admin)],
)
def run_source_now(
    source_key: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin),
) -> dict[str, Any]:
    """Execute an ingestion run for a source synchronously and return the result.

    The run is executed in the request thread and the response is returned
    only after the adapter finishes and results are persisted.  There is no
    background job queue; the response always contains the final status.
    Use GET /api/admin/ingestion-runs/{run_id} to retrieve the run record
    after the fact.
    """
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    if not source.is_active:
        raise HTTPException(
            status_code=409,
            detail=f"Source '{source_key}' is disabled; enable it before running.",
        )

    source_class = getattr(source, "source_class", None)
    if source_class != "machine_ingest":
        raise HTTPException(
            status_code=422,
            detail={
                "source_key": source_key,
                "source_class": source_class,
                "reason": "Only machine_ingest sources can be run.",
                "next_action": _SOURCE_CLASS_NEXT_ACTION.get(
                    source_class, "Unknown source class; classify before running."
                ),
            },
        )

    from app.core.config import get_settings
    from app.ingestion.source_adapter_factory import build_adapter
    from app.ingestion.source_runner import persist_ingestion_result

    adapter = build_adapter(source, get_settings())
    if adapter is None:
        raise HTTPException(
            status_code=501,
            detail={
                "source_key": source_key,
                "source_class": source_class,
                "reason": "No registered adapter exists for this machine_ingest source.",
                "next_action": "Implement and test the adapter before enabling source runs.",
            },
        )

    run_record = IngestionRun(
        source_name=source_key,
        started_at=datetime.now(timezone.utc),
        status=RUNNING,
        fetched_count=0,
        parsed_count=0,
        persisted_count=0,
        skipped_count=0,
        error_count=0,
        errors=[],
        pipeline_stage="adapter.run",
    )
    db.add(run_record)
    db.flush()

    try:
        result = adapter.run()
        summary = persist_ingestion_result(db, source, run_record, result)
        errors = list(getattr(result, "errors", []) or [])
        run_record.finished_at = datetime.now(timezone.utc)
        # GUARD: persist_ingestion_result may have set run_record.status = QUARANTINED
        # via quarantine_run() — never overwrite a quarantined status here.
        if run_record.status != QUARANTINED:
            run_record.status = COMPLETED_WITH_ERRORS if errors else COMPLETED
            run_record.pipeline_stage = COMPLETED
        else:
            run_record.pipeline_stage = "quarantine"
        run_record.fetched_count = int(getattr(result, "records_fetched", 0) or 0)
        run_record.parsed_count = len(getattr(result, "created_records", []) or []) + len(
            getattr(result, "review_items", []) or []
        )
        run_record.persisted_count = summary.persisted_incidents + summary.persisted_review_items
        run_record.skipped_count = summary.skipped_duplicates
        run_record.error_count = len(errors)
        run_record.errors = errors
        update_source_health(db, source_key, run_record)
        db.commit()
    except Exception as exc:
        run_record.finished_at = datetime.now(timezone.utc)
        run_record.status = FAILED
        run_record.error_count = 1
        run_record.errors = [str(exc)]
        run_record.pipeline_stage = FAILED
        update_source_health(db, source_key, run_record)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Source run failed: {exc}") from exc

    # Log the run mutation.
    log_mutation(
        action="source.run",
        entity_type="source_registry",
        entity_id=source.source_key,
        payload={"run_id": run_record.id, "source_key": source_key},
        request=request,
        actor=actor,
    )

    return {
        "run_id": run_record.id,
        "job_id": None,
        "run_mode": "synchronous",
        "source_key": source_key,
        "status": run_record.status,
        "records_fetched": run_record.fetched_count,
        "records_skipped": run_record.skipped_count,
        "adapter_records": run_record.parsed_count,
        "created_records": run_record.persisted_count,
        "duplicates_skipped": summary.skipped_duplicates,
        "persisted_incidents": summary.persisted_incidents,
        "persisted_review_items": summary.persisted_review_items,
        "snapshots_written": summary.snapshots_written,
        "pipeline_stage": run_record.pipeline_stage or "",
        "contract_violations": summary.contract_violations,
        "warnings": [],
        "errors": run_record.errors or [],
        "success": run_record.status in (COMPLETED, COMPLETED_WITH_ERRORS, COMPLETED_WITH_WARNINGS),
    }


@router.get("/{source_key}/runs", response_model=list[IngestionRunSummary])
def get_source_runs(
    source_key: str,
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[IngestionRun]:
    """Get ingestion run history for a source."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    runs = (
        db.query(IngestionRun)
        .filter(IngestionRun.source_name == source_key)
        .order_by(desc(IngestionRun.started_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return runs
