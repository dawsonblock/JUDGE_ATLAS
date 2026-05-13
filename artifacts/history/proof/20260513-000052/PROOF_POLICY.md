# PROOF_POLICY

- generated_at_utc: 2026-05-12T21:51:15.452657+00:00
- commit_hash: fa938e89be8232dbaed033d7f9a6979734a16d14

## Canonical Current Artifacts

- Canonical proof output location is artifacts/proof/current/.
- release_gate.json is the machine-readable source of truth for gate state.
- CURRENT_PROOF.md and release_readiness.md are derived summaries from release_gate.json.
- CURRENT_ALPHA_STATUS.md and SOURCE_REGISTRY_STATUS.md are generated per run from the same gate payload.

## History And Retention

- Historical sidecars are archived to artifacts/proof/history/.
- artifacts/proof/current/ represents only the latest authoritative run.

## Truth Boundaries

- Release recommendation is blocked on any required failed or missing check.
- Operational posture remains alpha; production readiness is false.
- Evidence snapshots are authoritative; memory is derivative and non-authoritative.
