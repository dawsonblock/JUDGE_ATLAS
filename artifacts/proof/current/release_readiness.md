# RELEASE_READINESS

- generated_at_utc: 2026-05-12T04:32:51.791851+00:00
- commit_hash: b8ed46b5783c1f36a0cec348529b1c9adf52f6c7
- alpha_gate_passed: false
- proof_freshness_result: PASS
- archive_validation_result: NOT_RUN

## Backend Proof

- grouped_status: FAIL
- backend_import_routes: 103
- backend_pytest: 2423 passed, 4 skipped
- proof_db_audit_logs: 3
- proof_db_source_snapshots: 3
- summary_json: artifacts/proof/current/backend_proof_summary.json

## Frontend Proof

- grouped_status: PASS
- frontend_build_log: artifacts/proof/current/frontend_build.log
- frontend_contracts_passed: 23
- summary_json: artifacts/proof/current/frontend_proof_summary.json

## Source Registry

- source_registry_status_json: artifacts/proof/current/source_registry_status.json
- total_sources: 26
- machine_ingest_sources: 7
- runnable_when_active_sources: 7
- sources_requiring_secrets: 5

## Release Blockers

- check_false_claims
- validate_sources
