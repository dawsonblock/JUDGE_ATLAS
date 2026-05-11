# Judge Atlas Current Status

Date: 2026-05-10
Release Status: ALPHA (proof-hardened, not ready for production deployment)

## Classification

- Current status: proof-hardened alpha legal/map evidence platform.
- Not ready for production deployment.
- Does not hold legal authority.
- Not a legal decision-maker.
- Evidence snapshots are authoritative; memory is derivative.
- AI is reviewer assistance only.

## Runtime/Authority Boundaries

- `JUDGE-main/` is the authoritative runtime.
- `external/CLI-Anything-main/` and `external/memvid-Human--main-main/` are reference-only.
- Source ingestion is disabled by default unless explicitly enabled via source registry controls.
- JWT mutation authority is current; legacy shared-token compatibility is deprecated.
- Public APIs must not expose private or unreviewed records.

## Proof Gate Reality

- `make verify` runs local no-Docker quality checks.
- `make release-proof-local` is the Docker/PostGIS alpha release gate.
- Alpha gate is blocked whenever Docker/PostGIS proof fails.
- Authoritative current proof artifacts are under `artifacts/proof/current/`.

## Verified Current Counts

- Alembic migration files: 44 (`backend/alembic/versions/*.py`).
- Backend pytest baseline in this environment: 2360 passed, 4 skipped, 20 warnings.
- FastAPI requirement: `fastapi>=0.115.0` (from `backend/pyproject.toml`).
- Python requirement: `>=3.11` (from `backend/pyproject.toml`).

## Current Risks/Limitations

- Environment-dependent Docker/PostGIS proof can block alpha gate even when backend/frontend checks pass.
- Historical sidecar proof files can drift from current gate outputs unless archived and regenerated.
- Ingestion paths require strict fail-closed audit ordering to avoid committing mutation state without durable audit rows.

## Required Operational Truth Statements

- Do not claim production deployment readiness.
- Do not claim legal authority over outcomes.
- Do not claim comprehensive legal coverage.
- Do not claim autonomous operation.
- Do not claim PostGIS-proven status unless current PostGIS proof passes.
