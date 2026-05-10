# Database Proof Status

Date: 2026-05-10

## Scope

This document tracks current proof reality for database behavior in the alpha gate.

- Current status: proof-hardened alpha.
- Not ready for production deployment.
- Does not hold legal authority.

## Verified Baseline Facts

- Alembic migration files in repository: 44.
- Backend Python requirement: `>=3.11`.
- FastAPI requirement: `fastapi>=0.115.0`.
- Local backend test baseline in this environment: 2360 passed, 4 skipped, 20 warnings.

## Gate Modes

- `make verify`:
  - Local no-Docker quality checks.
  - Useful for fast regression checks.
- `make release-proof-local`:
  - Docker/PostGIS alpha release gate.
  - Includes Docker runtime preflight and PostGIS proof execution.

## PostGIS Truth Boundary

PostGIS proof is only considered passed when current `artifacts/proof/current/postgis_proof.log` contains an explicit final PASS line and `artifacts/proof/current/release_gate.json` reports passing PostGIS status.

If Docker runtime preflight fails, alpha gate remains blocked. Do not claim PostGIS-proven status while blocked.

## Canonical Current Artifacts

- `artifacts/proof/current/release_gate.json`
- `artifacts/proof/current/release_gate.log`
- `artifacts/proof/current/CURRENT_PROOF.md`
- `artifacts/proof/current/docker_runtime_preflight.log`
- `artifacts/proof/current/postgis_proof.log`
- `artifacts/proof/current/backend_pytest.log`
- `artifacts/proof/current/check_api_contracts.log`
- `artifacts/proof/current/map_route_check.log`
- `artifacts/proof/current/public_api_boundary.log`
- `artifacts/proof/current/mutation_fail_closed_coverage.log`

## Historical Sidecars

Legacy sidecars (for example `manifest.json`, `proof_all_summary.json`, `environment_info.txt`) are historical and must not be treated as authoritative current release-gate state.
