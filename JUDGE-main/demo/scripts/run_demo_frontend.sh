#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEMO_BACKEND_PORT="${DEMO_BACKEND_PORT:-8010}"
export NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:${DEMO_BACKEND_PORT}}"

cd "${ROOT_DIR}/frontend"
exec npm run dev
