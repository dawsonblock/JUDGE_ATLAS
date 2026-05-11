#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${ROOT_DIR}/demo"
BACKEND_LOG="${LOG_DIR}/backend-demo.log"
FRONTEND_LOG="${LOG_DIR}/frontend-demo.log"
DEMO_BACKEND_PORT="${DEMO_BACKEND_PORT:-8010}"
DEMO_FRONTEND_PORT="${DEMO_FRONTEND_PORT:-4173}"
DEMO_LAN_IP="${DEMO_LAN_IP:-$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)}"

mkdir -p "${LOG_DIR}"

DEMO_BACKEND_PORT="${DEMO_BACKEND_PORT}" "${ROOT_DIR}/demo/scripts/run_demo_backend.sh" >"${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!

cleanup() {
  if ps -p "${BACKEND_PID}" >/dev/null 2>&1; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "Backend started (pid=${BACKEND_PID}) log=${BACKEND_LOG}"
echo "Starting frontend; press Ctrl+C to stop both services."
echo "Demo backend base URL: http://localhost:${DEMO_BACKEND_PORT}"
echo "Demo frontend URL: http://localhost:${DEMO_FRONTEND_PORT}/map-v2"
if [[ -n "${DEMO_LAN_IP}" ]]; then
  echo "iPhone URL: http://${DEMO_LAN_IP}:${DEMO_FRONTEND_PORT}/map-v2"
fi

DEMO_BACKEND_PORT="${DEMO_BACKEND_PORT}" DEMO_FRONTEND_PORT="${DEMO_FRONTEND_PORT}" DEMO_LAN_IP="${DEMO_LAN_IP}" NEXT_PUBLIC_API_BASE_URL="http://localhost:${DEMO_BACKEND_PORT}" "${ROOT_DIR}/demo/scripts/run_demo_frontend.sh" >"${FRONTEND_LOG}" 2>&1
