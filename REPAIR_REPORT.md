# REPAIR_REPORT

- generated_at_utc: 2026-05-12T05:40:39.767094+00:00
- commit_hash: 1ea9876edaac2306384b1d3adb477d6039dc2102
- alpha_gate_passed: false

## Phase Results

- 1. Alpha Gate Truthfulness: FAIL (artifacts/proof/current/release_gate.json)
- 2. Canonical Proof Artifacts: PASS (artifacts/proof/current/CURRENT_PROOF.md)
- 3. Generated Alpha Status: PASS (artifacts/proof/current/CURRENT_ALPHA_STATUS.md)
- 4. Source Registry Governance: PASS (artifacts/proof/current/source_registry_status.json)
- 5. Generated Source Registry Status: PASS (artifacts/proof/current/SOURCE_REGISTRY_STATUS.md)
- 6. Proof Policy Generated: PASS (artifacts/proof/current/PROOF_POLICY.md)
- 7. Evidence Store Integrity: PASS (artifacts/proof/current/verify_evidence_store.log)
- 8. Audit Chain Integrity: PASS (artifacts/proof/current/verify_audit_chain.log)
- 9. Justice XML Proof Coverage: FAIL (artifacts/proof/current/backend_pytest.log)
- 10. Public Review Gate Coverage: PASS (artifacts/proof/current/public_api_boundary.log)
- 11. Derivative Memory Boundary Coverage: PASS (artifacts/proof/current/public_api_boundary.log)
- 12. Frontend Node 20 Gate: FAIL (artifacts/proof/current/frontend_node_gate.log)
- 13. CI/Local Gate Parity Baseline: PASS (artifacts/proof/current/release_readiness.md)
- 14. Repair Report Generated: PASS (artifacts/proof/current/REPAIR_REPORT.md)

## Remaining Blockers

- backend_pytest
- frontend_node_gate
- frontend_install
- frontend_lint
- frontend_typecheck
- frontend_contracts
- frontend_build
- archive_validation
- release_readiness_generation
