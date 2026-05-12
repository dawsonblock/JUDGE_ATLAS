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

from app.auth.admin import enforce_jwt_mutation_authority, log_mutation, require_admin_token
from app.auth.actor import AdminActor
from app.core.rate_limit import rate_limit_admin
from app.db.session import get_db
from app.models.entities import IngestionRun, SourceRegistry
from app.ingestion.statuses import COMPLETED, COMPLETED_WITH_WARNINGS, FAILED, RUNNING, PENDING, QUARANTINED
from app.ingestion.automation_statuses import ENABLEABLE_STATUSES, MACHINE_READY_ENABLED, MACHINE_READY_DISABLED
from app.ingestion.source_registry_ctl import update_source_health
from app.security.import_authority import require_source_admin_actor

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
    enable_ready: bool = False
    enable_blockers: list[str] = Field(default_factory=list)

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
) -> list[SourceResponse]:
    """List all ingestion sources with optional filters."""
    query = db.query(SourceRegistry)

    if is_active is not None:
        query = query.filter(SourceRegistry.is_active == is_active)
    if source_type:
        query = query.filter(SourceRegistry.source_type == source_type)
    if country:
        query = query.filter(SourceRegistry.country == country)

    sources = query.order_by(SourceRegistry.source_name).offset(skip).limit(limit).all()
    return [_to_source_response(source) for source in sources]


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

    return _to_source_response(source)


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
    actor: AdminActor = Depends(require_source_admin_actor),
) -> SourceRegistry:
    """Update source configuration (enable/disable, rate limit, tier, notes).

    Applies strict validation to allowed_domains, base_url, parser, and
    config_json before storing.  Rejects unsafe values (localhost, private IPs,
    unknown parsers, malformed JSON objects).
    """
    enforce_jwt_mutation_authority(actor)

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

    # Guard: activation state transitions are only allowed via explicit
    # enable/disable routes so all safety/audit controls are centralized.
    if update.is_active is not None:
        raise HTTPException(
            status_code=422,
            detail=(
                "is_active cannot be changed via PATCH. "
                "Use /enable or /disable endpoints."
            ),
        )

    # Apply updates
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
    try:
        db.flush()
        log_mutation(
            action="source.update",
            entity_type="source_registry",
            entity_id=source.source_key,
            payload=update.model_dump(exclude_unset=True),
            request=request,
            actor=actor,
            db=db,
            fail_closed=True,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist source update audit trail: {exc}",
        ) from exc
    db.refresh(source)

    return _to_source_response(source)


@router.post(
    "/{source_key}/enable",
    response_model=SourceResponse,
    dependencies=[Depends(rate_limit_admin)],
)
def enable_source(
    source_key: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
) -> SourceRegistry:
    """Enable a source for ingestion."""
    enforce_jwt_mutation_authority(actor)

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

    auto_status = getattr(source, "automation_status", None)
    if auto_status not in ENABLEABLE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Source '{source_key}' has automation_status={auto_status!r} and cannot "
                f"be enabled. Only sources with automation_status in "
                f"{sorted(ENABLEABLE_STATUSES)} may be enabled."
            ),
        )

    # Validate required metadata fields before enabling.
    missing: list[str] = []
    if not source.parser:
        missing.append("parser")
    if not source.parser_version:
        missing.append("parser_version")
    if not source.allowed_domains or source.allowed_domains in ("[]", ""):
        missing.append("allowed_domains")
    if not source.base_url:
        missing.append("base_url")
    if getattr(source, "public_record_authority", None) in (None, "", "unknown"):
        missing.append("public_record_authority")
    if getattr(source, "terms_url", None) is None:
        missing.append("terms_url")
    if getattr(source, "requires_manual_review", None) is None:
        missing.append("requires_manual_review")
    if getattr(source, "public_publish_default", None) is None:
        missing.append("public_publish_default")
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "source_key": source_key,
                "reason": f"Source is missing required fields: {missing}",
                "missing_fields": missing,
            },
        )

    from app.core.config import get_settings
    from app.ingestion.source_adapter_factory import build_adapter, missing_required_secret_for_parser

    settings = get_settings()
    missing_secret = missing_required_secret_for_parser(source.parser, settings)
    if missing_secret is not None:
        raise HTTPException(status_code=422, detail=_secret_gate_detail(source, missing_secret))

    if build_adapter(source, settings) is None:
        raise HTTPException(
            status_code=422,
            detail={
                "source_key": source_key,
                "reason": "No registered adapter. Implement and register adapter before enabling.",
            },
        )

    source.is_active = True
    source.automation_status = MACHINE_READY_ENABLED
    source.updated_at = datetime.now(timezone.utc)
    try:
        db.flush()
        log_mutation(
            action="source.enable",
            entity_type="source_registry",
            entity_id=source.source_key,
            payload={"is_active": True, "automation_status": MACHINE_READY_ENABLED},
            request=request,
            actor=actor,
            db=db,
            fail_closed=True,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist source enable audit trail: {exc}",
        ) from exc
    db.refresh(source)

    return _to_source_response(source)


@router.post(
    "/{source_key}/disable",
    response_model=SourceResponse,
    dependencies=[Depends(rate_limit_admin)],
)
def disable_source(
    source_key: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
) -> SourceRegistry:
    """Disable a source (stops active crawls)."""
    enforce_jwt_mutation_authority(actor)

    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    # Transition automation_status when disabling an enabled source.
    if getattr(source, "automation_status", None) == MACHINE_READY_ENABLED:
        source.automation_status = MACHINE_READY_DISABLED

    source.is_active = False
    source.updated_at = datetime.now(timezone.utc)
    try:
        db.flush()
        log_mutation(
            action="source.disable",
            entity_type="source_registry",
            entity_id=source.source_key,
            payload={"is_active": False},
            request=request,
            actor=actor,
            db=db,
            fail_closed=True,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist source disable audit trail: {exc}",
        ) from exc
    db.refresh(source)

    return _to_source_response(source)


def _to_source_response(source: SourceRegistry) -> SourceResponse:
    enable_blockers = _compute_enable_blockers(source)
    try:
        payload = SourceResponse.model_validate(source).model_dump()
        payload["enable_ready"] = len(enable_blockers) == 0
        payload["enable_blockers"] = enable_blockers
        return SourceResponse.model_validate(payload)
    except Exception:
        # Unit tests pass MagicMock-backed source objects into route functions.
        # Keep route behavior testable by attaching readiness hints directly.
        setattr(source, "enable_ready", len(enable_blockers) == 0)
        setattr(source, "enable_blockers", enable_blockers)
        return source  # type: ignore[return-value]


def _compute_enable_blockers(source: SourceRegistry) -> list[str]:
    blockers: list[str] = []

    source_class = getattr(source, "source_class", None)
    if source_class != "machine_ingest":
        blockers.append(
            _SOURCE_CLASS_NEXT_ACTION.get(
                source_class,
                "Only machine_ingest sources can be enabled.",
            )
        )

    auto_status = getattr(source, "automation_status", None)
    if auto_status not in ENABLEABLE_STATUSES:
        blockers.append(
            f"automation_status={auto_status!r} is not enableable; must be one of {sorted(ENABLEABLE_STATUSES)}"
        )

    if not source.parser:
        blockers.append("parser is required")
    if not source.parser_version:
        blockers.append("parser_version is required")
    if not source.allowed_domains or source.allowed_domains in ("[]", ""):
        blockers.append("allowed_domains is required")
    if not source.base_url:
        blockers.append("base_url is required")
    if getattr(source, "public_record_authority", None) in (None, "", "unknown"):
        blockers.append("public_record_authority is required")
    if getattr(source, "terms_url", None) is None:
        blockers.append("terms_url is required")
    if getattr(source, "requires_manual_review", None) is None:
        blockers.append("requires_manual_review is required")
    if getattr(source, "public_publish_default", None) is None:
        blockers.append("public_publish_default is required")

    if source.parser:
        try:
            from app.core.config import get_settings
            from app.ingestion.source_adapter_factory import (
                build_adapter,
                missing_required_secret_for_parser,
            )

            settings = get_settings()
            missing_secret = missing_required_secret_for_parser(source.parser, settings)
            if missing_secret is not None:
                blockers.append(f"missing required secret: {missing_secret}")
            elif build_adapter(source, settings) is None:
                blockers.append("no registered adapter for parser/source")
        except Exception as exc:  # pragma: no cover - defensive diagnostic fallback
            blockers.append(f"readiness check error: {exc}")

    return blockers


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
    status: str  # completed / completed_with_warnings / quarantined / failed
    records_fetched: int = 0
    records_skipped: int = 0
    adapter_records: int = 0
    created_records: int = 0
    duplicates_skipped: int = 0
    persisted_incidents: int = 0
    persisted_review_items: int = 0
    quarantined_count: int = 0
    failed_records: int = 0
    review_items_skipped: int = 0
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


def _secret_gate_detail(source: SourceRegistry, missing_secret: str) -> dict[str, Any]:
    return {
        "source_key": source.source_key,
        "parser": source.parser,
        "automation_status": getattr(source, "automation_status", None),
        "reason": f"Source requires {missing_secret} before it can be enabled or run.",
        "missing_secret": missing_secret,
        "next_action": f"Set {missing_secret} and retry.",
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
    actor: AdminActor = Depends(require_source_admin_actor),
) -> dict[str, Any]:
    """Execute an ingestion run for a source synchronously and return the result.

    The run is executed in the request thread and the response is returned
    only after the adapter finishes and results are persisted.  There is no
    background job queue; the response always contains the final status.
    Use GET /api/admin/ingestion-runs/{run_id} to retrieve the run record
    after the fact.
    """
    enforce_jwt_mutation_authority(actor)

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

    from app.ingestion.source_registry_ctl import check_ingestion_allowed
    allowed, reason = check_ingestion_allowed(source)
    if not allowed:
        raise HTTPException(
            status_code=422,
            detail={
                "source_key": source_key,
                "reason": reason,
                "next_action": "Fix the source automation_status before running.",
            },
        )

    from app.core.config import get_settings
    from app.ingestion.source_adapter_factory import build_adapter, missing_required_secret_for_parser
    from app.ingestion.source_runner import persist_ingestion_result

    settings = get_settings()
    missing_secret = missing_required_secret_for_parser(source.parser, settings)
    if missing_secret is not None:
        raise HTTPException(status_code=422, detail=_secret_gate_detail(source, missing_secret))

    adapter = build_adapter(source, settings)
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
    db.commit()

    run_id = run_record.id

    try:
        result = adapter.run()
        summary = persist_ingestion_result(db, source, run_record, result)
        errors = list(getattr(result, "errors", []) or [])
        run_record.finished_at = datetime.now(timezone.utc)
        # GUARD: persist_ingestion_result may have set run_record.status = QUARANTINED
        # via quarantine_run() — never overwrite a quarantined status here.
        if run_record.status != QUARANTINED:
            run_record.status = COMPLETED_WITH_WARNINGS if errors else COMPLETED
            run_record.pipeline_stage = COMPLETED
        else:
            run_record.pipeline_stage = "quarantine"
        run_record.fetched_count = int(getattr(result, "records_fetched", 0) or 0)
        run_record.parsed_count = (
            len(getattr(result, "created_records", []) or [])
            + len(getattr(result, "legal_instruments", []) or [])
            + len(getattr(result, "review_items", []) or [])
        )
        run_record.persisted_count = (
            getattr(summary, "persisted_incidents", 0)
            + getattr(summary, "persisted_legal_instruments", 0)
            + getattr(summary, "persisted_review_items", 0)
        )
        run_record.skipped_count = summary.skipped_duplicates
        run_record.error_count = len(errors)
        run_record.errors = errors
        update_source_health(db, source_key, run_record, auto_commit=False)
        log_mutation(
            action="source.run",
            entity_type="source_registry",
            entity_id=source.source_key,
            payload={"run_id": run_id, "source_key": source_key},
            request=request,
            actor=actor,
            db=db,
            fail_closed=True,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        failed_run = db.merge(run_record)
        failed_run.finished_at = datetime.now(timezone.utc)
        failed_run.status = FAILED
        failed_run.error_count = 1
        failed_run.errors = [str(exc)]
        failed_run.pipeline_stage = FAILED
        update_source_health(db, source_key, failed_run, auto_commit=False)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Source run failed: {exc}") from exc

    return {
        "run_id": run_id,
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
        "quarantined_count": summary.quarantined_count,
        "failed_records": summary.failed_records,
        "review_items_skipped": summary.review_items_skipped,
        "snapshots_written": summary.snapshots_written,
        "pipeline_stage": run_record.pipeline_stage or "",
        "contract_violations": summary.contract_violations,
        "warnings": summary.warnings,
        "errors": run_record.errors or [],
        "success": run_record.status in (COMPLETED, COMPLETED_WITH_WARNINGS),
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
