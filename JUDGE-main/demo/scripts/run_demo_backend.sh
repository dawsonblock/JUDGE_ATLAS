#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEMO_DB_PATH="${ROOT_DIR}/demo/demo.sqlite3"
DEMO_BACKEND_PORT="${DEMO_BACKEND_PORT:-8010}"
export JTA_DATABASE_URL="${JTA_DATABASE_URL:-sqlite:///${DEMO_DB_PATH}}"
export JTA_APP_ENV="development"
export JTA_AUTO_SEED="false"
export JTA_SEED_SOURCE_REGISTRY="false"
export JTA_CORS_ORIGINS="http://localhost:3000,https://localhost:3000"

PYTHON_BIN="${ROOT_DIR}/backend/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" "${ROOT_DIR}/demo/scripts/seed_demo_data.py"

cd "${ROOT_DIR}/backend"
exec "${PYTHON_BIN}" -m uvicorn app.main:app --reload --port "${DEMO_BACKEND_PORT}"
