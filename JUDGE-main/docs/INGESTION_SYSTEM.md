# Ingestion System

**Status: alpha — Canada-first, reviewer-assisted**

---

## Overview

THE-JUDGE ingests records from registered sources, creates evidence snapshots, and routes all new records through a mandatory reviewer queue before any public visibility is granted.

The ingestion system is **not autonomous** — no record is auto-published.

---

## Ingestion Pipeline

```
Source → Adapter.fetch() → Adapter.parse() → IngestionResult
       → persist_ingestion_result() → SourceSnapshot + ReviewItem
       → Reviewer queue → Human decision → (optionally) public_visibility=True
```

---

## Adapter Status Classification

| Status | Meaning | Can auto-ingest |
|--------|---------|-----------------|
| `machine_ingest` | Has a working parser; can be run via CLI | ✅ |
| `manual_upload` | Requires CSV/document upload; no scraper | ❌ (upload only) |
| `portal_reference` | Reference link only; no scraper | ❌ |
| `disabled_stub` | Registered but not runnable | ❌ |

Only `machine_ingest` sources can be run via `judgectl ingest run` or `judgectl ingest canlii-sk`.

---

## Canada-First Sources

The primary ingest path is Canadian court records.

### Active machine-ingest paths

| Source Key | Description | API Required |
|------------|-------------|--------------|
| `sk_courts_qb_decisions` | Saskatchewan Court of King's Bench (CanLII) | JTA_CANLII_API_KEY |
| `sk_courts_ca_decisions` | Saskatchewan Court of Appeal (CanLII) | JTA_CANLII_API_KEY |

### Portal-reference only (no scraper)

Many sources are registered as `portal_reference` or `disabled_stub`. These cannot be automatically ingested and serve as reference entries only.

See `CANADA_DATA_SOURCES.md` for the full list.

---

## Evidence Requirements

Every successful ingest run must produce:
- A `SourceSnapshot` with `content_hash`, `fetched_at`, `parser_version`
- `ReviewItem` records with `public_visibility=False` by default
- An `IngestionRun` record tracking status and counts

If `SourceSnapshot` cannot be created (e.g. API unavailable), the run fails — no records are created.

---

## CLI Usage

```bash
# CanLII Saskatchewan — dry run (no DB writes)
judgectl --json ingest canlii-sk --limit 10 --dry-run

# CanLII Saskatchewan — commit to DB as pending-review
judgectl --json ingest canlii-sk --limit 10 --commit

# Run any registered machine_ingest source
judgectl ingest run <source_key>

# Check status of a run
judgectl ingest status <run_id>
```

---

## Deduplication

Each `ReviewItem` is linked to a `SourceSnapshot`. If the same external ID is ingested twice, the existing record is updated (not duplicated). Deduplication is based on `external_id` + `source_key`.

---

## Alpha Limitations

- CanLII API requires a registered API key; without it, the adapter exits cleanly with a clear error
- Saskatchewan courts only (QB + CA) are the active machine-ingest paths
- Federal Court HTML parser is a stub (portal_reference)
- Statistical Canada sources require manual download
