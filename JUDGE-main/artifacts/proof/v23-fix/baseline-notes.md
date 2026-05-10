# Baseline Notes (v23-fix)

- current release gate check count: authoritative `artifacts/proof/current/release_gate.json` missing; latest legacy sidecar (`proof_all_summary.json`) reports 20 steps.
- failed checks (effective baseline blockers): `docker_runtime_preflight`, `postgis_proof` (no current postgis proof artifact present).
- docker timeout details: existing runtime preflight log stops after `Running docker version...` and does not emit terminal PASS/FAIL lines.
- postgis proof status: `artifacts/proof/current/postgis_proof.log` missing; container workflow evidence is absent in current proof folder.
- stale proof sidecars present and contradictory:
  - `artifacts/proof/current/manifest.json` reports `result: pass` and Python `3.9.7`.
  - `artifacts/proof/current/proof_all_summary.json` reflects legacy summary output.
  - `artifacts/proof/current/environment_info.txt` reports Python `3.9.7`.
- stale docs found:
  - `README.md` FastAPI version/test count claims outdated.
  - `docs/CURRENT_STATUS.md` migration/auth/proof claims outdated.
  - `docs/DB_PROOF.md` migration/test count claims outdated.
- known ingestion transaction risks requiring verification/fixes:
  - `run_courtlistener_ingestion(..., commit=False)` branch behavior must prove no helper-owned `commit`/`rollback`.
  - admin retry adapter-failure path must remain audit-before-commit and rollback on audit failure.
  - bulk import needs explicit tests proving per-file durable audit rows before per-file commit.
