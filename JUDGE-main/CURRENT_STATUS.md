# Current Status

Date: 2026-05-08

Release status: **alpha / reviewer-assisted / evidence-linked / source-dependent**.

## External/ directory

`external/` contains reference systems only — `CLI-Anything-main` and `memvid-Human--main-main`. Neither is imported by, vendored into, or required for the JUDGE-main runtime. They must not be treated as runtime dependencies, authoritative data stores, or production infrastructure.

## Operational today

- FastAPI backend with SQLAlchemy, Alembic, source registry, evidence snapshots, review queues, and audit log models.
- Next.js frontend with a MapLibre map workspace and admin/source/review surfaces.
- Local Docker Compose stack for Postgres/PostGIS, Redis, backend, and frontend.
- Click-based `judgectl` CLI with existing source, ingest, archive, audit, and health command patterns.
- Canada/Saskatchewan source registry YAML with explicit non-runnable classifications for unsupported sources.
- Root-level GitHub Actions quality/postgres gates execute against `JUDGE-main` paths from repository root.
- Frontend admin API proxy auth is JWT-only (httpOnly cookie/Bearer forwarding); legacy admin-token frontend wiring is removed.

## Source register states

Each source is classified by `source_class` and must be treated accordingly:

| Class | Meaning | Auto-ingestion allowed |
| --- | --- | --- |
| `machine_ingest` | Automated HTTP fetch + parser pipeline, parser version declared | Yes — after contract validation |
| `portal_reference` | Data exists on a public portal; no automated fetch pipeline | No — manual/portal only |
| `manual_upload` | Data arrives as human-supplied file uploads | No — human-gated |
| `disabled_stub` | Source is registered but intentionally non-operational | No |
| `None` (legacy) | Treated as `machine_ingest`; must be migrated or quarantined | Quarantine-gated |

Sources in `portal_reference`, `manual_upload`, or `disabled_stub` must never be promoted to auto-ingest without an explicit registry update and contract validation proof.

## Memory layer

`backend/app/memory/` is a **derivative layer** — it rebuilds summaries from authoritative evidence snapshots. Memory is not authoritative storage, not a primary source of truth, and does not replace or supersede evidence records. Public-facing answers that rely on memory claims must carry an explicit `ai_generated: true` and `requires_human_review: true` flag.

## AI layer

`backend/app/ai/` modules are **citation-bounded reviewer-assistance tools only**. No AI module produces guilt, danger, or corruption scores as publishable fields. All AI output is of type `reviewer_suggestion` and requires human review before any public action. AI modules are not legal adjudicators, do not deliver accountability conclusions autonomously, and do not produce binding legal findings.

## Not yet acceptable for public production use

- Shared-token admin compatibility remains for development and must not be used as public deployment auth.
- JWT/RBAC/session management still requires full-suite proof across all mutation paths.
- Evidence lineage exists but needs full immutable snapshot, replay, and duplicate-detection proof.
- Canadian law and legislation ingestion is partial; legal coverage is incomplete.
- Source adapters are source-dependent. Portal-only or unsupported sources are not automated ingestion pipelines.
- AI modules are reviewer-assistance/rule-based helpers, not legal adjudication.

## Required proof before a release candidate

1. Backend editable install and pytest pass.
2. Alembic single-head and upgrade proof pass.
3. Frontend `npm ci`, typecheck, and build pass.
4. Docker stack boots with explicit local secrets and smoke tests pass.
5. Source registry validation passes.
6. Banned-claim check passes.
7. Mutation endpoints enforce JWT/RBAC and write audit records with actor and before/after state.
