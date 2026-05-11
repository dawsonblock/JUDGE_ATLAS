# RELEASE_READINESS

This file explains how release readiness is determined for the current alpha state.

## Source of Truth

Use current run artifacts only:

- artifacts/proof/release_readiness.md
- artifacts/proof/source_registry_status.json
- artifacts/proof/backend_grouped_tests_summary.log
- artifacts/proof/frontend_build.log

## Allowed Recommendation Values

- blocked
- alpha-internal
- alpha-demo
- beta-candidate
- production-candidate

Current policy for this repository:

- Do not recommend above `alpha-demo` unless every gate in `scripts/proof_all_current.sh` passes and docs/proof are current.
- Do not claim production deployment readiness.
