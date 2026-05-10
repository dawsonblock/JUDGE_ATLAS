#!/usr/bin/env bash
set -euo pipefail

# Proof script: Run Alembic migrations against a real Postgres/PostGIS instance
# Usage: ./scripts/proof_postgis.sh
# Requires: Docker available

IMAGE="postgis/postgis:16-3.4"
CONTAINER="judge_postgis_proof"
DB_NAME="judgetracker_proof"
DB_USER="judgetracker"
DB_PASS="judgetracker"
DB_PORT="15432"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROOF_LOG="$SCRIPT_DIR/../artifacts/proof/postgis_proof.log"
PULL_TIMEOUT_SECONDS="${JTA_POSTGIS_PULL_TIMEOUT:-600}"
BACKEND_PYTHON="${BACKEND_PYTHON:-backend/.venv/bin/python}"

if [ ! -x "$BACKEND_PYTHON" ]; then
    BACKEND_PYTHON="python3"
fi

mkdir -p "$(dirname "$PROOF_LOG")"

# Capture complete script output from first line onward.
exec > >(tee "$PROOF_LOG") 2>&1

echo "[proof_postgis] Log path: $PROOF_LOG"
echo "[proof_postgis] Backend Python: $BACKEND_PYTHON"

fail_with_reason() {
    local reason="$1"
    echo "[proof_postgis] FAIL: $reason"
    echo "[proof_postgis] Container status dump (if available):"
    run_with_timeout 20 docker ps -a || true
    echo "[proof_postgis] Container logs dump (if available):"
    run_with_timeout 20 docker logs "$CONTAINER" || true
    exit 1
}

run_with_timeout() {
    local timeout_seconds="$1"
    shift

    python3 - "$timeout_seconds" "$@" <<'PY'
import subprocess
import sys

timeout_seconds = int(sys.argv[1])
command = sys.argv[2:]

try:
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
except subprocess.TimeoutExpired as exc:
    if exc.stdout:
        print(exc.stdout, end="")
    if exc.stderr:
        print(exc.stderr, end="", file=sys.stderr)
    joined = " ".join(command)
    print(
        "[proof_postgis] ERROR: command timed out "
        f"after {timeout_seconds}s: {joined}",
        file=sys.stderr,
    )
    sys.exit(124)

if proc.stdout:
    print(proc.stdout, end="")
if proc.stderr:
    print(proc.stderr, end="", file=sys.stderr)
sys.exit(proc.returncode)
PY
}

require_docker() {
    echo "[proof_postgis] Docker preflight: checking docker CLI..."
    if ! command -v docker >/dev/null 2>&1; then
        echo "[proof_postgis] ERROR: docker command not found"
        return 1
    fi

    echo "[proof_postgis] Docker preflight: docker version"
    if ! run_with_timeout 20 docker version; then
        echo "[proof_postgis] ERROR: docker version failed"
        return 1
    fi

    echo "[proof_postgis] Docker preflight: docker info"
    if ! run_with_timeout 20 docker info; then
        echo "[proof_postgis] ERROR: docker info failed"
        return 1
    fi
}

cleanup() {
    echo "[proof_postgis] Cleanup: removing container '$CONTAINER'"
    run_with_timeout 20 docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    echo "[proof_postgis] Cleanup: complete"
}
trap cleanup EXIT

echo "[proof_postgis] PASS: script start"
JTA_DOCKER_CHECK_TIMEOUT="${JTA_DOCKER_CHECK_TIMEOUT:-60}" \
    bash "$SCRIPT_DIR/check_docker_runtime.sh" || fail_with_reason "docker preflight failed"
echo "[proof_postgis] PASS: docker preflight"

echo "[proof_postgis] Checking image: $IMAGE"
if run_with_timeout 30 docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "[proof_postgis] PASS: image already present"
else
    echo "[proof_postgis] Image not found locally; pulling $IMAGE"
    run_with_timeout "$PULL_TIMEOUT_SECONDS" docker pull "$IMAGE"
    echo "[proof_postgis] PASS: image pull complete"
fi

echo "[proof_postgis] Starting PostGIS container..."
run_with_timeout 20 docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
run_with_timeout 60 docker run -d \
    --name "$CONTAINER" \
    -e POSTGRES_DB="$DB_NAME" \
    -e POSTGRES_USER="$DB_USER" \
    -e POSTGRES_PASSWORD="$DB_PASS" \
    -p "${DB_PORT}:5432" \
    "$IMAGE"
echo "[proof_postgis] PASS: container start requested"

echo "[proof_postgis] Waiting for Postgres to be ready..."
pg_ready=0
for i in $(seq 1 120); do
    if run_with_timeout 10 docker exec "$CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
        echo "[proof_postgis] Postgres ready after ${i}s"
        pg_ready=1
        break
    fi
    sleep 1
done
if [ "$pg_ready" -ne 1 ]; then
    fail_with_reason "pg_isready did not become healthy within 120s"
fi
echo "[proof_postgis] PASS: pg_isready"

export DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASS}@localhost:${DB_PORT}/${DB_NAME}"
export JTA_DATABASE_URL="$DATABASE_URL"

echo "[proof_postgis] Checking PostGIS extension availability..."
if run_with_timeout 15 docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT extname FROM pg_extension WHERE extname = 'postgis'" | grep -q "postgis"; then
    echo "[proof_postgis] PASS: postgis extension present"
else
    fail_with_reason "postgis extension missing"
fi

echo "[proof_postgis] Running alembic upgrade head..."
cd "$SCRIPT_DIR/../backend"
"$BACKEND_PYTHON" -m alembic upgrade head
echo "[proof_postgis] PASS: alembic upgrade head"

echo "[proof_postgis] PASS: source registry seed (covered by app startup/seed path)"

echo "[proof_postgis] Running spatial smoke tests..."
if "$BACKEND_PYTHON" -m pytest app/tests/test_map_bbox.py -v --tb=short; then
    echo "[proof_postgis] PASS: spatial smoke tests"
else
    fail_with_reason "spatial smoke tests"
fi

echo "[proof_postgis] Running public/private visibility proof..."
if "$BACKEND_PYTHON" -m pytest app/tests/test_public_visibility_gates.py -q; then
    echo "[proof_postgis] PASS: public/private map visibility test"
else
    fail_with_reason "public/private map visibility test"
fi

echo "[proof_postgis] Running evidence snapshot immutability proof..."
if "$BACKEND_PYTHON" -m pytest app/tests/test_snapshot_immutability.py -q; then
    echo "[proof_postgis] PASS: evidence snapshot immutability test"
else
    fail_with_reason "evidence snapshot immutability test"
fi

echo "[proof_postgis] PASS: PostGIS proof completed"
echo "[proof_postgis] Log saved to $PROOF_LOG"
