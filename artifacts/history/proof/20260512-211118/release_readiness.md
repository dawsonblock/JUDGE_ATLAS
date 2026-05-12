# RELEASE_READINESS

- generated_at_utc: 2026-05-12T21:08:59.363600+00:00
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
| backend_pytest | PASS | 0 | artifacts/proof/current/backend_pytest.log | 3d1c60cdf9c36a57f44b52dab09f5260505ba74e5c0ee76789f1aa65db60b528 |
| check_migrations | PASS | 0 | artifacts/proof/current/check_migrations.log | b1a31ef1e482457fd1c47ac213cc98d199e78f8051acc81264a305cf629b66bf |
| docker_runtime_preflight | PASS | 0 | artifacts/proof/current/docker_runtime_preflight.log | 9f9cb9c72852bcec170b77b310c58bfa93ac87ab4ebb2e77d10cdc59e8fc96a4 |
| postgis_proof | PASS | 0 | artifacts/proof/current/postgis_proof.log | 0e383bc92ce32d85235ced3df12bd1c1a4f3fc63c942dd63c7d8fb4f798eab08 |
| egress_proxy_proof | PASS | 0 | artifacts/proof/current/egress_proxy_proof.log | bd9784aadab0c04e54c0a3f1d068dadd3a6ad0a24d33921bb2594971c24ad141 |
| demo_proof | PASS | 0 | artifacts/proof/current/demo_proof.log | 3b6e8fd0bab0b6d878c88253eaf6c86c54a0e02d0c0ad54d97526411817bc7c7 |
| validate_sources | PASS | 0 | artifacts/proof/current/validate_sources.log | 4d734d90bf04c25a04d4752d5067c94dc51e963876cfc4f61bbf698de63c27ba |
| source_registry_status | PASS | 0 | artifacts/proof/current/source_registry_status.log | 0acdea3c45b6e48d40b558a056fcb1707cc893564cf5d3f67a46f3fffd2cb26f |
| prepare_proof_db | PASS | 0 | artifacts/proof/current/prepare_proof_db.log | ef6779db88eeffa32551cb68ca12147f76837d1ef139b9e8d67f668940f260d5 |
| verify_evidence_store | PASS | 0 | artifacts/proof/current/verify_evidence_store.log | 52ea4efb6abb497249a5979fa98d8da1fc891bc67e24fc3e746e3a2c859e909d |
| verify_audit_chain | PASS | 0 | artifacts/proof/current/verify_audit_chain.log | b4ad4387fb6e67c7d860acd7da3d51764aef8db3f5592e5ec29daae65c069a72 |
| auth_mutation_route_coverage | PASS | 0 | artifacts/proof/current/auth_mutation_route_coverage.log | 4f2767dd35da0798b30b723a2e5faa17c9df8610512ffa4e10e8adcc09806241 |
| mutation_fail_closed_coverage | PASS | 0 | artifacts/proof/current/mutation_fail_closed_coverage.log | aeb9d833b04c6c0cff4afc9a719e83fd527ff4dd021f08d3f678f5bc63f4dd1c |
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
| public_api_boundary | PASS | 0 | artifacts/proof/current/public_api_boundary.log | a249eb6dff5dc7f6a1ed51bdce20260f742fd9ce58656402e5073497e9f43aca |
| proof_freshness | PASS | 0 | artifacts/proof/current/proof_freshness.log | 06cf4d798a8b8b4d2179b7fe68836b0a06def4526e98a7d91852d9162bb39a53 |
| release_readiness_generation | PASS | 0 | artifacts/proof/current/release_readiness.md | 453ecb674e1698b289b39763d016ddd0877a2ac30a51d472f435e339fad97484 |
| archive_validation | FAIL | 1 | artifacts/proof/current/archive_validation.log | e586588cb1c0a382c0a09e3057d890d840b6fe484f54c96ef26b3e31c839e671 |

## Remaining Blockers

- required_gate_failed:frontend_node_gate
- required_gate_failed:frontend_install
- required_gate_failed:frontend_lint
- required_gate_failed:frontend_typecheck
- required_gate_failed:frontend_contracts
- required_gate_failed:frontend_build
- required_gate_failed:archive_validation
- node_major_mismatch:Expected Node 20.x, found Node v24.15.0
- archive_validation_not_pass

## Stale Or Misreported Claims

- readiness is blocked due to failed/missing required proof evidence

## Next Repair Action

- Resolve any required failed gate and rerun scripts/release_gate.py.
