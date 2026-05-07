# Current Status

Date: 2026-05-06

Release status: **alpha / reviewer-assisted / evidence-linked / source-dependent**.

## Operational today

- FastAPI backend with SQLAlchemy, Alembic, source registry, evidence snapshots, review queues, and audit log models.
- Next.js frontend with a MapLibre map workspace and admin/source/review surfaces.
- Local Docker Compose stack for Postgres/PostGIS, Redis, backend, and frontend.
- Click-based `judgectl` CLI with existing source, ingest, archive, audit, and health command patterns.
- Canada/Saskatchewan source registry YAML with explicit non-runnable classifications for unsupported sources.

## Not yet acceptable for public production use

- Shared-token admin compatibility remains for development and must not be used as public deployment auth.
- JWT/RBAC/session management needs final role alignment and mutation-route proof.
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
