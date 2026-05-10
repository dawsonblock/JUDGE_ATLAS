# CURRENT_PROOF

- generated_at_utc: 2026-05-10T19:28:50.339826+00:00
- commit_hash: 2944112fcfbe5c4ccbba666f7f0e87dd3663e1bf
- alpha_gate_status: PASS
- alpha_gate_passed: true
- release_gate_check_count: 24
- docker_available: true
- postgis_proof_result: PASS

## Runtime Metadata

- gate_runner_python_version: 3.11.7
- gate_runner_python_executable: /Users/dawsonblock/Downloads/THE-JUDGE-main/JUDGE-main/backend/.venv/bin/python
- backend_test_python_version: 3.11.7
- backend_test_python_executable: /Users/dawsonblock/Downloads/THE-JUDGE-main/JUDGE-main/backend/.venv/bin/python
- backend_required_python: >=3.11
- node_version: v24.15.0
- npm_version: 11.12.1
- platform: macOS-26.2-arm64-arm-64bit
- test_database_backend: sqlite
- test_database_url_type: sqlite_file

## Scope and Safety

- Current status: proof-hardened alpha.
- Not ready for production deployment.
- Does not hold legal authority.
- Evidence snapshots are authoritative; memory is derivative.
- AI is reviewer assistance only.
- Source ingestion is disabled by default unless explicitly enabled.
- External folders are reference-only.
- JWT mutation authority is current; legacy shared-token compatibility is deprecated.
- make verify = local no-Docker quality checks.
- make release-proof-local = Docker/PostGIS alpha release gate.
- Current alpha release is blocked if Docker/PostGIS proof fails.

## Egress Proxy Coverage

- Covered by backend tests for production proxy policy and runtime proxy opener wiring.

## Canonical Artifacts

- artifacts/proof/current/release_gate.json
- artifacts/proof/current/release_gate.log
- artifacts/proof/current/docker_runtime_preflight.log
- artifacts/proof/current/postgis_proof.log
- artifacts/proof/current/backend_pytest.log
- artifacts/proof/current/frontend_contracts.log
- artifacts/proof/current/check_api_contracts.log
- artifacts/proof/current/map_route_check.log
- artifacts/proof/current/public_api_boundary.log
- artifacts/proof/current/mutation_fail_closed_coverage.log
