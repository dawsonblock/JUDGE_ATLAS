# Baseline Notes (v23-fix)

- release gate checks: 24
- failed checks: docker_runtime_preflight, postgis_proof
- docker failure observed: docker version timed out (20s current script default)
- postgis proof status: blocked due to docker runtime availability; container workflow not reached fully
- stale proof sidecars present and contradictory:
  - artifacts/proof/current/manifest.json reports pass and Python 3.9.7
  - artifacts/proof/current/proof_all_summary.json stale relative to release_gate.json
- stale docs found:
  - README.md FastAPI/tests counts outdated
  - docs/CURRENT_STATUS.md migration/auth claims outdated
  - docs/DB_PROOF.md migration/test counts outdated
- known ingestion transaction risks:
  - admin ingestion retry adapter exception path commits failed state without fail-closed audit
  - run_courtlistener_ingestion commit=False still has rollback/refresh behavior risks in failure branches
