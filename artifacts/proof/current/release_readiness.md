# RELEASE_READINESS

- generated_at_utc: 2026-05-14T02:56:11.359060+00:00
- overall_status: alpha-proof-pass
- production_ready: false
- release_recommendation: alpha-proof-pass
- archive_hash: 42241cd0bd55d9e98aca775dd40f4e1b7fdb2889
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
| backend_pytest | PASS | 0 | artifacts/proof/current/backend_pytest.log | b241992bd196ad5db0f0dc3928acc7ed288e03dab8ffe0e0f744bbceed3b8a5d |
| check_migrations | PASS | 0 | artifacts/proof/current/check_migrations.log | b1a31ef1e482457fd1c47ac213cc98d199e78f8051acc81264a305cf629b66bf |
| docker_runtime_preflight | PASS | 0 | artifacts/proof/current/docker_runtime_preflight.log | 02f7283ab6012eea4ed77e72de82d52e17a495e6d6eec4bdab67f07ee30bc5d4 |
| postgis_proof | PASS | 0 | artifacts/proof/current/postgis_proof.log | 6ac677a836e013ef1100363391e8c739a5a959d82d2b96a51cce7e6a0b72e4df |
| egress_proxy_proof | PASS | 0 | artifacts/proof/current/egress_proxy_proof.log | 8917d8c624cba8962689e971f3c1caf4d12efebc1004caf2377d5986f81a902a |
| demo_proof | PASS | 0 | artifacts/proof/current/demo_proof.log | 8801b82f178ff962b19a6e7d38c5e3d78d479ad92ae4a78d84a6697d1335e0d1 |
| validate_sources | PASS | 0 | artifacts/proof/current/validate_sources.log | 4d734d90bf04c25a04d4752d5067c94dc51e963876cfc4f61bbf698de63c27ba |
| source_registry_status | PASS | 0 | artifacts/proof/current/source_registry_status.log | 0acdea3c45b6e48d40b558a056fcb1707cc893564cf5d3f67a46f3fffd2cb26f |
| prepare_proof_db | PASS | 0 | artifacts/proof/current/prepare_proof_db.log | ef6779db88eeffa32551cb68ca12147f76837d1ef139b9e8d67f668940f260d5 |
| verify_evidence_store | PASS | 0 | artifacts/proof/current/verify_evidence_store.log | 52ea4efb6abb497249a5979fa98d8da1fc891bc67e24fc3e746e3a2c859e909d |
| verify_audit_chain | PASS | 0 | artifacts/proof/current/verify_audit_chain.log | 5f514393fd521175aa30cc83f5dfc7d47836dd64934d34cc83f272f3e519080c |
| auth_mutation_route_coverage | PASS | 0 | artifacts/proof/current/auth_mutation_route_coverage.log | 3af0abece68cb36716441ba3bd51d1e0c17d26fdfe126851ba87e0ad77baca7b |
| mutation_fail_closed_coverage | PASS | 0 | artifacts/proof/current/mutation_fail_closed_coverage.log | 4c4fd05142bd23c8c7fb9bebc0b5eb3daad6b1b299ca191af53fb3b2996ee47e |
| frontend_node_gate | PASS | 0 | artifacts/proof/current/frontend_node_gate.log | 1aaabeefd07a61f2e5f39241277580ddbe158ff27c88271f2732e612208ffa33 |
| frontend_install | PASS | 0 | artifacts/proof/current/frontend_install.log | f2d9efab1d1cf4932507e7f8a7769d311a8c3f5a8665e13655e3eb986494e09a |
| frontend_lint | PASS | 0 | artifacts/proof/current/frontend_lint.log | 9d79910829d5abcf1161f85f3d57cc9c745d1edd5734a88fee634c9913b368e8 |
| frontend_typecheck | PASS | 0 | artifacts/proof/current/frontend_typecheck.log | 701338e1389ab6284419cba533b353099f6b47658b930e128a8627a7a2d6d6e7 |
| frontend_contracts | PASS | 0 | artifacts/proof/current/frontend_contracts.log | 95e81545fbd8241251d670b47c40adc1a8a491fbbfe76b1963fd0304dd61b3ef |
| frontend_build | PASS | 0 | artifacts/proof/current/frontend_build.log | bf91ca2f35f7c80c9fc3bce976e8882a9388d70485eb3231a0ffc62f93c071b4 |
| check_api_contracts | PASS | 0 | artifacts/proof/current/check_api_contracts.log | f6750f8d64797a660c9122c245fa0ae38eb689dd8023b7fef1d0481e4ab86216 |
| repo_generated_files | PASS | 0 | artifacts/proof/current/repo_generated_files.log | a445dcba0b3253c29c7dd5785ae59c3eb95be0fa8e752a85f501f8db0b5103f0 |
| check_npm_audit_triage | PASS | 0 | artifacts/proof/current/check_npm_audit_triage.log | 78ebbcc52598a48a739f08fbbc4ef958826f7b2d66cc8a5b365b473e71847020 |
| map_route_check | PASS | 0 | artifacts/proof/current/map_route_check.log | 0e80afc9bb82b4b8f0816b210c78499c88a92d59ea5305bf46bd4ac83a858420 |
| public_api_boundary | PASS | 0 | artifacts/proof/current/public_api_boundary.log | 0791c20d47db81791c250e712ab8a8eb0f88a9e2dc4cd7a36ed0a9ba964b614c |
| proof_freshness | PASS | 0 | artifacts/proof/current/proof_freshness.log | 88730c2c1440f7f2418adb9555fef44063192abfba319785c5df4bc24c3b4860 |
| release_readiness_generation | PASS | 0 | artifacts/proof/current/release_readiness.md | 6dfa1315defa40a49bdf9817f28566839b84370ecb209f3e14b3ebcc1f601a5c |
| archive_validation | PASS | 0 | artifacts/proof/current/archive_validation.log | b1f0a8326684ba68530f6246f1f237748a1104e552faa41e1cb8d19fbf5b4bab |

## Remaining Blockers

- none

## Stale Or Misreported Claims

- none

## Next Repair Action

- Resolve any required failed gate and rerun scripts/release_gate.py.
