# RELEASE_READINESS

- generated_at_utc: 2026-05-12T06:57:16.685416+00:00
- overall_status: blocked
- production_ready: false
- release_recommendation: blocked
- archive_hash: a01e4ab96be3fb3522efce49f8d08c08f27a5a50
- platform: macOS-26.2-arm64-arm-64bit
- python_version: 3.9.7
- node_version: v20.20.2
- npm_version: 10.8.2

## Required Proof Gates

| gate | status | exit_code | log | sha256 |
|---|---|---:|---|---|
| check_no_pyc | PASS | 0 | artifacts/proof/current/check_no_pyc.log | a846f2e3cfab43e1b94af70247e6dff79ec62b983961a207185d87595b1b7ff6 |
| check_false_claims | FAIL | 1 | artifacts/proof/current/check_false_claims.log | 325a7499dc2dfa8230d97e08ea96c8e4507c4fffe30c9bd053b7c43aff747cfb |
| check_source_keys | PASS | 0 | artifacts/proof/current/check_source_keys.log | 5a19cc9f9747d78ac73bb6e54323386b8a32b69079e204630f249748b6ffb39c |
| check_statuses | PASS | 0 | artifacts/proof/current/check_statuses.log | c5a1e374a12383ff2f924e70bd72bb2ba7210c803d1bba658765034a41a5b256 |
| check_no_direct_ingestion_network_clients | PASS | 0 | artifacts/proof/current/check_no_direct_ingestion_network_clients.log | ab01be057c4e3b265f8f9cc13a4ab4a145abca00913b61d7adf7116dbb1dca58 |
| check_source_registry_docs | FAIL | 1 | artifacts/proof/current/check_source_registry_docs.log | 733ecb2ac7aaf4afb5f66501dd43bb99ec28c7080ad637376e5155881cd7fba4 |
| check_external_boundaries | PASS | 0 | artifacts/proof/current/check_external_boundaries.log | da039530a33bf730b0cc264637a3196b2212a42c42e24f50edcb6f1090c41b62 |
| backend_compile | PASS | 0 | artifacts/proof/current/backend_compile.log | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| backend_import | PASS | 0 | artifacts/proof/current/backend_import.log | b37c6dbf65566cc27820af5fe0de5997781559cea4b5e5a4219696855d2a89cf |
| backend_pytest | FAIL | 1 | artifacts/proof/current/backend_pytest.log | 79571c6d58cd70f72d4a863dafbc00879a4c0f77038b18fd076999cf81e25f1d |
| check_migrations | PASS | 0 | artifacts/proof/current/check_migrations.log | b1a31ef1e482457fd1c47ac213cc98d199e78f8051acc81264a305cf629b66bf |
| docker_runtime_preflight | PASS | 0 | artifacts/proof/current/docker_runtime_preflight.log | a90ba9372262de5a7357ee5a8de5ef4ce301fb9f01dd27c972bf0507ac674a76 |
| postgis_proof | PASS | 0 | artifacts/proof/current/postgis_proof.log | 72b7ff10382f330cdafc3f7b6b3945c5847ebb364e121970011e757b9c251ee1 |
| egress_proxy_proof | PASS | 0 | artifacts/proof/current/egress_proxy_proof.log | 9a094c6ea14a9053d750bed58c420c654dfa4b57deef4eb2b261c7ff6a6e528f |
| demo_proof | PASS | 0 | artifacts/proof/current/demo_proof.log | 3b6e8fd0bab0b6d878c88253eaf6c86c54a0e02d0c0ad54d97526411817bc7c7 |
| validate_sources | PASS | 0 | artifacts/proof/current/validate_sources.log | 4d734d90bf04c25a04d4752d5067c94dc51e963876cfc4f61bbf698de63c27ba |
| source_registry_status | PASS | 0 | artifacts/proof/current/source_registry_status.log | 0acdea3c45b6e48d40b558a056fcb1707cc893564cf5d3f67a46f3fffd2cb26f |
| prepare_proof_db | PASS | 0 | artifacts/proof/current/prepare_proof_db.log | ef6779db88eeffa32551cb68ca12147f76837d1ef139b9e8d67f668940f260d5 |
| verify_evidence_store | PASS | 0 | artifacts/proof/current/verify_evidence_store.log | 52ea4efb6abb497249a5979fa98d8da1fc891bc67e24fc3e746e3a2c859e909d |
| verify_audit_chain | PASS | 0 | artifacts/proof/current/verify_audit_chain.log | 2c2703c1d222a1c6457e032d0382a8f0d32f3474d6a0765ee263e7f51db36aec |
| auth_mutation_route_coverage | PASS | 0 | artifacts/proof/current/auth_mutation_route_coverage.log | a73bd575fcf77c29ba86323af191361b0938a6a4bd52a673df572c4089039ffe |
| mutation_fail_closed_coverage | PASS | 0 | artifacts/proof/current/mutation_fail_closed_coverage.log | 29c8e44c40987f5cb5250ad3b38650446cc5e2442f2cfc99971651bf2c078f17 |
| frontend_node_gate | PASS | 0 | artifacts/proof/current/frontend_node_gate.log | 1aaabeefd07a61f2e5f39241277580ddbe158ff27c88271f2732e612208ffa33 |
| frontend_install | PASS | 0 | artifacts/proof/current/frontend_install.log | a1e170290c179a7f3b7d3143507b3cef2e3d5fbdfdb0e34475e80b0e0345cfe2 |
| frontend_lint | PASS | 0 | artifacts/proof/current/frontend_lint.log | 9d79910829d5abcf1161f85f3d57cc9c745d1edd5734a88fee634c9913b368e8 |
| frontend_typecheck | PASS | 0 | artifacts/proof/current/frontend_typecheck.log | 701338e1389ab6284419cba533b353099f6b47658b930e128a8627a7a2d6d6e7 |
| frontend_contracts | PASS | 0 | artifacts/proof/current/frontend_contracts.log | 7e7e29be992aeddd328d913fea70143a4945cf58d0c0f66fa73ad3277a995b46 |
| frontend_build | PASS | 0 | artifacts/proof/current/frontend_build.log | c237df7fe88835c240448b0e7b12faf1638098f75a5e0b2938fced33b5c2a61b |
| check_api_contracts | PASS | 0 | artifacts/proof/current/check_api_contracts.log | f6750f8d64797a660c9122c245fa0ae38eb689dd8023b7fef1d0481e4ab86216 |
| repo_generated_files | PASS | 0 | artifacts/proof/current/repo_generated_files.log | a445dcba0b3253c29c7dd5785ae59c3eb95be0fa8e752a85f501f8db0b5103f0 |
| check_npm_audit_triage | PASS | 0 | artifacts/proof/current/check_npm_audit_triage.log | 78ebbcc52598a48a739f08fbbc4ef958826f7b2d66cc8a5b365b473e71847020 |
| map_route_check | PASS | 0 | artifacts/proof/current/map_route_check.log | 0e80afc9bb82b4b8f0816b210c78499c88a92d59ea5305bf46bd4ac83a858420 |
| public_api_boundary | PASS | 0 | artifacts/proof/current/public_api_boundary.log | 834d34fe8c0321328aca35ccf1dec590f33731bb2aee144965fbf7c70d252af7 |
| proof_freshness | PASS | 0 | artifacts/proof/current/proof_freshness.log | 0929f71f3b19ffce8957d418c6b7e332185d594514e38d92edb92caa479d251d |
| release_readiness_generation | FAIL | 1 | artifacts/proof/current/release_readiness.md | e266d420cc7d99c7b72954d85474c64388de3f50d1d6043c712b2d1d374c1204 |
| archive_validation | FAIL | 1 | artifacts/proof/current/archive_validation.log | 69460a49e7e67fdd4744cdc3e3cba398b4398a6600bc622a4c0795feff502b5b |

## Remaining Blockers

- required_gate_failed:check_false_claims
- required_gate_failed:check_source_registry_docs
- required_gate_failed:backend_pytest
- required_gate_failed:release_readiness_generation
- required_gate_failed:archive_validation
- archive_validation_not_pass

## Stale Or Misreported Claims

- readiness is blocked due to failed/missing required proof evidence

## Next Repair Action

- Resolve any required failed gate and rerun scripts/release_gate.py.
