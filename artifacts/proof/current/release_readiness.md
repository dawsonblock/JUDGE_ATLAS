# RELEASE_READINESS

- generated_at_utc: 2026-05-12T21:14:26.777681+00:00
- overall_status: blocked
- production_ready: false
- release_recommendation: blocked
- archive_hash: 84d4757880c7b894723cbc8b2f997b2f8ed831b5
- platform: macOS-26.2-arm64-arm-64bit
- python_version: 3.9.7
- node_version: v24.15.0
- npm_version: 11.12.1

## Required Proof Gates

| gate | status | exit_code | log | sha256 |
|---|---|---:|---|---|
| check_no_pyc | PASS | 0 | artifacts/proof/current/check_no_pyc.log | a846f2e3cfab43e1b94af70247e6dff79ec62b983961a207185d87595b1b7ff6 |
| check_false_claims | PASS | 0 | artifacts/proof/current/check_false_claims.log | 8b8785743b076670b5e6cb3524f7a9638bf9563b877477b3e6a9b13ee3bb2f90 |
| check_source_keys | PASS | 0 | artifacts/proof/current/check_source_keys.log | 5a19cc9f9747d78ac73bb6e54323386b8a32b69079e204630f249748b6ffb39c |
| check_statuses | PASS | 0 | artifacts/proof/current/check_statuses.log | c5a1e374a12383ff2f924e70bd72bb2ba7210c803d1bba658765034a41a5b256 |
| check_no_direct_ingestion_network_clients | PASS | 0 | artifacts/proof/current/check_no_direct_ingestion_network_clients.log | ab01be057c4e3b265f8f9cc13a4ab4a145abca00913b61d7adf7116dbb1dca58 |
| check_source_registry_docs | PASS | 0 | artifacts/proof/current/check_source_registry_docs.log | fe1b62e3c0b1bc448549dfe49a124455c9c01b1813f6d4e8effac96e238d35fe |
| check_external_boundaries | PASS | 0 | artifacts/proof/current/check_external_boundaries.log | da039530a33bf730b0cc264637a3196b2212a42c42e24f50edcb6f1090c41b62 |
| backend_compile | PASS | 0 | artifacts/proof/current/backend_compile.log | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| backend_import | PASS | 0 | artifacts/proof/current/backend_import.log | b37c6dbf65566cc27820af5fe0de5997781559cea4b5e5a4219696855d2a89cf |
| backend_pytest | PASS | 0 | artifacts/proof/current/backend_pytest.log | 291caee34e5f721c9d2abaf4fa47d5dfe33da345183ce1356e2890bd0748a5e2 |
| check_migrations | PASS | 0 | artifacts/proof/current/check_migrations.log | b1a31ef1e482457fd1c47ac213cc98d199e78f8051acc81264a305cf629b66bf |
| docker_runtime_preflight | PASS | 0 | artifacts/proof/current/docker_runtime_preflight.log | 0e8d94b9c2965facbd126c5b5329280e1c59728327651a3b4f38cb9fbeb05090 |
| postgis_proof | PASS | 0 | artifacts/proof/current/postgis_proof.log | 182f8697a36dee6e9db7ccfdccd73da7fb699d74cc4eeb799ac55cf0ea573705 |
| egress_proxy_proof | PASS | 0 | artifacts/proof/current/egress_proxy_proof.log | e75aed4bc3ff1c40791e87447abe726d44fb0f906ede6d7761a03dfbea0c376f |
| demo_proof | PASS | 0 | artifacts/proof/current/demo_proof.log | 3b6e8fd0bab0b6d878c88253eaf6c86c54a0e02d0c0ad54d97526411817bc7c7 |
| validate_sources | PASS | 0 | artifacts/proof/current/validate_sources.log | 4d734d90bf04c25a04d4752d5067c94dc51e963876cfc4f61bbf698de63c27ba |
| source_registry_status | PASS | 0 | artifacts/proof/current/source_registry_status.log | 0acdea3c45b6e48d40b558a056fcb1707cc893564cf5d3f67a46f3fffd2cb26f |
| prepare_proof_db | PASS | 0 | artifacts/proof/current/prepare_proof_db.log | ef6779db88eeffa32551cb68ca12147f76837d1ef139b9e8d67f668940f260d5 |
| verify_evidence_store | PASS | 0 | artifacts/proof/current/verify_evidence_store.log | 52ea4efb6abb497249a5979fa98d8da1fc891bc67e24fc3e746e3a2c859e909d |
| verify_audit_chain | PASS | 0 | artifacts/proof/current/verify_audit_chain.log | 9bc11b3d11e55656935ad982f163b9c916efc44c2b04cd8c74053dbeb8436986 |
| auth_mutation_route_coverage | PASS | 0 | artifacts/proof/current/auth_mutation_route_coverage.log | 76d1cba6915f30895aa46eb4d870d6e597e8467c3bdccdcc88a8461b52e75b09 |
| mutation_fail_closed_coverage | PASS | 0 | artifacts/proof/current/mutation_fail_closed_coverage.log | 29c8e44c40987f5cb5250ad3b38650446cc5e2442f2cfc99971651bf2c078f17 |
| frontend_node_gate | FAIL | 1 | artifacts/proof/current/frontend_node_gate.log | b3ce707275b3915a63d1c93a012e14890499d823cd68d9cba8e409e1eb208340 |
| frontend_install | BLOCKED | 1 | artifacts/proof/current/frontend_install.log | 81e994d60d6eb291e23f2cbfcc54f0008a99563866c7214c6b862d5cb66decbc |
| frontend_lint | BLOCKED | 1 | artifacts/proof/current/frontend_lint.log | 81e994d60d6eb291e23f2cbfcc54f0008a99563866c7214c6b862d5cb66decbc |
| frontend_typecheck | BLOCKED | 1 | artifacts/proof/current/frontend_typecheck.log | 81e994d60d6eb291e23f2cbfcc54f0008a99563866c7214c6b862d5cb66decbc |
| frontend_contracts | BLOCKED | 1 | artifacts/proof/current/frontend_contracts.log | 81e994d60d6eb291e23f2cbfcc54f0008a99563866c7214c6b862d5cb66decbc |
| frontend_build | BLOCKED | 1 | artifacts/proof/current/frontend_build.log | 81e994d60d6eb291e23f2cbfcc54f0008a99563866c7214c6b862d5cb66decbc |
| check_api_contracts | PASS | 0 | artifacts/proof/current/check_api_contracts.log | f6750f8d64797a660c9122c245fa0ae38eb689dd8023b7fef1d0481e4ab86216 |
| repo_generated_files | PASS | 0 | artifacts/proof/current/repo_generated_files.log | a445dcba0b3253c29c7dd5785ae59c3eb95be0fa8e752a85f501f8db0b5103f0 |
| check_npm_audit_triage | PASS | 0 | artifacts/proof/current/check_npm_audit_triage.log | 78ebbcc52598a48a739f08fbbc4ef958826f7b2d66cc8a5b365b473e71847020 |
| map_route_check | PASS | 0 | artifacts/proof/current/map_route_check.log | 0e80afc9bb82b4b8f0816b210c78499c88a92d59ea5305bf46bd4ac83a858420 |
| public_api_boundary | PASS | 0 | artifacts/proof/current/public_api_boundary.log | 923e5dcf5804afe1e0d27aa24b4f14e2f56663e91b40acfea766d895ae822024 |
| proof_freshness | PASS | 0 | artifacts/proof/current/proof_freshness.log | 990d55074ea2e4c5450358f62241e10d1f08ea8518028caf30fa26b9bc8caacf |
| release_readiness_generation | PASS | 0 | artifacts/proof/current/release_readiness.md | 03d2077944f723985e2b686ce8bb424f30ef06a22f45e22ce1932787ea027a2f |
| archive_validation | PASS | 0 | artifacts/proof/current/archive_validation.log | 5b22c418813980e3765abeb9bde2f1d7e45ca0e714f5daed55ad93f8ea829419 |

## Remaining Blockers

- required_gate_failed:frontend_node_gate
- required_gate_failed:frontend_install
- required_gate_failed:frontend_lint
- required_gate_failed:frontend_typecheck
- required_gate_failed:frontend_contracts
- required_gate_failed:frontend_build
- node_major_mismatch:Expected Node 20.x, found Node v24.15.0

## Stale Or Misreported Claims

- readiness is blocked due to failed/missing required proof evidence

## Next Repair Action

- Resolve any required failed gate and rerun scripts/release_gate.py.
