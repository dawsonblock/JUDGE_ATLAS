# CURRENT_PROOF

- generated_at_utc: 2026-05-10T21:14:56.934961+00:00
- commit_hash: 4392946e6afb950ef6cc2d676dd7d876ed4223ed
- alpha_gate_status: PASS
- alpha_gate_passed: true
- release_gate_check_count: 26
- docker_available: true
- postgis_proof_result: PASS
- egress_proxy_proof_result: PASS
- proof_freshness_result: PASS
- proof_input_tree_hash: 3736b75e3d07ec893165f184dbd4745e4db2cc1a4bf1ade744c6c48616377d24
- egress_proxy_proof_log: artifacts/proof/current/egress_proxy_proof.log

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
- Docker/PostGIS proof passed in the current release gate.
- Dedicated egress proxy proof passed in the current release gate.

## Governance Status

- legacy_shared_token_status: deprecated, removal plan documented
- dependency_security_status: npm audit issues triaged for alpha; remediation plan documented

## Current Proof Facts

- backend pytest: 2364 passed, 4 skipped
- frontend contracts: 23 passed
- public API boundary: 11 passed
- Docker runtime preflight: PASS
- PostGIS proof: PASS
- egress proxy proof: PASS
- mutation fail-closed coverage: PASS
- Alembic migrations: 44

## Egress Proxy Coverage

- Dedicated gate artifact: artifacts/proof/current/egress_proxy_proof.log.
- Production startup proxy policy coverage: backend/app/tests/test_production_fetch_egress_policy.py.
- Runtime proxy opener/wiring coverage: backend/app/tests/test_source_fetcher_proxy.py.
- SSRF defense context coverage remains in backend/app/tests/test_source_fetcher_ssrf.py.

## Canonical Artifacts

- artifacts/proof/current/release_gate.json
- artifacts/proof/current/release_gate.log
- artifacts/proof/current/docker_runtime_preflight.log
- artifacts/proof/current/postgis_proof.log
- artifacts/proof/current/egress_proxy_proof.log
- artifacts/proof/current/proof_freshness.log
- artifacts/proof/current/backend_pytest.log
- artifacts/proof/current/frontend_contracts.log
- artifacts/proof/current/check_api_contracts.log
- artifacts/proof/current/map_route_check.log
- artifacts/proof/current/public_api_boundary.log
- artifacts/proof/current/mutation_fail_closed_coverage.log
