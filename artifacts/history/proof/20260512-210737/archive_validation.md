# Archive Validation

- validated_at_utc: 2026-05-12T21:06:50.088854+00:00
- archive: /private/var/folders/xt/jh84t2kj6hl26tk5qx3m_28h0000gn/T/tmp.2jxFJKC1DA/judge_atlas_archive.zip
- archive_sha256: bbe7cd7b569ea98006f8c1161474c558dd7ec6b21183404a71baa56a9ecfe66a
- expected_root: JUDGE_ATLAS-main
- actual_root: JUDGE_ATLAS-main
- top_level_roots: JUDGE_ATLAS-main
- root_match: yes
- valid: FAIL
- compressed_size_bytes: 1485407
- uncompressed_size_bytes: 5445589

## Errors

- missing_required_proof_file:artifacts/proof/current/CURRENT_PROOF.md

## Largest Files

| path | uncompressed | compressed |
|---|---:|---:|
| JUDGE_ATLAS-main/backend/uv.lock | 769811 | 238625 |
| JUDGE_ATLAS-main/frontend/package-lock.json | 357366 | 75703 |
| JUDGE_ATLAS-main/frontend/tsconfig.tsbuildinfo | 129372 | 42663 |
| JUDGE_ATLAS-main/scripts/release_gate.py | 69105 | 13401 |
| JUDGE_ATLAS-main/backend/app/models/entities.py | 67407 | 10485 |
| JUDGE_ATLAS-main/artifacts/proof/current/release_gate.json | 60387 | 9499 |
| JUDGE_ATLAS-main/backend/app/tests/test_api.py | 41968 | 7224 |
| JUDGE_ATLAS-main/backend/app/tests/test_ingestion_runtime.py | 38018 | 5725 |
| JUDGE_ATLAS-main/artifacts/proof/current/source_registry_status.json | 31846 | 2676 |
| JUDGE_ATLAS-main/backend/app/tests/test_ai_reasoning.py | 30318 | 4943 |
| JUDGE_ATLAS-main/backend/app/ingestion/courtlistener_bulk_normalizer.py | 29758 | 5588 |
| JUDGE_ATLAS-main/backend/app/ingestion/sources/canada_saskatchewan_sources.yaml | 29564 | 4375 |
| JUDGE_ATLAS-main/backend/app/api/routes/admin_sources.py | 28979 | 6073 |
| JUDGE_ATLAS-main/backend/app/tests/test_graph_layer.py | 28216 | 4765 |
| JUDGE_ATLAS-main/backend/app/api/routes/admin_ingest.py | 24949 | 4181 |
| JUDGE_ATLAS-main/backend/app/tests/test_memory_runtime.py | 24708 | 4490 |
| JUDGE_ATLAS-main/backend/app/tests/test_serializer_contracts.py | 24032 | 4726 |
| JUDGE_ATLAS-main/backend/app/seed/sample_data.py | 23771 | 4376 |
| JUDGE_ATLAS-main/backend/app/tests/test_evidence_runtime.py | 23712 | 3905 |
| JUDGE_ATLAS-main/backend/app/serializers/public.py | 23224 | 5025 |

## Largest Top-Level Directories

| path | uncompressed |
|---|---:|
| backend | 3899040 |
| frontend | 787311 |
| scripts | 355650 |
| docs | 230008 |
| artifacts | 128438 |
| README.md | 23149 |
| infra | 17264 |
| docker-compose.yml | 1900 |
| STATUS.md | 1894 |
| RELEASE_MANIFEST.json | 935 |
