# JUDGE Atlas Demo Package

This demo package provides a clean, local, synthetic demonstration of what the current platform does.

Scope shown by this demo:
- public map visualization
- reviewed/public event visibility
- private/unreviewed record hiding
- source registry governance
- evidence snapshot workflow
- review-gated publication behavior
- audit trail behavior
- controlled ingestion using synthetic data fixtures
- API/frontend contract-compatible usage of existing runtime endpoints

Safety and truth boundaries for this demo:
- Alpha status only.
- Not a legal decision-maker.
- No guilt, corruption, danger, or judicial-worth scoring.
- AI features are reviewer-assistance only.
- Evidence snapshots are authoritative; memory is derivative.
- Source ingestion is disabled by default unless explicitly enabled.
- No live scraping is used by this demo.

Authoritative runtime:
- Use JUDGE-main only.
- This demo package does not change core runtime behavior.

## Files

- demo/DEMO_SCRIPT.md: step-by-step demo flow for presenters.
- demo/demo_data/: synthetic fixtures for source registry, events, snapshots, and review items.
- demo/scripts/seed_demo_data.py: idempotent fixture seeding into isolated demo database.
- demo/scripts/reset_demo_data.py: remove the isolated demo database file.
- demo/scripts/run_demo_backend.sh: start backend with demo DB and seeded fixtures.
- demo/scripts/run_demo_frontend.sh: start the full Next.js frontend pointing to local backend.
- demo/scripts/run_demo_stack.sh: one-command stack runner with logs.
- demo/scripts/verify_demo.sh: verify visibility gates, governance rows, and API behavior.

## Quick Start

1. Start backend:
   - ./demo/scripts/run_demo_backend.sh
2. Start frontend in a second shell:
   - ./demo/scripts/run_demo_frontend.sh
3. Open map route:
   - http://localhost:4173/map-v2
4. Verify demo invariants:
   - ./demo/scripts/verify_demo.sh

## Local Logs

The stack runner writes logs to:
- demo/backend-demo.log
- demo/frontend-demo.log

A successful verification shows:
- public reviewed fixture event is visible in /api/map/events
- private pending fixture event is hidden from /api/map/events
- source_registry demo row exists in fail-closed state
- source_snapshots and review_items demo rows exist
- demo seeding action is audit-logged

Default demo backend URL:
- http://localhost:8010

You can override the backend port:
- DEMO_BACKEND_PORT=8123 ./demo/scripts/run_demo_backend.sh
- DEMO_BACKEND_PORT=8123 ./demo/scripts/run_demo_frontend.sh
- DEMO_BACKEND_PORT=8123 ./demo/scripts/verify_demo.sh

You can override the demo frontend port:
- DEMO_FRONTEND_PORT=5050 ./demo/scripts/run_demo_frontend.sh

## iPhone Access

1. Ensure your iPhone and Mac are on the same Wi-Fi network.
2. Start backend and frontend using the demo scripts.
3. Use the "iPhone UI URL" printed by `run_demo_frontend.sh`.
4. Open that URL in Safari on your iPhone.

Notes:
- The backend script now binds to `0.0.0.0` for LAN access.
- `run_demo_frontend.sh` auto-detects your Mac LAN IP and uses it for API calls by default.
- If auto-detection fails, provide the IP explicitly:
   - `DEMO_LAN_IP=192.168.1.50 ./demo/scripts/run_demo_backend.sh`
   - `DEMO_LAN_IP=192.168.1.50 ./demo/scripts/run_demo_frontend.sh`

## Interpreter Note

The demo seeding script requires Python 3.11+ (same as backend runtime).
If needed, run explicitly with:
- backend/.venv/bin/python demo/scripts/reset_demo_data.py
- backend/.venv/bin/python demo/scripts/seed_demo_data.py
