# Source Registry Additions: Tiered Structure

**Date:** 2026-05-11  
**Status:** All registry changes validated and passing source contract checks

## What Changed

The source registry now implements a **three-tier classification system** based on source honesty and runability:

- **TIER 1: Machine-Ingest** — Official APIs/XML with public licenses (9 sources)
- **TIER 2: Portal-Reference** — Official portals requiring manual review (11 sources)
- **TIER 3: Disabled Stub** — News/allegations with permanent review gates (3 sources)

### Before This Change

- 16 sources total
- Mix of machine_ingest and portal_reference, no clear pattern
- No tier separation for news vs. official sources
- No guidance for future additions

### After This Change

- 23 sources total (+7 new)
- Clear three-tier structure with distinct governance rules
- News sources explicitly marked as disabled_stub (not auto-publishable)
- Official XML/API sources prioritized in Tier 1
- Implementation order specified

## New Tier 1 Sources (Machine-Ingest)

These are the first real machine-ingest sources. No authentication required. Start here.

### 1. justice_canada_laws_xml

**Priority: HIGHEST**

```yaml
source_key: justice_canada_laws_xml
source_name: "Department of Justice Canada – Federal Laws XML"
source_class: machine_ingest
parser: justice_laws_xml
parser_version: "1.0"
requires_secret: false
allowed_domains: [laws-lois.justice.gc.ca, lois-laws.justice.gc.ca, open.canada.ca]
public_publish_default: true
```

**Why this first:**
- Official government source (Department of Justice Canada)
- Structured XML format from Open Canada
- No API key required
- Public domain license (Open Government Licence)
- Low risk, high impact

**What it produces:**
- ReviewItem records for federal Acts and Regulations
- Metadata: statute title, enactment date, amendment history
- Raw XML snapshots with hashes for evidence lineage

**Expected implementation loop:**
```
1. Fetch XML index from laws-lois.justice.gc.ca
2. Parse XML structure (statute metadata, amendments)
3. Create ReviewItem for each statute
4. Hash raw XML snapshot → evidence.raw_snapshot_bytes + hash
5. Admin reviews in /admin/review page
6. Approves for public → appears in /sources/{statute_id}
7. Link from map if geo-tagged, otherwise in legislation index
```

**Adapter Status:** Stub created (`backend/app/ingestion/source_adapters/justice_laws_xml.py`)
- Structure: ✓
- Parsing logic: TODO
- Tests: TODO

---

### 2. justice_canada_laws_pit_xml

**Priority: Second (after Tier 1.1 proven)**

Point-in-time (historical) versions of federal laws. Enables tracking legal changes over time.

```yaml
source_key: justice_canada_laws_pit_xml
source_name: "Department of Justice Canada – Point-in-Time Laws XML"
source_class: machine_ingest
parser: justice_laws_pit_xml
parser_version: "1.0"
requires_secret: false
```

**Difference from justice_canada_laws_xml:**
- Multiple versions tagged with effective dates
- Enables legal change analysis ("law X changed in year Y")
- Same official source, just historical

---

### 3. scc_judgments

**Priority: Second tier (after laws XML proven)**

Supreme Court of Canada judgments via Lexum API.

```yaml
source_key: scc_judgments
source_name: "Supreme Court of Canada – Judgments"
source_class: machine_ingest
parser: scc_lexum_api
parser_version: "1.0"
requires_secret: true
required_secret_name: LEXUM_API_KEY
allowed_domains: [scc-csc.ca, decisions.scc-csc.ca, scc-csc.lexum.com]
public_publish_default: true
```

**Key difference:** Requires LEXUM_API_KEY setup (unlike justice_canada_laws_xml)

---

## New Tier 2 Sources (Portal-Reference)

Official sources that need manual review or proven adapters before automation.

### 4. federal_court_canada_decisions

```yaml
source_key: federal_court_canada_decisions
source_class: portal_reference
automation_status: adapter_missing
admin_notes: "Adapter exists but needs stable pagination and HTML testing before promotion to machine_ingest"
```

**Current:** Portal-reference (manual review only)  
**Future:** Promote to machine_ingest once adapter is proven with real site

### 5. statscan_crime_tables

```yaml
source_key: statscan_crime_tables
source_class: portal_reference
admin_notes: "Promote to machine_ingest after pinning exact table IDs and writing schema tests"
```

Statistics Canada CCJS and UCR tables. Authoritative crime statistics but requires table ID pinning.

### 6. saskatchewan_legislation

```yaml
source_key: saskatchewan_legislation
source_class: portal_reference
admin_notes: "Portal-reference until stable XML/HTML/PDF endpoints and version metadata identified"
```

Provincial statutes and regulations.

### 7. saskatoon_open_data_public_safety

```yaml
source_key: saskatoon_open_data_public_safety
source_class: portal_reference
admin_notes: "Currently no crime/safety datasets exposed by city"
```

Municipal open data (waiting for datasets to emerge).

---

## New Tier 3 Sources (Disabled Stub)

News and press releases. **Always disabled by default.** Requires explicit review before publication.

### 8. saskatoon_police_news

```yaml
source_key: saskatoon_police_news
source_class: disabled_stub
parser: crawlee_police_release
public_record_authority: news_context
public_publish_default: false
admin_notes: "Press releases are incident reports/allegations, not court-proven facts"
```

**Critical rule:** When enabled by admin, requires mandatory review and must be published with `news_context` label, never as verified crime incident.

### 9. rcmp_sk_news

Same as above for RCMP Saskatchewan news releases.

---

## Registry Statistics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total sources | 16 | 23 | +7 |
| Machine-ingest | 6 | 9 | +3 |
| Portal-reference | 7 | 11 | +4 |
| Disabled stub | 3 | 3 | — |
| No secrets required | 12 | 18 | +6 |
| Requires CANLII key | 3 | 3 | — |
| Requires Lexum key | 1 | 2 | +1 |

---

## Key Design Decisions

### 1. Tier 1 (Machine-Ingest) Has Strict Gates

Only sources with:
- ✓ Official government or court API
- ✓ Structured data (XML, JSON, REST API)
- ✓ Public/open license
- ✓ No legal friction around scraping/redistribution

are classified as `machine_ingest`.

### 2. Portal-Reference Sources Don't Auto-Promote

A source stays `portal_reference` until:
- ✓ Adapter is proven with real data
- ✓ Schema/API structure is stable and versioned
- ✓ Pagination/filtering is handled correctly
- ✓ Tests confirm behavior with live site (not just fixtures)

**Only then** can an admin promote to `machine_ingest`.

### 3. News/Allegations Are Permanent Disabled Stub

News and press releases will **never** become fully-automated machine_ingest.

Reasons:
- Press releases are allegations, not adjudicated facts
- Terms of service often forbid bulk mining
- Risk: system becomes rumor engine without review
- Correct use: context/leads only, always reviewed, always labeled

---

## Validation

All new sources pass registry validation:

```
✓ SOURCE VALIDATION: PASS
✓ sources_checked=23
✓ All machine_ingest sources have required fields
✓ All sources have automation_status and public_visibility_policy
✓ No portal_reference sources have runnable automation_status
✓ All disabled_stub sources blocked from auto-enable
```

Registry validation script: `backend/tools/validate_sources.py`

---

## Next Steps

### Immediate
1. Implement `justice_laws_xml` adapter with real fetching and parsing
2. Create test fixtures from actual Justice Canada XML
3. Test end-to-end: fetch → parse → ReviewItem → review gate → public record
4. Verify evidence snapshot hashing and lineage

### After Tier 1.1 Proven
1. Add `justice_laws_pit_xml` (same source, historical versions)
2. Add `scc_judgments` (requires LEXUM_API_KEY)
3. Add Saskatchewan Court decisions (requires CANLII_API_KEY)

### Future Scalability
1. Identify more official XML/API sources (other provinces, federal agencies)
2. Promote portal_reference sources to machine_ingest as adapters prove stable
3. Document pattern for new source submission (must specify tier + reasoning)

---

## Design Principle: Honesty Over Coverage

This registry is designed to be **honest** about what is runnable, not to make the dashboard look full.

- ✓ Mark sources by true runability
- ✓ Explain why each source cannot run
- ✓ Keep news/allegations in review-only tier
- ✓ Promote portal_reference → machine_ingest only when proven

If the registry is dishonest, the platform becomes untrustworthy. Honesty is the foundation.

---

**Validated:** 2026-05-11 20:03:56 UTC  
**Status:** Ready for Tier 1 implementation  
**Proof:** `artifacts/proof/source_registry_status.json`
