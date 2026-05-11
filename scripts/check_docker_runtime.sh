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

classify_docker_failure() {
    local output="$1"
    if printf '%s' "$output" | grep -Eiq 'permission denied.*docker\.sock|got permission denied while trying to connect to the docker daemon socket'; then
        echo "permission"
        return
    fi
    if printf '%s' "$output" | grep -Eiq 'cannot connect to the docker daemon|is the docker daemon running|error during connect|docker desktop.*(not running|stopped)|cannot connect to the docker daemon at'; then
        echo "daemon"
        return
    fi
    echo "generic"
}

run_docker_check() {
    local label="$1"
    shift

    local tmp
    tmp="$(mktemp)"
    if run_with_timeout "$DOCKER_TIMEOUT_SECONDS" "$@" >"$tmp" 2>&1; then
        cat "$tmp"
        rm -f "$tmp"
        echo "[docker_runtime] PASS: ${label} completed"
        return 0
    fi

    local rc="$?"
    local output
    output="$(cat "$tmp")"
    cat "$tmp"
    rm -f "$tmp"

    if [ "$rc" -eq 124 ]; then
        echo "[docker_runtime] FAIL: ${label} timed out after ${DOCKER_TIMEOUT_SECONDS}s"
        echo "[docker_runtime] HINT: start Docker Desktop or verify Docker daemon/socket access"
        return 1
    fi

    case "$(classify_docker_failure "$output")" in
        permission)
            echo "[docker_runtime] FAIL: permission denied while accessing Docker daemon/socket"
            echo "[docker_runtime] HINT: verify user access to Docker socket and that Docker Desktop is running"
            ;;
        daemon)
            echo "[docker_runtime] FAIL: docker daemon unavailable"
            echo "[docker_runtime] HINT: start Docker Desktop and retry once daemon is healthy"
            ;;
        *)
            echo "[docker_runtime] FAIL: ${label} failed"
            echo "[docker_runtime] HINT: inspect docker diagnostics and local daemon configuration"
            ;;
    esac
    return 1
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
if ! run_docker_check "docker version" docker version; then
    exit 1
fi
echo "[docker_runtime] PASS: docker version completed"

echo "[docker_runtime] Running docker info..."
if ! run_docker_check "docker info" docker info; then
    exit 1
fi
echo "[docker_runtime] PASS: docker daemon reachable"
echo "[docker_runtime] PASS: docker info completed"

echo "[docker_runtime] Checking postgis image metadata..."
if run_with_timeout "$DOCKER_TIMEOUT_SECONDS" docker image inspect postgis/postgis:16-3.4 >/dev/null 2>&1; then
    echo "[docker_runtime] PASS: postgis image present locally"
else
    echo "[docker_runtime] INFO: postgis image not found locally"
fi

echo "[docker_runtime] SUCCESS: Docker runtime preflight completed"
