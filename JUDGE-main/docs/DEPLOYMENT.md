# DEPLOYMENT (Alpha)

This document describes alpha deployment posture only.

## Deployment Classification

- Target: proof-gated alpha deployment
- Not ready for production deployment
- No legal authority claims

## Required Pre-Deploy Proof

Run and review all of the following on the current code state:

- `backend/.venv/bin/python scripts/release_gate.py`
- `bash scripts/package_and_validate_release_archive.sh`
- `bash scripts/proof_all_current.sh`

Required artifacts:

- artifacts/proof/current/CURRENT_PROOF.md
- artifacts/proof/current/release_gate.json
- artifacts/proof/release_readiness.md

## Hard Safety Gates

- Ingestion remains fail-closed.
- Public visibility remains review/evidence gated.
- Evidence snapshots remain immutable and hash-checked.
- Memory remains derivative of evidence.

If any gate fails, release recommendation is `blocked`.
