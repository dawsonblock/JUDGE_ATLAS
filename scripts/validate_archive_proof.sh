#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT="$(dirname "${ROOT_DIR}")"
LOG_PATH="${ROOT_DIR}/artifacts/proof/current/archive_validation.log"
ARCHIVE_HELPER="${ROOT_DIR}/scripts/archive_validation_paths.py"

mkdir -p "$(dirname "${LOG_PATH}")"
: >"${LOG_PATH}"

log() {
  echo "[archive_validation] $*"
}

run_check() {
  local name="$1"
  shift
  local rc=0
  if "$@"; then
    log "PASS: ${name}"
    return 0
  else
    rc=$?
    log "FAIL: ${name} rc=${rc}"
    return ${rc}
  fi
}

require_file() {
  local file_path="$1"
  if [[ -f "$file_path" ]]; then
    return 0
  fi
  echo "Missing required file: $file_path"
  return 1
}

forbid_path() {
  local path="$1"
  if [[ -e "$path" ]]; then
    echo "Forbidden packaged path present: $path"
    return 1
  fi
  return 0
}

ARCHIVE_PATH="${1:-}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT INT TERM

archive_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
    return
  fi
  shasum -a 256 "$1" | awk '{print $1}'
}

if [[ -z "${ARCHIVE_PATH}" ]]; then
  ARCHIVE_PATH="${TMP_DIR}/judge_atlas_archive.zip"
  STAGE_DIR="${TMP_DIR}/stage"
  PACKAGE_ROOT="${STAGE_DIR}/JUDGE-main"
  mkdir -p "${PACKAGE_ROOT}"
  rsync -a --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.venv' \
    --exclude 'JUDGE-main' \
    --exclude 'backend/.venv' \
    --exclude 'frontend/node_modules' \
    --exclude 'node_modules' \
    "${ROOT_DIR}/" "${PACKAGE_ROOT}/"
  (
    cd "${STAGE_DIR}"
    zip -qr "${ARCHIVE_PATH}" "JUDGE-main"
  )
fi

EXTRACT_DIR="${TMP_DIR}/extract"
mkdir -p "${EXTRACT_DIR}"
unzip -q "${ARCHIVE_PATH}" -d "${EXTRACT_DIR}"

HELPER_PYTHON_BIN="${ROOT_DIR}/backend/.venv/bin/python"
if [[ ! -x "${HELPER_PYTHON_BIN}" ]]; then
  HELPER_PYTHON_BIN="python3"
fi

if ! JUDGE_MAIN_ROOT="$(${HELPER_PYTHON_BIN} "${ARCHIVE_HELPER}" --extract-dir "${EXTRACT_DIR}")"; then
  log "ERROR: failed to resolve JUDGE-main directory"
  exit 1
fi

if [[ ! -d "${JUDGE_MAIN_ROOT}" ]]; then
  log "ERROR: extracted archive missing JUDGE-main directory"
  exit 1
fi

PYTHON_BIN="${JUDGE_MAIN_ROOT}/backend/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

exec > >(tee -a "${LOG_PATH}") 2>&1

ARCHIVE_BASENAME="$(basename "${ARCHIVE_PATH}")"
ARCHIVE_SHA256="$(archive_sha256 "${ARCHIVE_PATH}")"
TOPLEVEL_DIRS="$(cd "${EXTRACT_DIR}" && find . -mindepth 1 -maxdepth 1 -type d | sort | tr '\n' ',' | sed 's/,$//')"

log "INFO: archive=${ARCHIVE_PATH}"
log "INFO: archive_filename=${ARCHIVE_BASENAME}"
log "INFO: archive_sha256=${ARCHIVE_SHA256}"
log "INFO: archive_top_level_dirs=${TOPLEVEL_DIRS}"
log "INFO: extract_dir=${EXTRACT_DIR}"
log "PASS: located JUDGE-main at ${JUDGE_MAIN_ROOT}"

REPO_ROOT_COUNT="$(find "${EXTRACT_DIR}" -type f -path '*/scripts/release_gate.py' | wc -l | tr -d ' ')"
if [[ "${REPO_ROOT_COUNT}" -gt 1 ]]; then
  log "FAIL: multiple repo roots detected (${REPO_ROOT_COUNT})"
  find "${EXTRACT_DIR}" -type f -path '*/scripts/release_gate.py' -print | sed 's/^/[archive_validation] INFO: repo_root_candidate=/'
  exit 1
fi

READINESS_COUNT="$(find "${EXTRACT_DIR}" -type f -path '*/artifacts/proof/current/release_readiness.md' | wc -l | tr -d ' ')"
if [[ "${READINESS_COUNT}" -gt 1 ]]; then
  log "FAIL: multiple release_readiness.md files detected (${READINESS_COUNT})"
  find "${EXTRACT_DIR}" -type f -path '*/artifacts/proof/current/release_readiness.md' -print | sed 's/^/[archive_validation] INFO: readiness_candidate=/'
  exit 1
fi

if ! RELEASE_GATE_HASH="$(${PYTHON_BIN} -c 'import json, sys; from pathlib import Path; payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")); print(payload.get("proof_input_tree_hash", "unknown"))' artifacts/proof/current/release_gate.json)";
then
  log "ERROR: failed to read proof_input_tree_hash from release_gate.json"
  exit 1
fi
log "INFO: release_gate.json proof_input_tree_hash=${RELEASE_GATE_HASH}"

cd "${JUDGE_MAIN_ROOT}"

overall_rc=0
export PYTHONDONTWRITEBYTECODE=1

if ! run_check "check_false_claims" "${PYTHON_BIN}" scripts/check_false_claims.py; then overall_rc=1; fi
if ! run_check "check_truth_claims" "${PYTHON_BIN}" scripts/check_truth_claims.py; then overall_rc=1; fi
if ! run_check "check_proof_freshness" "${PYTHON_BIN}" scripts/check_proof_freshness.py; then overall_rc=1; fi
if ! run_check "check_proof_freshness_strict" "${PYTHON_BIN}" scripts/check_proof_freshness.py --strict-extra-files; then overall_rc=1; fi
if ! run_check "check_no_pyc" bash scripts/check_no_pyc.sh; then overall_rc=1; fi
if ! run_check "check_external_boundaries" "${PYTHON_BIN}" scripts/check_external_boundaries.py; then overall_rc=1; fi
if ! run_check "check_repo_boundaries" "${PYTHON_BIN}" backend/scripts/check_repo_boundaries.py; then overall_rc=1; fi
if ! run_check "check_no_direct_ingestion_network_clients" "${PYTHON_BIN}" backend/scripts/check_no_direct_ingestion_network_clients.py; then overall_rc=1; fi
if ! run_check "validate_workflows" "${PYTHON_BIN}" scripts/validate_workflows.py; then overall_rc=1; fi

if ! run_check "required_proof_manifest" require_file artifacts/proof/current/proof_manifest.json; then overall_rc=1; fi
if ! run_check "required_release_gate" require_file artifacts/proof/current/release_gate.json; then overall_rc=1; fi
if ! run_check "required_release_readiness" require_file artifacts/proof/current/release_readiness.md; then overall_rc=1; fi
if ! run_check "required_current_alpha_status" require_file artifacts/proof/current/CURRENT_ALPHA_STATUS.md; then overall_rc=1; fi
if ! run_check "required_source_registry_status" require_file artifacts/proof/current/SOURCE_REGISTRY_STATUS.md; then overall_rc=1; fi
if ! run_check "required_proof_policy" require_file artifacts/proof/current/PROOF_POLICY.md; then overall_rc=1; fi

if ! run_check "forbid_python_bytecode" bash -lc '! find . -type f -name "*.pyc" | grep -q .'; then overall_rc=1; fi
if ! run_check "forbid_pycache_dirs" bash -lc '! find . -type d -name "__pycache__" | grep -q .'; then overall_rc=1; fi
if ! run_check "forbid_backend_venv" forbid_path backend/.venv; then overall_rc=1; fi
if ! run_check "forbid_repo_venv" forbid_path .venv; then overall_rc=1; fi
if ! run_check "forbid_frontend_node_modules" forbid_path frontend/node_modules; then overall_rc=1; fi
if ! run_check "forbid_repo_node_modules" forbid_path node_modules; then overall_rc=1; fi
if ! run_check "forbid_git_dir" forbid_path .git; then overall_rc=1; fi

PROOF_FRESHNESS_ACTUAL_HASH="$(grep -m1 '^proof_input_tree_hash=' "${LOG_PATH}" | tail -1 | cut -d= -f2-)"
if [[ -n "${PROOF_FRESHNESS_ACTUAL_HASH}" ]]; then
  log "INFO: proof_freshness actual_hash=${PROOF_FRESHNESS_ACTUAL_HASH}"
fi

if [[ -n "${RELEASE_GATE_HASH}" && -n "${PROOF_FRESHNESS_ACTUAL_HASH}" && "${RELEASE_GATE_HASH}" != "${PROOF_FRESHNESS_ACTUAL_HASH}" ]]; then
  log "FAIL: release hash and proof freshness hash differ"
  overall_rc=1
fi

if [[ ${overall_rc} -eq 0 ]]; then
  log "PASS: extracted archive checks completed"
else
  log "FAIL: extracted archive checks completed"
fi

echo "Archive validation log written: ${LOG_PATH}"
exit ${overall_rc}
