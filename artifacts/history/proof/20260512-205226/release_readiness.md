# RELEASE_READINESS

- generated_at_utc: 2026-05-12T08:12:38.845238+00:00
- overall_status: alpha-proof-pass
- production_ready: false
- release_recommendation: alpha-proof-pass
- archive_hash: fe75058db568a194491fcacca9ebddaeefef9b42
- platform: macOS-26.2-arm64-arm-64bit
- python_version: 3.9.7
- node_version: v20.20.2
- npm_version: 10.8.2

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
| backend_pytest | PASS | 0 | artifacts/proof/current/backend_pytest.log | 21d649f3b1f2157ab60a7153e7d5279db6852911a6ad66d7c140eb401e14b11f |
| check_migrations | PASS | 0 | artifacts/proof/current/check_migrations.log | b1a31ef1e482457fd1c47ac213cc98d199e78f8051acc81264a305cf629b66bf |
| docker_runtime_preflight | PASS | 0 | artifacts/proof/current/docker_runtime_preflight.log | a90ba9372262de5a7357ee5a8de5ef4ce301fb9f01dd27c972bf0507ac674a76 |
| postgis_proof | PASS | 0 | artifacts/proof/current/postgis_proof.log | 83907188d7dc0bef19dba43c9df4de3ceba7402389c4a7953802777b726dd784 |
| egress_proxy_proof | PASS | 0 | artifacts/proof/current/egress_proxy_proof.log | 6a0dff42a937c7ab28230995c52d33bc493df0c288b05204373a53ddabd15185 |
| demo_proof | PASS | 0 | artifacts/proof/current/demo_proof.log | 3b6e8fd0bab0b6d878c88253eaf6c86c54a0e02d0c0ad54d97526411817bc7c7 |
| validate_sources | PASS | 0 | artifacts/proof/current/validate_sources.log | 4d734d90bf04c25a04d4752d5067c94dc51e963876cfc4f61bbf698de63c27ba |
| source_registry_status | PASS | 0 | artifacts/proof/current/source_registry_status.log | 0acdea3c45b6e48d40b558a056fcb1707cc893564cf5d3f67a46f3fffd2cb26f |
| prepare_proof_db | PASS | 0 | artifacts/proof/current/prepare_proof_db.log | ef6779db88eeffa32551cb68ca12147f76837d1ef139b9e8d67f668940f260d5 |
| verify_evidence_store | PASS | 0 | artifacts/proof/current/verify_evidence_store.log | 52ea4efb6abb497249a5979fa98d8da1fc891bc67e24fc3e746e3a2c859e909d |
| verify_audit_chain | PASS | 0 | artifacts/proof/current/verify_audit_chain.log | a5ef87b23f53628a930c5346fac7693f9bf58619cc10be7af2b315a20869d8e5 |
| auth_mutation_route_coverage | PASS | 0 | artifacts/proof/current/auth_mutation_route_coverage.log | a73bd575fcf77c29ba86323af191361b0938a6a4bd52a673df572c4089039ffe |
| mutation_fail_closed_coverage | PASS | 0 | artifacts/proof/current/mutation_fail_closed_coverage.log | aeb9d833b04c6c0cff4afc9a719e83fd527ff4dd021f08d3f678f5bc63f4dd1c |
| frontend_node_gate | PASS | 0 | artifacts/proof/current/frontend_node_gate.log | 1aaabeefd07a61f2e5f39241277580ddbe158ff27c88271f2732e612208ffa33 |
| frontend_install | PASS | 0 | artifacts/proof/current/frontend_install.log | a1e170290c179a7f3b7d3143507b3cef2e3d5fbdfdb0e34475e80b0e0345cfe2 |
| frontend_lint | PASS | 0 | artifacts/proof/current/frontend_lint.log | 9d79910829d5abcf1161f85f3d57cc9c745d1edd5734a88fee634c9913b368e8 |
| frontend_typecheck | PASS | 0 | artifacts/proof/current/frontend_typecheck.log | 701338e1389ab6284419cba533b353099f6b47658b930e128a8627a7a2d6d6e7 |
| frontend_contracts | PASS | 0 | artifacts/proof/current/frontend_contracts.log | 227e1c05fe8974bc24bf3a30b9705e7288d16648a1454079052590e4401e1c7d |
| frontend_build | PASS | 0 | artifacts/proof/current/frontend_build.log | c237df7fe88835c240448b0e7b12faf1638098f75a5e0b2938fced33b5c2a61b |
| check_api_contracts | PASS | 0 | artifacts/proof/current/check_api_contracts.log | f6750f8d64797a660c9122c245fa0ae38eb689dd8023b7fef1d0481e4ab86216 |
| repo_generated_files | PASS | 0 | artifacts/proof/current/repo_generated_files.log | a445dcba0b3253c29c7dd5785ae59c3eb95be0fa8e752a85f501f8db0b5103f0 |
| check_npm_audit_triage | PASS | 0 | artifacts/proof/current/check_npm_audit_triage.log | 78ebbcc52598a48a739f08fbbc4ef958826f7b2d66cc8a5b365b473e71847020 |
| map_route_check | PASS | 0 | artifacts/proof/current/map_route_check.log | 0e80afc9bb82b4b8f0816b210c78499c88a92d59ea5305bf46bd4ac83a858420 |
| public_api_boundary | PASS | 0 | artifacts/proof/current/public_api_boundary.log | bca204f48f688d3bcbb12bd5f9c3cd483c6933445db8367b613abbbdbfeda678 |
| proof_freshness | PASS | 0 | artifacts/proof/current/proof_freshness.log | 0dd0b42921f7ade1309b839e2c984631e0027b3336d077fd527c1c172a1e2de8 |
| release_readiness_generation | PASS | 0 | artifacts/proof/current/release_readiness.md | a6cadc5ec74889cebb59de47e5981a24ad117c35f99814dcf5522d481ced0ff9 |
| archive_validation | PASS | 0 | artifacts/proof/current/archive_validation.log | a1e70a555c83cbc2bb7671412ed0b69e31a98f1bbe74b0f5d637574c1d4e623b |

## Remaining Blockers

- none

## Stale Or Misreported Claims

- none

## Next Repair Action

- Resolve any required failed gate and rerun scripts/release_gate.py.
