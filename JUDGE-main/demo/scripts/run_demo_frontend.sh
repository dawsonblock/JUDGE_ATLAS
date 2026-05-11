#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEMO_FRONTEND_PORT="${DEMO_FRONTEND_PORT:-4173}"
DEMO_BACKEND_PORT="${DEMO_BACKEND_PORT:-8010}"

if [[ ! -f "${ROOT_DIR}/demo/frontend/config.js" ]]; then
	echo "Missing demo/frontend/config.js" >&2
	exit 1
fi

cat > "${ROOT_DIR}/demo/frontend/config.js" <<EOF
window.DEMO_API_BASE = "http://localhost:${DEMO_BACKEND_PORT}";
EOF

cd "${ROOT_DIR}/demo/frontend"
echo "Serving demo frontend on http://localhost:${DEMO_FRONTEND_PORT} (API: http://localhost:${DEMO_BACKEND_PORT})"
exec python3 -m http.server "${DEMO_FRONTEND_PORT}"
