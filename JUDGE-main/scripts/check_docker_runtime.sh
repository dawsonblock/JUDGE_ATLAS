#!/usr/bin/env bash
set -euo pipefail

# Preflight Docker runtime diagnostics for proof gating.
# This script is intentionally fast-failing so release_gate can report
# environment blockers before PostGIS setup begins.

DOCKER_TIMEOUT_SECONDS="${JTA_DOCKER_CHECK_TIMEOUT:-60}"

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
        "[docker_runtime] ERROR: command timed out "
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

echo "[docker_runtime] Checking docker CLI availability..."
if ! command -v docker >/dev/null 2>&1; then
    echo "[docker_runtime] FAIL: docker command not found"
    echo "[docker_runtime] HINT: install Docker CLI and ensure it is on PATH"
    exit 1
fi
echo "[docker_runtime] PASS: docker CLI found: $(command -v docker)"
echo "[docker_runtime] INFO: timeout=${DOCKER_TIMEOUT_SECONDS}s"

echo "[docker_runtime] Running docker version..."
if ! run_with_timeout "$DOCKER_TIMEOUT_SECONDS" docker version; then
    echo "[docker_runtime] FAIL: docker version failed"
    echo "[docker_runtime] HINT: start Docker Desktop or verify daemon/socket access"
    exit 1
fi
echo "[docker_runtime] PASS: docker version"

echo "[docker_runtime] Running docker info..."
if ! run_with_timeout "$DOCKER_TIMEOUT_SECONDS" docker info; then
    echo "[docker_runtime] FAIL: docker info failed"
    echo "[docker_runtime] HINT: check daemon state and permissions to Docker socket"
    exit 1
fi
echo "[docker_runtime] PASS: docker daemon reachable"
echo "[docker_runtime] PASS: docker info"

echo "[docker_runtime] Checking postgis image metadata..."
if run_with_timeout "$DOCKER_TIMEOUT_SECONDS" docker image inspect postgis/postgis:16-3.4 >/dev/null 2>&1; then
    echo "[docker_runtime] PASS: postgis image present locally"
else
    echo "[docker_runtime] INFO: postgis image not found locally"
fi

echo "[docker_runtime] SUCCESS: Docker runtime preflight completed"
