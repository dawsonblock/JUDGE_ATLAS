# CURRENT_ALPHA_STATUS

- generated_at_utc: 2026-05-14T02:56:11.359060+00:00
- commit_hash: 42241cd0bd55d9e98aca775dd40f4e1b7fdb2889
- operational_posture: alpha
- production_ready: false
- alpha_gate_passed: true
- proof_freshness_result: PASS
- release_gate_check_count: 36
- postgis_proof_result: PASS
- egress_proxy_proof_result: PASS
- demo_proof_result: PASS

## Status

- This repository is in alpha proof-hardened posture.
- This repository is not approved for production deployment.
- Alpha gates pass; beta blockers remain.
- Human review remains mandatory for public publication decisions.

## Current Blockers

- Beta blocker: source lifecycle truth parity across proof output, CLI, and admin controls must remain test-verified.
- Beta blocker: legal section version/diff history storage and migration must be validated in production-like runs.
- Beta blocker: evidence store verification must enforce JSON summary plus missing/corrupt/orphan policy in CI.
- Beta blocker: map-v2 explicit filter semantics and non-aggregate reviewed public request shape require integration test lock.
- Beta blocker: legacy corruption/misconduct categories are quarantined from public labels and must remain blocked for accidental reuse.
