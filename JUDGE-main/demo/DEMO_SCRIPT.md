# Demo Script: JUDGE Atlas Main 25

This script is for a truthful alpha demonstration only.

## Presenter Statement (Use Verbatim)

"This is a proof-hardened alpha legal/map evidence platform. It is not production-ready, not legally authoritative, and not a legal decision-maker. It does not score guilt, corruption, danger, or judicial worth. AI is reviewer-assistance only. Evidence snapshots are authoritative and memory is derivative. Source ingestion is disabled by default unless explicitly enabled."

## Preconditions

- Docker/PostGIS proof and release gate are already covered by project proof artifacts.
- Backend virtualenv exists at backend/.venv (or use a compatible Python environment).
- Frontend dependencies are installed.

## Demo Flow

1. Reset local demo DB (optional clean start)
- backend/.venv/bin/python demo/scripts/reset_demo_data.py

2. Seed synthetic demo fixtures
- backend/.venv/bin/python demo/scripts/seed_demo_data.py

3. Start backend (demo DB)
- ./demo/scripts/run_demo_backend.sh

4. Start frontend
- ./demo/scripts/run_demo_frontend.sh

5. Open UI
- http://localhost:3000/map-v2

6. Show reviewed/public visibility behavior
- Explain that reviewed/public records can appear on map endpoints.
- Explain that pending/private records are intentionally hidden.

7. Show API evidence quickly
- GET http://localhost:8010/api/map/events
- Confirm DEMO-EVT-PUBLIC-001 appears.
- Confirm DEMO-EVT-PRIVATE-001 does not appear.

8. Show governance and audit behavior
- Run: ./demo/scripts/verify_demo.sh
- Point to verification outputs confirming:
  - source registry fail-closed state for demo source
  - evidence snapshots and review items present
  - audit log row for demo seeding action

## Notes for Q&A

- No live external data is fetched by this demo.
- All records are synthetic fixtures for controlled demonstration.
- Public visibility is review-gated and cannot be bypassed by this package.
- This package adds no product features and does not alter runtime gates.
