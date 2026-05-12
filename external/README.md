# External Reference Repositories

This directory contains **reference-only** copies of external repositories.

These are NOT part of the JUDGE-main runtime.

## Contents

- `CLI-Anything-main/` — Reference copy of CLI-Anything (not imported by JUDGE runtime)
- `memvid-Human--main-main/` — Reference copy of memvid (not imported by JUDGE runtime)

## Rules

1. These directories are **ignored** by JUDGE-main import paths
2. No code in `JUDGE-main/` may import from these directories
3. These are reference implementations for research/planning only
4. Do not merge these into the JUDGE-main runtime without explicit architectural review

## JUDGE-main runtime root

The primary runtime is located at `../JUDGE-main/`.

All backend dependencies, CLI tools, and tests live under `JUDGE-main/`.
