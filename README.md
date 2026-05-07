# THE-JUDGE

**A controlled public-data accountability platform.**

THE-JUDGE gathers public legal, government, court, crime, police, statistics, and civic data from approved sources, preserves the evidence trail, reviews it safely, and displays it through maps, search, reports, and AI-assisted analysis.

## Core Principle

> Evidence is authoritative. Memory is derivative. AI is an operator, not a source of truth.

## Repository Structure

```
THE-JUDGE/
  README.md               ← This file (authoritative workspace entry point)
  JUDGE-main/             ← The actual platform (backend, frontend, database, CLI)
  CLI-Anything-main/      ← Reference pattern only (not imported by JUDGE runtime)
  memvid-Human--main-main/ ← Reference archive sidecar (not the operational database)
  external/
    README.md             ← Explains reference-only role of external repos
  docs/
    INTEGRATION_PLAN.md   ← How external components integrate with JUDGE
```

> **Note:** `CLI-Anything-main/` and `memvid-Human--main-main/` are **reference-only** repositories.
> They are NOT imported by the JUDGE-main runtime. The `external/README.md` documents their
> reference-only role. `THE-JUDGE.sln` is a legacy Visual Studio solution file; it is not the
> build entrypoint. The Python backend under `JUDGE-main/backend/` is the authoritative runtime.

## Quick Start

```bash
cd JUDGE-main/backend
pip install -e ".[test]"
judgectl --json health
judgectl --json sources list
judgectl --json audit guards
```

## Component Roles

| Component | Role |
|---|---|
| `JUDGE-main` | The actual platform — backend, frontend, ingestion, evidence, review queue |
| `CLI-Anything-main` | Reference pattern only — contributes the `judgectl` CLI contract idea |
| `memvid-Human--main` | Future archive sidecar — portable `.mv2` evidence bundles |

## Agent Contract

AI agents interact with THE-JUDGE exclusively via `judgectl`. See:
- `JUDGE-main/skills/judgectl/SKILL.md` — agent instruction contract
- `JUDGE-main/docs/JUDGECTL_CONTRACT.md` — full CLI contract documentation
- `JUDGE-main/tools/registry.json` — approved tool registry

## External Components

`CLI-Anything-main` and `memvid-Human--main-main` are **reference components**, not runtime dependencies. They are kept in this repository for context but must not be merged into the JUDGE runtime.
