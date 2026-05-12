# Justice Canada Ingestion Proof

- generated_at: 2026-05-12T21:14:36.823095+00:00
- mode: fixture
- source_key: justice_canada_laws_xml
- source_class: machine_ingest
- automation_status: machine_ready_disabled
- enabled: false
- parser_version: justice_laws_xml_v1
- fixture_path: backend/app/tests/fixtures/sources/legis_sample.xml
- fixture_present: true
- fixture_sha256: bd862634203b2fd53b21322722f498fe9a66b49b8f78eacbe7aad58db236521e

## Lifecycle Assertions

- source exists in registry: PASS
- source is machine_ingest: PASS
- source is enableable: PASS
- adapter exists (laws_justice_xml): PASS
- sample XML fetch simulated: PASS
- raw bytes snapshot hash computed: PASS
- parser version recorded: PASS
- normalized records produced: PASS (covered by backend/app/tests/test_justice_laws_xml.py)
- review items created: PASS (covered by backend/app/tests/test_justice_laws_phase4.py)
- records private/pending by default: PASS
- approved record visible in public path: PASS (test-backed)
- unapproved record remains hidden: PASS (test-backed)
- citation provenance references source metadata: PASS
- evidence chat bounded when no evidence exists: PASS

## Notes

- Fixture mode is the default safety mode and does not publish live data.
- Live mode keeps review gating and does not auto-publish records.
