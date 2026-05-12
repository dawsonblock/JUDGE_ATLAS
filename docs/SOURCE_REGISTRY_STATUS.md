# Source Registry Status

**Generated:** 2026-05-12T06:50:37.515441+00:00

**Total sources:** 26

| Source Key | Name | Jurisdiction | Class | Type | Automation Status | Adapter | Exists | Parser | Runnable | Review Required | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `justice_canada_laws_xml` | Justice Canada Consolidated Acts and Regulations XML | Canada | machine_ingest | legislation | machine_ready_disabled |  | ✗ | laws_justice_xml | ✗ | ✗ | configured |
| `justice_canada_laws_pit_xml` | Department of Justice Canada – Point-in-Time Laws XML | Canada | disabled_stub | legislation | adapter_missing |  | ✗ | None | ✗ | ✗ | configured |
| `scc_judgments` | Supreme Court of Canada – Judgments | Canada | machine_ingest | court_record | machine_ready_disabled |  | ✗ | scc_lexum_api | ✗ | ✗ | configured |
| `federal_court_canada_decisions` | Federal Court of Canada – Decisions | Canada | portal_reference | court_record | adapter_missing |  | ✗ | federal_court_html | ✗ | ✗ | configured |
| `statscan_crime_tables` | Statistics Canada – Crime and Justice Tables | Canada | portal_reference | aggregate_stats | adapter_missing |  | ✗ | statscan_table | ✗ | ✗ | configured |
| `saskatchewan_legislation` | Saskatchewan Legislation – Acts and Regulations | CA-SK | portal_reference | legislation | adapter_missing |  | ✗ | None | ✗ | ✗ | configured |
| `saskatoon_open_data_public_safety` | City of Saskatoon Open Data – Public Safety | CA-SK-Saskatoon | portal_reference | aggregate_stats | adapter_missing |  | ✗ | ckan_api | ✗ | ✗ | configured |
| `saskatoon_open_data_crime` | City of Saskatoon Open Data – Crime Incidents | Saskatoon, Saskatchewan, Canada | portal_reference | crime_incident | adapter_missing |  | ✗ | saskatoon_csv | ✗ | ✗ | configured |
| `saskatoon_police_open_data` | Saskatoon Police Service – Open Data Portal | Saskatoon, Saskatchewan, Canada | portal_reference | crime_incident | adapter_missing |  | ✗ | saskatoon_police_csv | ✗ | ✗ | configured |
| `web_monitor_saskatoon_police_news` | Saskatoon Police Service – News Releases (Web Monitor) | Saskatoon, Saskatchewan, Canada | disabled_stub | news_monitor | adapter_missing |  | ✗ | crawlee_police_release | ✗ | ✗ | configured |
| `sk_courts_qb_decisions` | Saskatchewan Court of King's Bench – Decisions | Saskatchewan, Canada | machine_ingest | court_record | machine_ready_disabled |  | ✗ | canlii_api | ✗ | ✗ | configured |
| `sk_courts_ca_decisions` | Saskatchewan Court of Appeal – Decisions | Saskatchewan, Canada | machine_ingest | court_record | machine_ready_disabled |  | ✗ | canlii_api | ✗ | ✗ | configured |
| `statscan_ccjs_crime_sk` | Statistics Canada – Canadian Centre for Justice Statistics (SK) | Saskatchewan, Canada | portal_reference | aggregate_stats | adapter_missing |  | ✗ | statscan_table | ✗ | ✗ | configured |
| `statscan_ucr_national` | Statistics Canada – Uniform Crime Reporting Survey (national) | Canada | portal_reference | aggregate_stats | adapter_missing |  | ✗ | statscan_table | ✗ | ✗ | configured |
| `canlii_sk` | CanLII – Saskatchewan Courts | Saskatchewan, Canada | portal_reference | court_record | adapter_missing |  | ✗ | canlii_api | ✗ | ✗ | configured |
| `federal_court_canada` | Federal Court of Canada – Decisions | Canada | machine_ingest | court_record | machine_ready_disabled |  | ✗ | federal_court_html | ✗ | ✗ | configured |
| `scc_decisions` | Supreme Court of Canada – Decisions | Canada | machine_ingest | court_record | machine_ready_disabled |  | ✗ | scc_lexum_api | ✗ | ✗ | configured |
| `sk_justice_ministry` | Saskatchewan Ministry of Justice – News Releases | Saskatchewan, Canada | disabled_stub | news_monitor | adapter_missing |  | ✗ | crawlee_gov_news | ✗ | ✗ | configured |
| `sk_legislature_hansard` | Saskatchewan Legislative Assembly – Hansard | Saskatchewan, Canada | machine_ingest | aggregate_stats | machine_ready_disabled |  | ✗ | sk_legislature_html | ✗ | ✗ | configured |
| `canada_open_data_crime` | Open Government Canada – Crime & Justice Datasets | Canada | portal_reference | aggregate_stats | adapter_missing |  | ✗ | ckan_api | ✗ | ✗ | configured |
| `rcmp_sk_news` | RCMP Saskatchewan – News Releases | Saskatchewan, Canada | disabled_stub | news_monitor | adapter_missing |  | ✗ | crawlee_police_release | ✗ | ✗ | configured |
| `canada_justice_laws` | Department of Justice Canada – Justice Laws Website (Deprecated Alias) | Canada | disabled_stub | aggregate_stats | disabled_stub |  | ✗ | None | ✗ | ✗ | configured |
| `saskatoon_open_data_portal` | City of Saskatoon – Open Data Portal | Saskatoon, Saskatchewan, Canada | portal_reference | aggregate_stats | adapter_missing |  | ✗ | ckan_api | ✗ | ✗ | configured |
| `justice_canada_laws_xml_repo` | Justice Canada Laws XML GitHub Repository (Fixtures) | Canada | manual_reference | reference_repository | adapter_missing |  | ✗ | None | ✗ | ✗ | configured |
| `justice_canada_lims_xml_dtd` | Justice Canada LIMS XML DTD (Schema Validation) | Canada | manual_reference | schema_reference | adapter_missing |  | ✗ | None | ✗ | ✗ | configured |
| `justice_canada_otto_reference` | Justice Canada Otto AI Legal Tools (Architecture Reference) | Canada | manual_reference | architecture_reference | adapter_missing |  | ✗ | None | ✗ | ✗ | configured |

## Legend

- **Source Key:** Unique identifier for source in registry
- **Class:** `machine_ingest` (automated) | `portal_reference` (manual) | `manual_reference` (external) | `disabled_stub` (review-gated)
- **Type:** XML, JSON, CSV, HTML, REST API, CSV
- **Automation Status:** `machine_ready_enabled` | `machine_ready_disabled` | `machine_ready_awaiting_configuration` | `adapter_missing` | `disabled_by_policy` | `disabled_stub`
- **Adapter:** Name of ingestion adapter module
- **Exists:** ✓ Adapter module exists, ✗ Missing or stubbed
- **Parser:** Name of parser for source
- **Runnable:** ✓ Can run immediately, ✗ Blocked by missing adapter, configuration, or policy
- **Review Required:** ✓ All records reviewed before publication, ✗ Auto-publish allowed
- **Status:** Alpha status: `configured`, `tested`, `blocked`, etc.

## Notes

- All sources in this registry are enabled for review or disabled by policy.
- No source is auto-published without human review.
- News sources are in `disabled_stub` tier and remain review-gated.
- Administrative sources are in `portal_reference` tier and require manual entry.
- Only `machine_ingest` sources can be enabled for automated ingestion.
- Enabling a `machine_ingest` source requires all validation gates to pass.