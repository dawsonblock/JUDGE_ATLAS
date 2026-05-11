#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT="$(dirname "${ROOT_DIR}")"
LOG_PATH="${ROOT_DIR}/artifacts/proof/current/archive_validation.log"

mkdir -p "$(dirname "${LOG_PATH}")"

ARCHIVE_PATH="${1:-}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT INT TERM

if [[ -z "${ARCHIVE_PATH}" ]]; then
  ARCHIVE_PATH="${TMP_DIR}/judge_atlas_archive.zip"
  (
    cd "${WORKSPACE_ROOT}"
    zip -qr "${ARCHIVE_PATH}" "JUDGE-main" \
      -x "JUDGE-main/**/*.pyc" \
      -x "JUDGE-main/**/__pycache__/*" \
      -x "JUDGE-main/backend/.venv/*" \
      -x "JUDGE-main/backend/.venv/**" \
      -x "JUDGE-main/.venv/*" \
      -x "JUDGE-main/.venv/**" \
      -x "JUDGE-main/frontend/node_modules/*" \
      -x "JUDGE-main/frontend/node_modules/**" \
      -x "JUDGE-main/node_modules/*" \
      -x "JUDGE-main/node_modules/**"
  )
fi

EXTRACT_DIR="${TMP_DIR}/extract"
mkdir -p "${EXTRACT_DIR}"
unzip -q "${ARCHIVE_PATH}" -d "${EXTRACT_DIR}"

EXTRACTED_ROOT="${EXTRACT_DIR}/JUDGE-main"
if [[ ! -d "${EXTRACTED_ROOT}" ]]; then
  echo "ERROR: extracted archive missing JUDGE-main directory" | tee "${LOG_PATH}"
  exit 1
fi

PYTHON_BIN="${EXTRACTED_ROOT}/backend/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

{
  echo "[archive_validation] extracted_root=${EXTRACTED_ROOT}"
  echo "[archive_validation] archive_path=${ARCHIVE_PATH}"
  cd "${EXTRACTED_ROOT}"

  "${PYTHON_BIN}" scripts/check_false_claims.py
  "${PYTHON_BIN}" scripts/check_truth_claims.py
  "${PYTHON_BIN}" scripts/check_proof_freshness.py
  bash scripts/check_no_pyc.sh
  "${PYTHON_BIN}" scripts/check_external_boundaries.py
  "${PYTHON_BIN}" backend/scripts/check_repo_boundaries.py
  "${PYTHON_BIN}" backend/scripts/check_no_direct_ingestion_network_clients.py
  "${PYTHON_BIN}" scripts/validate_workflows.py

  echo "[archive_validation] PASS: extracted archive checks completed"
} > "${LOG_PATH}" 2>&1

echo "Archive validation log written: ${LOG_PATH}"
