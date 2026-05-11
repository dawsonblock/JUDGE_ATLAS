# judgectl Agent Skill

## What is THE-JUDGE?
THE-JUDGE is a controlled public-data accountability platform. Its job is to gather public legal, government, court, crime, police, statistics, and civic data from approved sources, preserve the evidence trail, review it safely, and then display it through maps, search, reports, and AI-assisted analysis.

## Core Rules
1. **Evidence is authoritative. Memory is derivative. AI is an operator, not a source of truth.**
2. The AI should not invent claims, scrape random websites, or directly write accusations into the system.
3. The AI should only operate approved tools (`judgectl`), ingest approved sources, and point back to evidence.
4. **Never** edit the database directly.
5. **Never** auto-publish legal/person/crime claims.
6. Evidence snapshots must be verified before relying on extracted claims.
7. Use the review queue before public display.

## Source Classes
Only specific sources can be automatically ingested.
- `machine_ingest`: Sources the system is allowed to run automatically. Only these can run.
- `portal_reference`: Useful public portals, but not automatically runnable. The agent should not blindly scrape them.
- `disabled_stub`: Planned future sources. Not runnable.
- News/context sources are not primary evidence.

## What is `judgectl`?
`judgectl` is the command-line control surface for the whole system. It is what an AI agent should use instead of touching internals.

### Agent Contract
- **Always** use `--json` for machine-readable output.
- All commands must return stable JSON envelopes.
- Use dry-run or explicit `--yes` for mutations (like enabling/disabling sources).

### Example Commands
```bash
judgectl --json health
judgectl --json sources list
judgectl --json sources validate
judgectl --json sources info federal_court_canada
judgectl --json ingest run federal_court_canada --limit 10
judgectl --json audit guards
```
