#!/usr/bin/env bash
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS_DIR="$REPO_ROOT/artifacts/proof"
HISTORY_DIR="$REPO_ROOT/artifacts/history/proof"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"

mkdir -p "$ARTIFACTS_DIR"
mkdir -p "$HISTORY_DIR"
mkdir -p "$ARTIFACTS_DIR/backend"

if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"
else
  BACKEND_PYTHON="python3"
fi

STATUS_FILE="$ARTIFACTS_DIR/.proof_status.tmp"
: > "$STATUS_FILE"

archive_existing_artifacts() {
  local stamp
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  local target="$HISTORY_DIR/$stamp"
  mkdir -p "$target"

  local paths=(
    "$ARTIFACTS_DIR/backend"
    "$ARTIFACTS_DIR/backend_compile.log"
    "$ARTIFACTS_DIR/backend_import.log"
    "$ARTIFACTS_DIR/backend_grouped_tests_summary.log"
    "$ARTIFACTS_DIR/frontend_typecheck.log"
    "$ARTIFACTS_DIR/frontend_contracts.log"
    "$ARTIFACTS_DIR/frontend_lint.log"
    "$ARTIFACTS_DIR/frontend_build.log"
    "$ARTIFACTS_DIR/source_registry_status.log"
    "$ARTIFACTS_DIR/source_registry_status.json"
    "$ARTIFACTS_DIR/release_readiness.md"
  )

  local moved_any=0
  for p in "${paths[@]}"; do
    if [[ -e "$p" ]]; then
      mv "$p" "$target/"
      moved_any=1
    fi
  done

  if [[ $moved_any -eq 0 ]]; then
    rmdir "$target" 2>/dev/null || true
  fi
}

run_step() {
  local name="$1"
  local log_path="$2"
  shift 2
  local command=("$@")

  echo "[proof_all_current] STEP=$name"
  {
    echo "STEP=$name"
    echo "STARTED_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "COMMAND=${command[*]}"
    echo
  } > "$log_path"

  set +e
  "${command[@]}" >> "$log_path" 2>&1
  local rc=$?
  set -e

  {
    echo
    echo "ENDED_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "EXIT_CODE=$rc"
  } >> "$log_path"

  if [[ $rc -eq 0 ]]; then
    echo "$name|PASS|$log_path" >> "$STATUS_FILE"
  elif [[ $rc -eq 124 ]]; then
    echo "$name|TIMEOUT|$log_path" >> "$STATUS_FILE"
  else
    echo "$name|FAIL|$log_path" >> "$STATUS_FILE"
  fi
  return 0
}

set -e

archive_existing_artifacts

run_step "backend_compile" "$ARTIFACTS_DIR/backend_compile.log" \
  "$BACKEND_PYTHON" -m compileall -q "$REPO_ROOT/backend/app" "$REPO_ROOT/backend/tools"

run_step "backend_import" "$ARTIFACTS_DIR/backend_import.log" \
  "$BACKEND_PYTHON" "$REPO_ROOT/backend/scripts/proof_backend_import.py"

run_step "backend_targeted_tests" "$ARTIFACTS_DIR/backend_targeted_tests.log" \
  "$BACKEND_PYTHON" -m pytest \
  "$REPO_ROOT/backend/app/tests/test_factory_config_passthrough.py" \
  "$REPO_ROOT/backend/app/tests/test_source_run_policy.py" \
  "$REPO_ROOT/backend/app/tests/test_admin_source_run_status_truth.py" \
  -q

run_step "backend_grouped_tests" "$ARTIFACTS_DIR/backend_grouped_tests_summary.log" \
  "$BACKEND_PYTHON" "$REPO_ROOT/scripts/proof_backend_groups.py"

run_step "backend_justice_laws" "$ARTIFACTS_DIR/backend/justice_laws.log" \
  "$BACKEND_PYTHON" -m pytest \
  "$REPO_ROOT/backend/app/tests/test_justice_laws_xml.py" \
  "$REPO_ROOT/backend/app/tests/test_justice_laws_phase4.py" \
  -q

run_step "backend_source_registry" "$ARTIFACTS_DIR/backend/source_registry.log" \
  bash -lc "\
    $BACKEND_PYTHON -m pytest \
      $REPO_ROOT/backend/app/tests/test_source_registry_contracts.py \
      $REPO_ROOT/backend/app/tests/test_source_registry_canada.py \
      $REPO_ROOT/backend/app/tests/test_source_keys.py -q && \
    $BACKEND_PYTHON $REPO_ROOT/scripts/export_source_registry_status.py --output $ARTIFACTS_DIR/source_registry_status.json\
  "

run_step "backend_boundary" "$ARTIFACTS_DIR/backend/boundary.log" \
  "$BACKEND_PYTHON" "$REPO_ROOT/backend/scripts/check_repo_boundaries.py"

run_step "frontend_typecheck" "$ARTIFACTS_DIR/frontend_typecheck.log" \
  npm run typecheck --prefix "$FRONTEND_DIR"

run_step "frontend_contracts" "$ARTIFACTS_DIR/frontend_contracts.log" \
  npm run test:contracts --prefix "$FRONTEND_DIR"

run_step "frontend_lint" "$ARTIFACTS_DIR/frontend_lint.log" \
  npm run lint --prefix "$FRONTEND_DIR"

run_step "frontend_build" "$ARTIFACTS_DIR/frontend_build.log" \
  node "$FRONTEND_DIR/scripts/proof_frontend_build.mjs"

run_step "source_registry_status" "$ARTIFACTS_DIR/source_registry_status.log" \
  "$BACKEND_PYTHON" "$REPO_ROOT/scripts/export_source_registry_status.py" --output "$ARTIFACTS_DIR/source_registry_status.json"

# Build release readiness report from recorded statuses.
release_recommendation="alpha-demo"
if grep -Eq "\|(FAIL|TIMEOUT)\|" "$STATUS_FILE"; then
  release_recommendation="blocked"
fi

git_commit="unknown"
if command -v git >/dev/null 2>&1; then
  git_commit="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
fi

{
  echo "# RELEASE_READINESS"
  echo
  echo "- generated_at_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- commit: $git_commit"
  echo "- proof_profile: current"
  echo "- release_recommendation: $release_recommendation"
  echo "- production_ready: false"
  echo
  echo "## Gate Results"
  echo
  while IFS="|" read -r name status log_path; do
    echo "- $name: $status ($log_path)"
  done < "$STATUS_FILE"

  echo
  echo "## Required Checks"
  echo
  for required_step in \
    backend_compile \
    backend_import \
    backend_grouped_tests \
    backend_justice_laws \
    backend_source_registry \
    backend_boundary \
    frontend_typecheck \
    frontend_contracts \
    frontend_lint \
    frontend_build; do
    if grep -q "^${required_step}|PASS|" "$STATUS_FILE"; then
      echo "- ${required_step}: PASS"
    elif grep -q "^${required_step}|TIMEOUT|" "$STATUS_FILE"; then
      echo "- ${required_step}: TIMEOUT"
    else
      echo "- ${required_step}: FAIL"
    fi
  done
  echo
  echo "## Known Disabled Features"
  echo
  echo "- Source ingestion remains disabled by default unless explicitly enabled by admin controls."
  echo "- Non-machine source classes (portal_reference, disabled_stub) are not runnable."
  echo "- Public publication remains review-gated and evidence-gated."
  echo
  echo "## Known Failures"
  echo
  if grep -Eq "\|(FAIL|TIMEOUT)\|" "$STATUS_FILE"; then
    while IFS="|" read -r name status log_path; do
      if [[ "$status" == "FAIL" || "$status" == "TIMEOUT" ]]; then
        echo "- $name (see $log_path)"
      fi
    done < "$STATUS_FILE"
  else
    echo "- none"
  fi

  echo
  echo "## Remaining Blockers"
  echo
  if grep -Eq "\|(FAIL|TIMEOUT)\|" "$STATUS_FILE"; then
    while IFS="|" read -r name status log_path; do
      if [[ "$status" == "FAIL" || "$status" == "TIMEOUT" ]]; then
        echo "- $name ($status): $log_path"
      fi
    done < "$STATUS_FILE"
  else
    echo "- none"
  fi
} > "$ARTIFACTS_DIR/release_readiness.md"

rm -f "$STATUS_FILE"

echo "[proof_all_current] wrote $ARTIFACTS_DIR/release_readiness.md"
if [[ "$release_recommendation" == "blocked" ]]; then
  exit 1
fi
