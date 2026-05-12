#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT INT TERM

ARCHIVE_PATH="/tmp/JUDGE_ATLAS-main-final.zip"
PACKAGE_ROOT_NAME="JUDGE-main"
SKIP_RELEASE_GATE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --archive-path)
      ARCHIVE_PATH="$2"
      shift 2
      ;;
    --package-root-name)
      PACKAGE_ROOT_NAME="$2"
      shift 2
      ;;
    --skip-release-gate)
      SKIP_RELEASE_GATE=true
      shift
      ;;
    *)
      echo "ERROR: unknown argument: $1"
      exit 2
      ;;
  esac
done

log() {
  echo "[release_package] $*"
}

cd "${ROOT_DIR}"

if [[ "${SKIP_RELEASE_GATE}" != "true" ]]; then
  log "Running release proof gate"
  make release-proof-local
fi

log "Validating local proof freshness"
python scripts/check_proof_freshness.py
python scripts/check_proof_freshness.py --strict-extra-files

PACKAGE_ROOT="${TMP_DIR}/${PACKAGE_ROOT_NAME}"
mkdir -p "${PACKAGE_ROOT}"

log "Building archive at ${ARCHIVE_PATH}"
rsync -a --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.venv' \
  --exclude 'JUDGE-main' \
  --exclude 'backend/.venv' \
  --exclude 'frontend/node_modules' \
  --exclude 'node_modules' \
  ./ "${PACKAGE_ROOT}/"

mkdir -p "$(dirname "${ARCHIVE_PATH}")"
rm -f "${ARCHIVE_PATH}"
(cd "${TMP_DIR}" && zip -qr "${ARCHIVE_PATH}" "${PACKAGE_ROOT_NAME}")

archive_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
    return
  fi
  shasum -a 256 "$1" | awk '{print $1}'
}

ARCHIVE_BASENAME="$(basename "${ARCHIVE_PATH}")"
ARCHIVE_SHA256="$(archive_sha256 "${ARCHIVE_PATH}")"
log "Built archive filename=${ARCHIVE_BASENAME} sha256=${ARCHIVE_SHA256}"

log "Running archive validation"
bash scripts/validate_archive_proof.sh "${ARCHIVE_PATH}"

EXTRACT_DIR="${TMP_DIR}/extracted"
mkdir -p "${EXTRACT_DIR}"
unzip -q "${ARCHIVE_PATH}" -d "${EXTRACT_DIR}"

EXTRACTED_ROOT="$(python scripts/archive_validation_paths.py --extract-dir "${EXTRACT_DIR}")"
log "Resolved extracted root: ${EXTRACTED_ROOT}"

PYTHON_BIN="${EXTRACTED_ROOT}/backend/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

(
  cd "${EXTRACTED_ROOT}"
  "${PYTHON_BIN}" scripts/check_false_claims.py
  "${PYTHON_BIN}" scripts/check_truth_claims.py
  "${PYTHON_BIN}" scripts/check_proof_freshness.py
  "${PYTHON_BIN}" scripts/check_proof_freshness.py --strict-extra-files
  bash scripts/check_no_pyc.sh
  "${PYTHON_BIN}" scripts/check_external_boundaries.py
  "${PYTHON_BIN}" backend/scripts/check_repo_boundaries.py
  "${PYTHON_BIN}" backend/scripts/check_no_direct_ingestion_network_clients.py
  "${PYTHON_BIN}" scripts/validate_workflows.py
)

log "Verifying proof hash synchronization"
python - <<'PY'
import json
import re
from pathlib import Path

root = Path('.')
rg = json.loads((root / 'artifacts/proof/current/release_gate.json').read_text(encoding='utf-8'))
cp = (root / 'artifacts/proof/current/CURRENT_PROOF.md').read_text(encoding='utf-8')
pf = (root / 'artifacts/proof/current/proof_freshness.log').read_text(encoding='utf-8')
av = (root / 'artifacts/proof/current/archive_validation.log').read_text(encoding='utf-8')

release_hash = rg.get('proof_input_tree_hash', '')
cp_match = re.search(r"- proof_input_tree_hash: ([0-9a-f]{64})", cp)
pf_match = re.search(r"proof_input_tree_hash=([0-9a-f]{64})", pf)
av_release_match = re.search(r"release_gate\.json proof_input_tree_hash=([0-9a-f]{64})", av)
av_actual_match = re.search(r"proof_freshness actual_hash=([0-9a-f]{64})", av)

values = {
    'release_gate.json': release_hash,
    'CURRENT_PROOF.md': cp_match.group(1) if cp_match else '',
    'proof_freshness.log': pf_match.group(1) if pf_match else '',
    'archive_validation.log release_hash': av_release_match.group(1) if av_release_match else '',
    'archive_validation.log actual_hash': av_actual_match.group(1) if av_actual_match else '',
}

missing = [name for name, value in values.items() if not value]
if missing:
    raise SystemExit('Missing hash values in: ' + ', '.join(missing))

unique = set(values.values())
if len(unique) != 1:
    lines = ['Hash mismatch across proof artifacts:']
    for name, value in values.items():
        lines.append(f'  {name}: {value}')
    raise SystemExit('\n'.join(lines))

print(f"PASS: synchronized proof_input_tree_hash={release_hash}")
PY

log "PASS: release package and proof validation complete"
