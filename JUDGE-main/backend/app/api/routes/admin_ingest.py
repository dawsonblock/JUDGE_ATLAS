"""Admin ingestion endpoint.

Triggers manual ingestion runs for each open-data source.
Guarded by JTA_ENABLE_ADMIN_IMPORTS and admin token.
"""

from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.auth.admin import enforce_jwt_mutation_authority, log_mutation
from app.auth.actor import AdminActor
from app.core.config import get_settings
from app.core.rate_limit import rate_limit_ingestion
from app.core.request_utils import read_upload_file_limited
from app.db.session import get_db
from app.ingestion.gdelt import fetch_gdelt_articles, import_gdelt_articles
from app.ingestion.crime_sources.chicago_socrata import import_chicago_csv
from app.ingestion.crime_sources.toronto import import_toronto_csv
from app.ingestion.crime_sources.saskatoon import import_saskatoon_csv
from app.ingestion.crime_sources.los_angeles import import_la_csv
from app.ingestion.crime_sources.statscan import (
    extract_csv_from_bytes,
    import_statscan_csv,
)
from app.ingestion.crime_sources.fbi_crime_data import import_fbi_json
from app.ingestion.source_keys import COURTLISTENER_BULK, resolve_source_key
from app.ingestion.source_registry_ctl import (
    check_ingestion_allowed,
    require_source_registry,
)
from app.ingestion.statuses import FAILED, PENDING
from app.security.import_authority import require_source_admin_actor

router = APIRouter(prefix="/api/admin/ingest", tags=["admin"])


def _check_csv_row_limit(content: bytes, max_rows: int, source: str) -> None:
    """Raise HTTP 422 if the CSV byte content exceeds the row-count cap.

    Uses newline count as a fast O(n) proxy; subtracts 1 for the header row.
    Raises before the importer processes any rows, preventing DoS via huge
    CSVs that pass the byte-size check but contain millions of tiny rows.
    """
    row_count = content.count(b"\n")
    if row_count > max_rows:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{source} CSV exceeds the maximum allowed row count "
                f"({row_count:,} rows found, limit is {max_rows:,}). "
                "Split the file and re-upload in batches."
            ),
        )


def _check_source_active(source_key: str, source_name: str, db: Session) -> None:
    """Raise HTTP 403 if the source is disabled in SourceRegistry."""
    registry = require_source_registry(db, source_key, source_name)
    allowed, reason = check_ingestion_allowed(registry)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)


@router.post("/gdelt", dependencies=[Depends(rate_limit_ingestion)])
def ingest_gdelt(
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
):
    """Fetch and import GDELT news articles."""
    enforce_jwt_mutation_authority(actor)
    
    settings = get_settings()
    if not settings.gdelt_enabled:
        raise HTTPException(
            status_code=403,
            detail="GDELT global circuit breaker off (set JTA_GDELT_ENABLED=true). Ensure source is also active in SourceRegistry.",
        )
    source_key = resolve_source_key("gdelt")
    _check_source_active(source_key, "GDELT News Feed", db)
    articles = fetch_gdelt_articles()
    if articles is None:
        raise HTTPException(status_code=502, detail="GDELT fetch failed")
    result = import_gdelt_articles(db, articles)
    
    # Log the mutation
    log_mutation(
        action="ingest.gdelt",
        entity_type="ingestion_run",
        entity_id=str(result.run_id) if hasattr(result, 'run_id') else None,
        payload={
            "articles_fetched": len(articles) if articles else 0,
            "persisted_incidents": result.persisted_incidents,
            "skipped_duplicates": result.skipped_duplicates,
        },
        request=request,
        actor=actor,
    )
    
    return result.__dict__


@router.post("/chicago")
async def ingest_chicago(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
):
    """Import Chicago Data Portal crime CSV upload."""
    enforce_jwt_mutation_authority(actor)
    
    settings = get_settings()
    if not settings.local_feeds_enabled:
        raise HTTPException(
            status_code=403,
            detail="Local feeds circuit breaker off (set JTA_LOCAL_FEEDS_ENABLED=true). Ensure source is also active in SourceRegistry.",
        )
    source_key = resolve_source_key("chicago_crime")
    _check_source_active(source_key, "Chicago Data Portal", db)
    content = await read_upload_file_limited(file, settings.max_csv_upload_size)
    _check_csv_row_limit(content, settings.max_csv_rows, "Chicago")
    stream = io.StringIO(content.decode("utf-8-sig"))
    result = import_chicago_csv(db, stream)
    
    # Log the mutation
    log_mutation(
        action="ingest.chicago",
        entity_type="ingestion_run",
        entity_id=str(result.run_id) if hasattr(result, 'run_id') else None,
        payload={
            "filename": file.filename,
            "persisted_incidents": result.persisted_incidents,
            "skipped_duplicates": result.skipped_duplicates,
        },
        request=request,
        actor=actor,
    )
    
    return result.__dict__


@router.post("/toronto")
async def ingest_toronto(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
):
    """Import Toronto Police CSV upload."""
    enforce_jwt_mutation_authority(actor)
    
    settings = get_settings()
    if not settings.local_feeds_enabled:
        raise HTTPException(
            status_code=403,
            detail="Local feeds circuit breaker off (set JTA_LOCAL_FEEDS_ENABLED=true). Ensure source is also active in SourceRegistry.",
        )
    source_key = resolve_source_key("toronto_crime")
    _check_source_active(source_key, "Toronto Police Service", db)
    content = await read_upload_file_limited(file, settings.max_csv_upload_size)
    _check_csv_row_limit(content, settings.max_csv_rows, "Toronto")
    stream = io.StringIO(content.decode("utf-8-sig"))
    result = import_toronto_csv(db, stream)
    
    # Log the mutation
    log_mutation(
        action="ingest.toronto",
        entity_type="ingestion_run",
        entity_id=str(result.run_id) if hasattr(result, 'run_id') else None,
        payload={
            "filename": file.filename,
            "persisted_incidents": result.persisted_incidents,
            "skipped_duplicates": result.skipped_duplicates,
        },
        request=request,
        actor=actor,
    )
    
    return result.__dict__


@router.post("/saskatoon")
async def ingest_saskatoon(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
):
    """Import Saskatoon Police CSV upload."""
    enforce_jwt_mutation_authority(actor)
    
    settings = get_settings()
    if not settings.local_feeds_enabled:
        raise HTTPException(
            status_code=403,
            detail="Local feeds circuit breaker off (set JTA_LOCAL_FEEDS_ENABLED=true). Ensure source is also active in SourceRegistry.",
        )
    source_key = resolve_source_key("saskatoon_crime")
    _check_source_active(source_key, "Saskatoon Police Service", db)
    content = await read_upload_file_limited(file, settings.max_csv_upload_size)
    _check_csv_row_limit(content, settings.max_csv_rows, "Saskatoon")
    stream = io.StringIO(content.decode("utf-8-sig"))
    result = import_saskatoon_csv(db, stream)
    
    # Log the mutation
    log_mutation(
        action="ingest.saskatoon",
        entity_type="ingestion_run",
        entity_id=str(result.run_id) if hasattr(result, 'run_id') else None,
        payload={
            "filename": file.filename,
            "persisted_count": result.persisted_count,
            "skipped_count": result.skipped_count,
        },
        request=request,
        actor=actor,
    )
    
    return result.__dict__


@router.post("/los-angeles")
async def ingest_los_angeles(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
):
    """Import LA Open Data crime CSV upload."""
    enforce_jwt_mutation_authority(actor)
    
    settings = get_settings()
    if not settings.local_feeds_enabled:
        raise HTTPException(
            status_code=403,
            detail="Local feeds circuit breaker off (set JTA_LOCAL_FEEDS_ENABLED=true). Ensure source is also active in SourceRegistry.",
        )
    source_key = resolve_source_key("la_crime")
    _check_source_active(source_key, "LA Open Data", db)
    content = await read_upload_file_limited(file, settings.max_csv_upload_size)
    _check_csv_row_limit(content, settings.max_csv_rows, "Los Angeles")
    stream = io.StringIO(content.decode("utf-8-sig"))
    result = import_la_csv(db, stream)
    
    # Log the mutation
    log_mutation(
        action="ingest.los_angeles",
        entity_type="ingestion_run",
        entity_id=str(result.run_id) if hasattr(result, 'run_id') else None,
        payload={
            "filename": file.filename,
            "persisted_incidents": result.persisted_incidents,
            "skipped_duplicates": result.skipped_duplicates,
        },
        request=request,
        actor=actor,
    )
    
    return result.__dict__


@router.post("/statscan")
async def ingest_statscan(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
):
    """Import Statistics Canada CSV upload."""
    enforce_jwt_mutation_authority(actor)
    
    settings = get_settings()
    if not settings.statscan_enabled:
        raise HTTPException(
            status_code=403,
            detail="StatsCan global circuit breaker off (set JTA_STATSCAN_ENABLED=true). Ensure source is also active in SourceRegistry.",
        )
    source_key = resolve_source_key("statscan")
    _check_source_active(source_key, "Statistics Canada", db)
    content = await read_upload_file_limited(file, settings.max_csv_upload_size)
    csv_text = extract_csv_from_bytes(content)
    if csv_text is None:
        raise HTTPException(
            status_code=422, detail="StatsCan ZIP contained no CSV files"
        )
    _check_csv_row_limit(csv_text.encode(), settings.max_csv_rows, "StatsCan")
    stream = io.StringIO(csv_text)
    result = import_statscan_csv(db, stream)
    
    # Log the mutation
    log_mutation(
        action="ingest.statscan",
        entity_type="ingestion_run",
        entity_id=str(result.run_id) if hasattr(result, 'run_id') else None,
        payload={
            "filename": file.filename,
            "persisted_incidents": result.persisted_incidents,
            "skipped_duplicates": result.skipped_duplicates,
        },
        request=request,
        actor=actor,
    )
    
    return result.__dict__


@router.post("/fbi")
def ingest_fbi(
    payload: list[dict],
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
):
    """Import FBI Crime Data JSON payload."""
    enforce_jwt_mutation_authority(actor)
    
    settings = get_settings()
    if not settings.fbi_crime_enabled:
        raise HTTPException(
            status_code=403,
            detail="FBI Crime global circuit breaker off (set JTA_FBI_CRIME_ENABLED=true). Ensure source is also active in SourceRegistry.",
        )
    source_key = resolve_source_key("fbi_crime")
    _check_source_active(source_key, "FBI Crime Data", db)
    result = import_fbi_json(db, payload)
    
    # Log the mutation
    log_mutation(
        action="ingest.fbi",
        entity_type="ingestion_run",
        entity_id=str(result.run_id) if hasattr(result, 'run_id') else None,
        payload={
            "records_imported": len(payload) if payload else 0,
            "persisted_incidents": result.persisted_incidents,
            "skipped_duplicates": result.skipped_duplicates,
        },
        request=request,
        actor=actor,
    )
    
    return result.__dict__


# ---------------------------------------------------------------------------
# CourtListener bulk-data endpoints
# ---------------------------------------------------------------------------


@router.get("/courtlistener-bulk/runs")
def cl_bulk_runs(
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
):
    """List all CourtListener bulk import run records."""
    enforce_jwt_mutation_authority(actor)
    _check_source_active(COURTLISTENER_BULK, "CourtListener Bulk", db)
    from sqlalchemy import select as _select
    from app.models.entities import CourtListenerBulkRun

    runs = db.scalars(
        _select(CourtListenerBulkRun).order_by(CourtListenerBulkRun.id.desc())
    ).all()
    return [
        {
            "id": r.id,
            "snapshot_date": r.snapshot_date,
            "file_name": r.file_name,
            "status": r.status,
            "rows_read": r.rows_read,
            "rows_persisted": r.rows_persisted,
            "rows_skipped": r.rows_skipped,
            "errors": (r.errors or [])[:10],
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": (r.finished_at.isoformat() if r.finished_at else None),
        }
        for r in runs
    ]


@router.post("/courtlistener-bulk/list", dependencies=[Depends(rate_limit_ingestion)])
def cl_bulk_list(
    request: Request = None,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
):
    """List CSV files available in the configured bulk_data_dir."""
    enforce_jwt_mutation_authority(actor)
    _check_source_active(COURTLISTENER_BULK, "CourtListener Bulk", db)
    import os

    settings = get_settings()
    data_dir = settings.courtlistener_bulk_data_dir
    if not os.path.isdir(data_dir):
        raise HTTPException(
            status_code=404,
            detail=f"bulk_data_dir not found: {data_dir}",
        )
    files = [f for f in sorted(os.listdir(data_dir)) if f.endswith(".csv")]
    log_mutation(
        action="ingest.courtlistener_bulk_list",
        entity_type="courtlistener_bulk_snapshot",
        entity_id=str(settings.courtlistener_bulk_snapshot_date or ""),
        payload={"data_dir": data_dir, "file_count": len(files)},
        request=request,
        actor=actor,
    )
    return {
        "data_dir": data_dir,
        "snapshot_date": settings.courtlistener_bulk_snapshot_date,
        "files": files,
    }


@router.post("/courtlistener-bulk/import", dependencies=[Depends(rate_limit_ingestion)])
def cl_bulk_import(
    payload: dict | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
):
    """Trigger bulk normalization for a snapshot date.

    Body (optional JSON):
        {"snapshot_date": "2026-03-31", "files": ["courts","dockets"],
         "force": false, "include_opinions": false}
    """
    enforce_jwt_mutation_authority(actor)
    _check_source_active(COURTLISTENER_BULK, "CourtListener Bulk", db)
    import os
    from app.ingestion.courtlistener_bulk_normalizer import (
        get_or_create_bulk_run,
        mark_run_done,
        mark_run_failed,
        mark_run_started,
        normalize_clusters,
        normalize_courts,
        normalize_dockets,
        normalize_opinions,
        normalize_people,
        normalize_positions,
    )

    _NORMALIZERS = {
        "courts": normalize_courts,
        "people-db-people": normalize_people,
        "people-db-positions": normalize_positions,
        "dockets": normalize_dockets,
        "opinion-clusters": normalize_clusters,
        "opinions": normalize_opinions,
    }
    _ORDER = [
        "courts",
        "people-db-people",
        "people-db-positions",
        "dockets",
        "opinion-clusters",
    ]

    settings = get_settings()
    body = payload or {}
    snapshot_date = str(
        body.get("snapshot_date") or settings.courtlistener_bulk_snapshot_date or ""
    )
    if not snapshot_date:
        raise HTTPException(status_code=422, detail="snapshot_date required")
    force = bool(body.get("force", False))
    include_opinions = bool(
        body.get("include_opinions", settings.courtlistener_bulk_include_opinions)
    )
    enabled = [
        s.strip()
        for s in str(
            body.get("files") or settings.courtlistener_bulk_enabled_files
        ).split(",")
        if s.strip()
    ]
    ordered = [s for s in _ORDER if s in enabled]
    if include_opinions:
        ordered.append("opinions")

    data_dir = settings.courtlistener_bulk_data_dir
    results = []
    for stem in ordered:
        csv_path = None
        for fname in sorted(os.listdir(data_dir)):
            if fname.startswith(stem) and fname.endswith(".csv"):
                csv_path = os.path.join(data_dir, fname)
                break
        if not csv_path:
            results.append({"file": stem, "status": "skipped_no_file"})
            continue

        run = get_or_create_bulk_run(db, snapshot_date, stem)
        if run.status in ("done", "done_with_errors") and not force:
            results.append(
                {
                    "file": stem,
                    "status": "skipped_already_done",
                    "rows_persisted": run.rows_persisted,
                }
            )
            continue
        if force and run.status != PENDING:
            db.delete(run)
            db.flush()
            run = get_or_create_bulk_run(db, snapshot_date, stem)

        mark_run_started(db, run)
        try:
            with open(csv_path, encoding="utf-8", errors="replace") as fh:
                result = _NORMALIZERS[stem](
                    db,
                    fh,
                    settings.courtlistener_bulk_import_batch_size,
                    run.id,
                    stem,
                    snapshot_date,
                )
            mark_run_done(db, run, result)
            db.commit()
            results.append(
                {
                    "file": stem,
                    "status": run.status,
                    "rows_read": result.rows_read,
                    "rows_persisted": result.rows_persisted,
                    "rows_skipped": result.rows_skipped,
                    "error_count": len(result.errors),
                }
            )
        except Exception as exc:
            mark_run_failed(db, run, exc)
            db.commit()
            results.append({"file": stem, "status": FAILED, "error": str(exc)})

    # Log the mutation
    log_mutation(
        action="ingest.courtlistener_bulk",
        entity_type="courtlistener_bulk_run",
        entity_id=str(snapshot_date),
        payload={
            "snapshot_date": snapshot_date,
            "files_processed": len([r for r in results if r["status"] != "skipped_no_file"]),
            "results_summary": results,
        },
        request=request,
        actor=actor,
    )

    return {"snapshot_date": snapshot_date, "results": results}


@router.post("/courtlistener-bulk/normalize")
def cl_bulk_normalize(
    payload: dict | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin_actor),
):
    """Re-run normalization only (skips file-existence check for already-imported rows).

    Delegates to /import with force=True but only for already-downloaded files.
    """
    _check_source_active(COURTLISTENER_BULK, "CourtListener Bulk", db)
    body = dict(payload or {})
    body["force"] = True
    log_mutation(
        action="ingest.courtlistener_bulk_normalize",
        entity_type="courtlistener_bulk_snapshot",
        entity_id=str(body.get("snapshot_date") or ""),
        payload={"force": True, "requested_files": body.get("files")},
        request=request,
        actor=actor,
    )
    return cl_bulk_import(body, request, db, actor)
