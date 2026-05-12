# Stub Adapter Report

- generated_at: 2026-05-12T20:53:59.062905+00:00
- findings: 12

| source_key | file_path | source_class | automation_status | enabled | runnable | reason |
|---|---|---|---|---|---|---|
| canada_justice_laws | backend/app/ingestion/source_adapters/.py | disabled_stub | disabled_stub | false | false | adapter_missing |
| justice_canada_laws_pit_xml | backend/app/ingestion/source_adapters/.py | disabled_stub | adapter_missing | false | false | adapter_missing |
| justice_canada_laws_xml_repo | backend/app/ingestion/source_adapters/.py | manual_reference | adapter_missing | false | false | adapter_missing |
| justice_canada_lims_xml_dtd | backend/app/ingestion/source_adapters/.py | manual_reference | adapter_missing | false | false | adapter_missing |
| justice_canada_otto_reference | backend/app/ingestion/source_adapters/.py | manual_reference | adapter_missing | false | false | adapter_missing |
| rcmp_sk_news | backend/app/ingestion/source_adapters/crawlee_police_release.py | disabled_stub | adapter_missing | false | false | not_implemented_stub |
| saskatchewan_legislation | backend/app/ingestion/source_adapters/.py | portal_reference | adapter_missing | false | false | adapter_missing |
| sk_justice_ministry | backend/app/ingestion/source_adapters/crawlee_gov_news.py | disabled_stub | adapter_missing | false | false | not_implemented_stub |
| statscan_ccjs_crime_sk | backend/app/ingestion/source_adapters/statscan_table.py | portal_reference | adapter_missing | false | false | not_implemented_stub |
| statscan_crime_tables | backend/app/ingestion/source_adapters/statscan_table.py | portal_reference | adapter_missing | false | false | not_implemented_stub |
| statscan_ucr_national | backend/app/ingestion/source_adapters/statscan_table.py | portal_reference | adapter_missing | false | false | not_implemented_stub |
| web_monitor_saskatoon_police_news | backend/app/ingestion/source_adapters/crawlee_police_release.py | disabled_stub | adapter_missing | false | false | not_implemented_stub |

## Fail-Closed Result

- PASS if all stub/reference/manual/adapter-missing sources are non-runnable.
- Current report computes runnable=false for all discovered stubs.
