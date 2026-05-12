<div align="center">

<br/>

# ⚖️ JUDGE Atlas

### A map-first transparency platform for public court records and verified incident data.

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-research%20alpha-orange.svg)](https://github.com/dawsonblock/THE-JUDGE/issues)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](backend/pyproject.toml)
[![Node](https://img.shields.io/badge/Node.js-20+-339933.svg?logo=node.js&logoColor=white)](frontend/package.json)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000.svg?logo=next.js&logoColor=white)](frontend/package.json)
[![FastAPI](https://img.shields.io/badge/FastAPI-%3E%3D0.115-009688.svg?logo=fastapi&logoColor=white)](backend/pyproject.toml)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2BPostGIS-4169E1.svg?logo=postgresql&logoColor=white)](backend/pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-proof%20gated-brightgreen.svg)](artifacts/proof/current/CURRENT_PROOF.md)

<br/>

**[Documentation](./docs)** &nbsp;·&nbsp; **[Deployment Guide](./DEPLOYMENT.md)** &nbsp;·&nbsp; **[Report Issue](../../issues)** &nbsp;·&nbsp; **[API Reference](./docs/API.md)**

<br/>

</div>

---

## What Is This?

JUDGE Atlas maps federal court events — sentencing, detention orders, release decisions — to **verified public sources**. Every record links to an official court document or police open-data feed. Records pass automated privacy filters and human review before appearing on the map.

> **Research Alpha** — this is a hardened prototype, not production legal infrastructure. See [Known Gaps](#known-gaps).

---

## Highlights

<table>
<tr>
<td width="50%">

**🔗 Source-required records**
Every record links to a verified official source URL. No unattributed data, ever.

**🔒 Privacy by default**
Automatic redaction, anonymized defendants. No personal addresses exposed.

**🗺️ Map-first design**
Geographic exploration at court-level precision — never home-address resolution.

</td>
<td width="50%">

**👨‍⚖️ Judge tracking**
Connect events to judges with verified source evidence.

**✅ Human review queue**
All records reviewed before public display. Fail-closed by design.

**📡 Open data API**
GeoJSON endpoints for researchers and journalists. MIT licensed.

</td>
</tr>
</table>

---

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **API** | Python 3.11, FastAPI >=0.115.0 | OpenAPI docs at `/docs` |
| **Database** | PostgreSQL 16 + PostGIS | Spatial queries; geom index in place |
| **Frontend** | Next.js 14, React 18 | App Router; SSR disabled for map components |
| **Map v2** | MapLibre GL JS 4.x | OpenFreeMap tiles — no API key required |
| **Map legacy** | Leaflet 1.x | Original `/map` route |
| **CLI** | Click 8.1, `judgectl` | Local ingestion management; see [CLI Reference](#cli-judgectl) |
| **Auth** | JWT mutation authority (legacy shared-token compatibility deprecated) | See [Known Gaps](#known-gaps) |
| **Testing** | pytest (see canonical current proof artifacts for exact counts) | `make verify` and `make release-proof-local` |

---

## Proof Gate Reality

- Current status: proof-hardened alpha.
- Not ready for production deployment.
- Does not hold legal authority.
- Evidence snapshots are authoritative; memory is derivative.
- AI is reviewer assistance only (not a truth oracle).
- Source ingestion is disabled by default unless explicitly enabled.
- Canonical Justice law source key is `justice_canada_laws_xml` and remains review-required/public-private by default.
- Justice GitHub repositories (including Otto) are reference-only and not runtime imports.
- `external/` folders are reference-only, not runtime code.
- `make verify` runs local no-Docker quality checks.
- `make release-proof-local` runs the Docker/PostGIS alpha release gate.
- `bash scripts/proof_all_current.sh` runs current grouped backend/frontend proof and writes `artifacts/proof/release_readiness.md`.
- Alpha gate remains blocked when Docker/PostGIS proof fails.
- Repository runtime boundaries are documented in `docs/REPO_REALITY.md`.

---

## Quick Start

### Option 1 — Docker (Recommended)

```bash
cp .env.example .env
docker compose up --build
```

### Option 2 — Local Development

<details>
<summary><b>Prerequisites</b></summary>

- Python 3.11+ with `pyenv` (see `backend/pyproject.toml`)
- Node.js 20
- PostgreSQL 16 with PostGIS extension

</details>

**Backend (Terminal 1):**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
createdb judgetracker
python -m alembic upgrade head
JTA_APP_ENV=development uvicorn app.main:app --reload --port 8000
```

**Frontend (Terminal 2):**
```bash
cd frontend
npm install && npm run dev
```

### Available URLs

| URL | Description |
|-----|-------------|
| `http://localhost:3000` | Frontend dashboard |
| `http://localhost:3000/map-v2` | MapLibre GL map (v2) |
| `http://localhost:3000/map` | Leaflet map (legacy) |
| `http://localhost:8000/health` | Backend health check |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/api/map/events` | GeoJSON court events |
| `http://localhost:8000/api/map/crime-incidents` | GeoJSON crime incidents |

```bash
# quick smoke test
curl http://localhost:8000/health
curl "http://localhost:8000/api/map/events"
```

> Sample data auto-seeds when `JTA_AUTO_SEED=true`. No CourtListener token required for local dev.

---

## CLI — `judgectl`

The `judgectl` CLI manages ingestion sources and runs local ingest jobs without touching the HTTP API.

```bash
pip install -e ".[cli]"          # installs Click entry-point
judgectl --help
```

### Commands

```
judgectl [--json] health              Check backend + DB connectivity

judgectl [--json] sources list        List all registered ingestion sources
judgectl [--json] sources info KEY    Show full detail for a source
judgectl [--json] sources enable KEY  --yes  Mark source active
judgectl [--json] sources disable KEY --yes  Mark source inactive

judgectl [--json] ingest run KEY      Run ingestion for KEY synchronously
judgectl [--json] ingest status RUN_ID  Show run record

judgectl [--json] audit list          Show recent ingestion audit trail
judgectl [--json] audit show RUN_ID   Detailed audit for a single run
```

Pass `--json` to any command to receive machine-readable output:

```bash
$ judgectl --json sources list | jq '.[0].source_key'
"saskatoon_police_open_data"
```

**Gate enforcement:** `ingest run` refuses to start unless the source exists, has `source_class=machine_ingest`, and is marked active. Gate failures emit structured error JSON with `error_code` and `next_action` hints.

---

## Data Sources

All records come from **verified official sources only**:

| Source | Description |
|--------|-------------|
| **Court Records** | Federal court dockets via [CourtListener](https://www.courtlistener.com/) (RECAP/PACER) |
| **Police Open Data** | Official crime statistics from participating departments |
| **Government Stats** | Verified aggregate reports |
| **News Context** | Secondary context only — never a primary source |

**Publication Gate** — every record must pass before appearing on the map:

- ✅ Valid official source URL
- ✅ Reviewed and approved by a human admin
- ✅ No personal addresses or identifying details
- ✅ Privacy-safe location precision (city/neighbourhood level)

---

## Repository Layout

```text
.
├── backend/                             Python FastAPI backend
│   ├── alembic/                         Database migrations
│   ├── app/
│   │   ├── ai/                          Evidence-clerk pipeline
│   │   ├── api/routes/                  REST endpoints
│   │   │   ├── admin_review.py          Review queue + audit history
│   │   │   ├── ai_review.py             AI review item actions
│   │   │   ├── ingestion.py             Import trigger endpoints
│   │   │   ├── map.py                   GeoJSON map endpoints
│   │   │   └── public_events.py         Public event/case/judge API
│   │   ├── auth/                        Token auth + feature flags
│   │   ├── cli/                         judgectl CLI (Click 8)
│   │   │   ├── main.py                  Entry-point group
│   │   │   ├── output.py                Structured JSON/human output
│   │   │   └── commands/                health, sources, ingest, audit
│   │   ├── core/                        Pydantic settings
│   │   ├── db/                          SQLAlchemy + PostGIS
│   │   ├── ingestion/                   Data adapters + source registry
│   │   ├── models/                      SQLAlchemy ORM
│   │   ├── schemas/                     Pydantic schemas
│   │   ├── seed/                        Sample + registry seed data
│   │   └── tests/                       pytest suite (see artifacts/proof/current/backend_pytest.log)
│   ├── Dockerfile.backend
│   └── pyproject.toml
│
├── frontend/                            Next.js 14 frontend
│   ├── app/
│   │   ├── map-v2/                      MapLibre GL map (v2)
│   │   ├── map/                         Leaflet map (legacy)
│   │   ├── judges/                      Judge index + detail pages
│   │   ├── cases/                       Case pages
│   │   └── admin/                       Admin review queue UI
│   ├── components/
│   │   ├── maplibre/                    MapLibre GL components
│   │   │   ├── JudgeMap.tsx             Map canvas + context provider
│   │   │   ├── JudgeClusterLayer.tsx    GeoJSON source + cluster layers
│   │   │   ├── JudgeMapPopup.tsx        Click-to-popup detail card
│   │   │   ├── JudgeMapControls.tsx     Zoom / layer toggle controls
│   │   │   ├── JudgeMapLegend.tsx       Layer colour legend
│   │   │   ├── JudgeRelationshipArcs.tsx  Arc layer (stub, pending API)
│   │   │   └── JudgeMapDrawerBridge.tsx   Drawer↔map sync bridge
│   │   └── crime-map/                   Leaflet map components (legacy)
│   ├── lib/api.ts                       Type-safe API client
│   ├── Dockerfile
│   └── package.json
│
├── docs/                                Project documentation
│   ├── MAP_V2.md                        MapLibre map architecture
│   ├── UI_COMPONENTS.md                 Component API reference
│   ├── AI_PIPELINE.md                   Evidence clerk design
│   ├── API.md                           Full API reference
│   └── AUTH_ROADMAP.md                  Auth implementation plan
├── infra/                               Azure Bicep deployment
├── scripts/                             Verification scripts
├── artifacts/proof/                     Historical verification logs
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Environment Variables

Key variables from `.env.example`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `JTA_DATABASE_URL` | (required) | PostgreSQL connection string |
| `JTA_CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `JTA_ENABLE_ADMIN_REVIEW` | `false` | Enable review queue API |
| `JTA_ADMIN_REVIEW_TOKEN` | (empty) | Admin token for review endpoints |
| `JTA_ENABLE_ADMIN_IMPORTS` | `false` | Enable ingestion endpoints |
| `JTA_ADMIN_TOKEN` | (empty) | Token for import endpoints — **server-side only; never sent to browser** |
| `COURTLISTENER_API_TOKEN` | (empty) | CourtListener v4 API token |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Frontend → backend (browser) |
| `BACKEND_INTERNAL_URL` | `http://backend:8000` | Frontend → backend (Docker) |

> **Fail-Closed by Default:** Admin features require explicit opt-in. All admin endpoints return `403` unless enabled.

---

## API Endpoints

### Public Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/api/events` | Public events (paginated) |
| `GET` | `/api/events/{id}` | Single event detail |
| `GET` | `/api/cases` | Public cases |
| `GET` | `/api/judges` | Public judges |
| `GET` | `/api/map/events` | GeoJSON court events |
| `GET` | `/api/map/crime-incidents` | GeoJSON crime incidents |
| `GET` | `/api/evidence/source-panel/{type}/{id}` | Source evidence panel |

**Spatial Filtering:** Map endpoints support `?bbox=west,south,east,north` (WGS84). Uses lat/lon column comparisons (PostGIS geom column exists but not yet used for bbox queries).

```json
{
  "type": "FeatureCollection",
  "features": [...],
  "returned_count": 12,
  "truncated": false,
  "filters_applied": { "bbox": [-114.07, 51.0, -113.9, 51.1] },
  "disclaimer": "..."
}
```

### Admin Endpoints

<details>
<summary><b>Review Queue</b> (requires <code>JTA_ENABLE_ADMIN_REVIEW=true</code> + token)</summary>

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/admin/review-queue` | Paginated review queue |
| `POST` | `/api/admin/review-queue/{type}/{id}/decision` | Apply decision |
| `GET` | `/api/admin/review-history` | Audit trail |

**Valid decisions:** `approve`, `reject`, `correct`, `dispute`, `remove`

</details>

<details>
<summary><b>Data Imports</b> (requires <code>JTA_ENABLE_ADMIN_IMPORTS=true</code> + token)</summary>

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/ingest/courtlistener` | Trigger CourtListener ingestion |
| `POST` | `/api/admin/import/crime-incidents/manual-csv` | Upload crime CSV |
| `POST` | `/api/admin/ai/verify-source/{type}/{id}` | Verify source with Ollama |
| `GET` | `/api/admin/review/items` | AI review queue |
| `POST` | `/api/admin/review/items/{id}/{action}` | Act on AI review item |

</details>

---

## Data Model

```
Judge ──< Event >── Case ──< CaseParty >── Defendant
              │
              ├── EventSource ──> LegalSource
              ├── EventDefendant ──> Defendant
              ├── EventOutcome
              └── Location (court coordinates)

CrimeIncident   (separate layer — NOT linked to judges/cases)
EvidenceReview  (audit log of every review decision)
ReviewItem      (AI-generated evidence-clerk draft)

SourceRegistry  (registered ingestion sources + enabled/disabled state)
IngestionRun    (per-run audit record: source, started_at, status, row counts)
```

> **Fail-Closed:** All entities carry `review_status` and `public_visibility`. Nothing appears on the public API until `public_visibility=True` with an approved `review_status`. Ingestion is additionally gated by `SourceRegistry` — only sources with `source_class=machine_ingest` and `is_active=True` may run.

---

## Privacy & Safety Rules

> Code-enforced protections, not just policy:

| Rule | Implementation |
|------|----------------|
| **Anonymized Defendants** | Public API returns `DEF-000001` labels. Real names never exposed. |
| **No Personal Addresses** | DOBs, family details, victim locations redacted by serializer + AI pipeline. |
| **Court-Level Precision** | Map points are courthouse locations, never home/incident addresses. |
| **Generalized Coordinates** | Crime incidents use neighborhood/city centroids. `exact_address` rejected at import. |
| **Default Private** | CSV imports start `is_public=False`. Records require manual review. |
| **Valid Source Required** | Crime incidents need valid HTTP/HTTPS `source_url` or are rejected. |
| **Pending Review Default** | CourtListener events start `pending_review` / `public_visibility=False`. |
| **Explicit Flags Only** | Repeat-offender flags require matched phrases in source text. Never inferred. |
| **Verified Outcomes** | Outcomes require court/appeal/official sources. News is secondary only. |
| **Review Status Preserved** | Maintained on re-ingestion unless safety fields change (then drops to `pending_review`). |

---

## Ingestion

### CourtListener / RECAP

Set `COURTLISTENER_API_TOKEN` in `.env`. The adapter targets the v4 REST API (`/api/rest/v4/dockets/`), fetches RECAP/PACER docket entries, and persists them as `Event` + `LegalSource` rows.

Trigger a run locally with the CLI:

```bash
judgectl ingest run courtlistener_recap
```

- **Rate limiting:** Configurable max pages, dockets per run, timeout
- **Resilience:** Retry/backoff on 429 and 5xx
- **Concurrency:** Ingestion lock prevents concurrent runs
- **Scope:** PACER-direct document purchasing intentionally excluded
- **Gate:** Source must be registered in `SourceRegistry` with `source_class=machine_ingest` and `is_active=True`

### Manual CSV Import

Upload a CSV with columns:
```
source_id, incident_type, incident_category, reported_at, occurred_at,
latitude_public, longitude_public, precision_level, city, province_state,
country, public_area_label, notes, source_name, source_url, is_public
```

**Validation rejects:**
- `exact_address` precision
- Zero coordinates
- Residence/victim terms in notes/labels
- Non-HTTP source URLs

> All imports start `is_public=False` regardless of CSV value.

---

## AI-Assisted Evidence Clerk

Deterministic pipeline (no external LLM calls):

1. Redacts private data patterns from ingested text
2. Classifies record type and source quality
3. Writes neutral plain-language summary
4. Suggests entity links (judge, case, defendant)
5. Creates `ReviewItem` draft for admin review

> **AI outputs are not authoritative.** High-risk fields require human review. See [`docs/AI_PIPELINE.md`](./docs/AI_PIPELINE.md).

---

## Review Workflow

```
Ingested record
    │
    ▼
review_status = "pending_review"
public_visibility = False
    │
    ▼
Admin reviews via /api/admin/review-queue
    │
    ├── approve  → review_status = "verified_court_record"
    │                  public_visibility = True
    ├── reject   → review_status = "rejected"
    │                  public_visibility = False
    ├── correct  → review_status = "corrected"
    │                  public_visibility = True, correction_note set
    ├── dispute  → review_status = "disputed"
    │                  public_visibility = False, dispute_note set
    └── remove   → review_status = "removed_from_public"
                       public_visibility = False
    │
    ▼
EvidenceReview row written (audit trail)
```

All decisions logged to `EvidenceReview` and queryable via `GET /api/admin/review-history`.

---

## Verification Status

> Verify current state locally:

```bash
# Backend: creates .venv, installs deps, runs alembic + pytest
./scripts/verify_backend.sh

# Frontend: requires Node 20 — hard-fails if wrong version
./scripts/verify_frontend.sh

# Docker: compose build + health check
./scripts/verify_docker.sh
```

> Historical proof logs live under `artifacts/proof/`. Current authoritative proof state lives under `artifacts/proof/current/`.

<details>
<summary><b>What each script does</b></summary>

**`verify_backend.sh`** (hard-fail on any error):
1. Locate Python 3 interpreter
2. Create/reuse `backend/.venv`, run `pip install -e ".[test]"`
3. Print versions
4. `python -m compileall -q app`
5. `JTA_DATABASE_URL=sqlite:///./test.db alembic upgrade head`
6. `python -m pytest -q`

**`verify_frontend.sh`** (requires Node 20):
1. Node version check
2. `npm ci`
3. `npm run lint`
4. `npm run typecheck`
5. `npm run build`

</details>

### Current Status

| Check | Status | Notes |
|-------|--------|-------|
| `compileall` | ✅ Passing | Run `./scripts/verify_backend.sh` |
| `pytest` | See current proof artifact | `artifacts/proof/current/backend_pytest.log` is authoritative |
| Alembic migrations | See CI | SQLite test in verify script |
| Frontend lint/typecheck/build | See CI | Run `./scripts/verify_frontend.sh` |
| Docker Compose | Manual | Manual verification required |
| PostGIS geometry | Ready | Migration exists; bbox uses lat/lon |
| API split | Complete | Separate incidents/aggregates endpoints |
| CLI (`judgectl`) | ✅ Implemented | `health`, `sources`, `ingest`, `audit` |

---

## Known Gaps

> This is a prototype. The following are real gaps that must be closed before any production use:

<details>
<summary><b>Auth & Access Control</b></summary>

- No real authentication system. Admin access uses a single shared secret token (`X-JTA-Admin-Token`). No user accounts, sessions, roles, or per-user audit trails.
- Token compared in plaintext. No rate limiting on auth attempts.

</details>

<details>
<summary><b>Database & Migrations</b></summary>

- Alembic `upgrade head` not exercised in CI. Migration file matches ORM (audited in `docs/schema_audit.md`) but no automated migration test in this runtime.
- `Base.metadata.create_all()` used on startup when `AUTO_SEED=true`, bypassing Alembic for local development.

</details>

<details>
<summary><b>Security (Partially Hardened)</b></summary>

| Hardened | Gap |
|----------|-----|
| ✅ Rate limiting (in-memory: 100/min public, 30/min admin) | ❌ No security headers (CSP, HSTS) |
| ✅ Request size limits | ❌ No secrets management — plain `.env` tokens |
| ✅ CORS strict validation | ❌ No complete security audit |
| ✅ Source verification with SSRF protection | |
| ✅ SourceRegistry fail-closed ingestion | |
| ✅ Admin token (`JTA_ADMIN_TOKEN`) server-side only | |
| ✅ Source-class enforcement: only `machine_ingest` eligible for API enable/run | |

</details>

<details>
<summary><b>Data & Legal</b></summary>

- Only **SAMPLE data** seeded. No real court data included.
- CourtListener ingestion not exercised end-to-end in this environment.
- Source licensing for real data not reviewed.
- Crime incidents: manual CSV only (Saskatoon). No automatic police open-data adapter.
- No geocoding pipeline. Court coordinates pre-seeded or manual.

</details>

<details>
<summary><b>Operational</b></summary>

- No production monitoring, alerting, or structured logging pipeline
- No automated backups
- No audit log retention policy or storage backend
- `on_event("startup")` deprecated in FastAPI; needs `lifespan` migration
- PostGIS: bbox filtering uses lat/lon only (geom column exists but not yet trusted)
- Docker Compose: manual verification required

</details>

<details>
<summary><b>Features Not Implemented</b></summary>

- Source correction/dispute resolution workflow UI
- User-facing source dispute submission
- Full CourtListener coverage (PACER-direct intentionally excluded)
- Court-location geocoding
- Real-time ingestion / webhooks
- Export or bulk download

</details>
