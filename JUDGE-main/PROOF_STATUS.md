# PROOF STATUS

## Required Proof Commands
- `python -m backend.tools.validate_sources`
- `python -m backend.tools.verify_evidence_store`
- `python -m backend.tools.verify_audit_chain`
- Backend test suite (`pytest` from backend workspace)

## Current State
- Verification tooling is present.
- Proof receipts must be regenerated after each material change.
- A release is not considered proven until fresh command outputs are captured.

## Artifact Policy
Store proof outputs under `artifacts/proof/` with timestamped run metadata.
