#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEMO_DB_PATH="${ROOT_DIR}/demo/demo.sqlite3"
DEMO_BACKEND_PORT="${DEMO_BACKEND_PORT:-8010}"
DEMO_FRONTEND_PORT="${DEMO_FRONTEND_PORT:-4173}"
DEMO_LAN_IP="${DEMO_LAN_IP:-$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)}"
export JTA_DATABASE_URL="${JTA_DATABASE_URL:-sqlite:///${DEMO_DB_PATH}}"
export JTA_APP_ENV="development"
export JTA_AUTO_SEED="false"
export JTA_SEED_SOURCE_REGISTRY="false"

DEFAULT_CORS="http://localhost:3000,https://localhost:3000,http://127.0.0.1:3000,http://localhost:${DEMO_FRONTEND_PORT},http://127.0.0.1:${DEMO_FRONTEND_PORT}"
if [[ -n "${DEMO_LAN_IP}" ]]; then
  DEFAULT_CORS+=",http://${DEMO_LAN_IP}:${DEMO_FRONTEND_PORT}"
fi
export JTA_CORS_ORIGINS="${JTA_CORS_ORIGINS:-${DEFAULT_CORS}}"

PYTHON_BIN="${ROOT_DIR}/backend/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" "${ROOT_DIR}/demo/scripts/seed_demo_data.py"

cd "${ROOT_DIR}/backend"
echo "Starting demo backend on http://0.0.0.0:${DEMO_BACKEND_PORT}"
if [[ -n "${DEMO_LAN_IP}" ]]; then
  echo "iPhone/API URL: http://${DEMO_LAN_IP}:${DEMO_BACKEND_PORT}"
fi
exec "${PYTHON_BIN}" -m uvicorn app.main:app --reload --host 0.0.0.0 --port "${DEMO_BACKEND_PORT}"
