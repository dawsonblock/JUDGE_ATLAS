#!/usr/bin/env bash
# run_full_proof.sh — mechanical enforcement proof for THE JUDGE
#
# Runs every architecture-enforcement guard in the repo and records dated
# artifacts.  Exit 0 means all guards passed and artifacts are committed.
# Exit 1 means at least one guard failed; see SUMMARY.md for which step.
#
# Usage:
#   bash scripts/run_full_proof.sh
#
# Environment overrides (all optional):
#   JTA_APP_ENV  — default "development"
#   JTA_DATABASE_URL — default in-memory sqlite
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ARTIFACT_ROOT="$PROJECT_ROOT/artifacts/proof"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$ARTIFACT_ROOT/enforcement-$TIMESTAMP"
VENV="$PROJECT_ROOT/backend/.venv"
PYTHON="$VENV/bin/python"

# Export minimal runtime environment
export JTA_APP_ENV="${JTA_APP_ENV:-development}"
export JTA_DATABASE_URL="${JTA_DATABASE_URL:-sqlite:///:memory:}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PROJECT_ROOT/backend"

mkdir -p "$RUN_DIR"

PASS=0
FAIL=0
SUMMARY="$RUN_DIR/SUMMARY.md"

log_step() {
    echo "==> $*" | tee -a "$RUN_DIR/proof.log"
}

# Run one named check.  Records stdout+stderr to <name>.log.
# On failure: records FAIL and continues (does not exit early).
run_check() {
    local name="$1"; shift
    local logfile="$RUN_DIR/${name}.log"
    log_step "CHECK: $name"
    set +e
    ("$@") >"$logfile" 2>&1
    local rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
        echo "  PASS: $name" | tee -a "$RUN_DIR/proof.log"
        echo "- [x] \`$name\` PASS" >> "$SUMMARY"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $name (exit $rc)" | tee -a "$RUN_DIR/proof.log"
        echo "- [ ] \`$name\` FAIL (see \`${name}.log\`)" >> "$SUMMARY"
        FAIL=$((FAIL + 1))
    fi
}

# --- Begin summary header ---
cat > "$SUMMARY" <<HEADER
# Enforcement Proof — $TIMESTAMP

Repo: $PROJECT_ROOT
Python: $("$PYTHON" --version 2>&1 || echo "venv not found")

## Guard Results

HEADER

log_step "Artifacts: $RUN_DIR"

cd "$PROJECT_ROOT/backend"

# 1 — Python compile-check (catches import-time syntax errors)
run_check "compile" \
    "$PYTHON" -m compileall -q app

# 2 — No direct network clients in ingestion adapters / tree
run_check "no-direct-ingestion-network-clients" \
    "$PYTHON" scripts/check_no_direct_ingestion_network_clients.py

# 3 — Repo boundary enforcement (NOT_RUNTIME sentinels, fetch boundary)
run_check "repo-boundary-enforcement" \
    "$PYTHON" "$PROJECT_ROOT/backend/scripts/check_repo_boundaries.py"

# 4 — No compiled .pyc artefacts committed
run_check "no-pyc" \
    bash scripts/check_no_pyc.sh

# 5 — No legacy hardcoded admin tokens in source
run_check "no-legacy-token" \
    "$PYTHON" scripts/check_no_legacy_token.py

# 6 — Canonical status constants are consistent
run_check "check-statuses" \
    "$PYTHON" "$PROJECT_ROOT/scripts/check_statuses.py"

# 7 — Source key registry coherence
run_check "check-source-keys" \
    "$PYTHON" "$PROJECT_ROOT/scripts/check_source_keys.py"

# 8 — Truth-claim guard (no unproven "Completed" claims)
run_check "truth-claims" \
    "$PYTHON" "$PROJECT_ROOT/scripts/check_truth_claims.py" --root "$PROJECT_ROOT"

# 9 — Unit tests (guard + contract + status tests)
run_check "backend-tests" \
    "$PYTHON" -m pytest -q \
        app/tests/test_no_direct_ingestion_network_clients.py \
        app/tests/test_source_automation_status_gate.py \
        app/tests/test_parser_version_contract.py \
        app/tests/test_run_persist_summary_truth.py \
        app/tests/test_ingestion_statuses.py

# --- Write summary footer ---
cat >> "$SUMMARY" <<FOOTER

## Totals

| Result | Count |
|--------|-------|
| PASS   | $PASS |
| FAIL   | $FAIL |

Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
FOOTER

log_step "Summary written: $SUMMARY"

# Record pointer to latest run
echo "$RUN_DIR" > "$ARTIFACT_ROOT/latest-enforcement-proof.txt"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "ERROR: $FAIL guard(s) failed. See $SUMMARY for details."
    exit 1
fi

echo ""
echo "All $PASS enforcement guards passed."
echo "Artifacts: $RUN_DIR"
