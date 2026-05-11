#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEMO_FRONTEND_PORT="${DEMO_FRONTEND_PORT:-4173}"
DEMO_BACKEND_PORT="${DEMO_BACKEND_PORT:-8010}"
DEMO_LAN_IP="${DEMO_LAN_IP:-$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)}"

export NEXT_PUBLIC_API_PORT="${NEXT_PUBLIC_API_PORT:-${DEMO_BACKEND_PORT}}"
export PORT="${PORT:-${DEMO_FRONTEND_PORT}}"

if [[ ! -f "${ROOT_DIR}/frontend/package.json" ]]; then
	echo "Missing frontend/package.json" >&2
	exit 1
fi

cd "${ROOT_DIR}/frontend"
echo "Starting full Next.js frontend on http://localhost:${PORT} (map route: /map-v2)"
if [[ -n "${NEXT_PUBLIC_API_BASE_URL:-}" ]]; then
	echo "Frontend API base override: ${NEXT_PUBLIC_API_BASE_URL}"
else
	echo "Frontend API base: dynamic host resolution on port ${NEXT_PUBLIC_API_PORT}"
fi
if [[ -n "${DEMO_LAN_IP}" ]]; then
	echo "iPhone UI URL: http://${DEMO_LAN_IP}:${PORT}/map-v2"
fi
exec npm run dev -- -p "${PORT}"
