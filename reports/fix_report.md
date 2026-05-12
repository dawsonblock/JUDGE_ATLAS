# Proof Honesty Repair Report

**Generated**: 2026-05-13  
**Scope**: JUDGE_ATLAS / JUDGE-main

---

## Problem Statement

The repository was in a contradictory state:

| Artifact | Previous Value | Correct Value |
|---|---|---|
| `STATUS.md` — Alpha proof status | PASS | **BLOCKED** |
| `alpha_gate_summary.json` — alpha_gate_pass | `true` | **`false`** |
| `alpha_gate_summary.json` — frontend_tests_passed | `"not_run"` | `"not_run"` (unchanged, but now forces BLOCKED) |
| `release_gate.json` — alpha_gate_passed | `false` | `false` (was always correct, ignored by wrapper) |

The root cause: `scripts/run_alpha_proof_gate.py` was run with `--skip-frontend-if-missing-deps`, which silently excluded all six frontend gate checks from the blocking set, allowing `alpha_gate_pass: true` even though zero frontend tests ran. `STATUS.md` was then set to PASS based on this false summary.

---

## Changes Made

### 1. `scripts/run_alpha_proof_gate.py`
- Added `frontend_actually_passed: bool = frontend_tests_passed is True`
- `alpha_gate_pass` now requires `frontend_actually_passed` — `"not_run"` no longer counts as PASS
- Added `alpha_gate_status` field: `"PASS"` | `"BLOCKED"` | `"FAIL"`
- Old permissive value retained as `alpha_gate_pass_DEPRECATED_all` for reference

### 2. `scripts/verify_status_consistency.py`
- **Removed** hard-coded requirement that `STATUS.md` contains `"Alpha proof status: PASS"` — this was enforcing the wrong state
- **Added** validation against `artifacts/proof/current/release_gate.json`:
  - If `alpha_gate_passed: false` but STATUS.md says PASS → error
- **Added** validation of `alpha_gate_summary.json`:
  - If `alpha_gate_pass: true` and `frontend_tests_passed: "not_run"` → error
- **Added** error if `release_gate.json` is missing entirely
- `import json` added

### 3. `STATUS.md`
- `Alpha proof status: PASS` → `Alpha proof status: BLOCKED`
- `Alpha readiness status: PASS` → `Alpha readiness status: BLOCKED`
- Added blocker: "Node 24.x detected; frontend release gate requires Node 20.x"

### 4. `.nvmrc`
- Created with content `20` — pins the repo to Node 20.x for nvm users

### 5. `scripts/check_frontend_node_gate.py`
- Error message updated to:  
  `"Frontend release gate requires Node {N}.x. Current Node: {v}. Use nvm use {N}."`

### 6. `scripts/run_frontend_gate.sh`
- New structured frontend gate shell script
- Runs all six frontend gates, writes `artifacts/proof/current/frontend_gate.json`
- Exits 0 only on complete PASS; exits 1 with BLOCKED summary otherwise

### 7. `scripts/run_release_gate.py`
- New thin alias delegating to `scripts/release_gate.py`
- Satisfies references in docs/CI that expect `run_release_gate.py`

### 8. `backend/app/tests/test_status_consistency.py`
- Added `import json`
- Updated `_seed_valid_repo` to include `release_gate.json` with `alpha_gate_passed: True`
- Added 5 new tests:
  1. `test_missing_release_gate_json_is_an_error`
  2. `test_status_pass_contradicts_release_gate_false_is_an_error`
  3. `test_status_blocked_with_release_gate_false_is_clean`
  4. `test_gate_summary_pass_with_frontend_not_run_is_an_error`
  5. `test_gate_summary_pass_with_frontend_true_is_clean`

### 9. `artifacts/proof/current/alpha_gate_summary.json`
- `alpha_gate_pass`: `true` → **`false`**
- `alpha_gate_status`: new field → `"BLOCKED"`
- `_note`: added explanation
- `release_gate_effective_passed`: `true` → `false`
- `release_gate_blocking_checks`: `[]` → six frontend check names

### 10. `.github/workflows/` — stale workflow removal
Removed:
- `rust.yml` — Rust project; unrelated to this repository
- `webpack.yml` — Webpack bundler; this project uses Next.js (no webpack config)
- `octopusdeploy.yml` — Octopus Deploy; not used here
- `nextjs.yml` — GitHub Pages deployment; not used here

---

## Node Version Situation

Current installed Node: **v24.15.0**  
Required by `frontend/package.json engines.node`: **20.x**  
`frontend/.npmrc`: `engine-strict=true` (install will fail without matching version)

To unblock frontend gates:
```bash
nvm install 20
nvm use 20
node --version   # should print v20.x.x
bash scripts/run_frontend_gate.sh
```

---

## Canonical Truth Chain (post-repair)

```
release_gate.json (alpha_gate_passed: false)
       ↓  validates
alpha_gate_summary.json (alpha_gate_pass: false, alpha_gate_status: BLOCKED)
       ↓  reflected in
STATUS.md (Alpha proof status: BLOCKED)
       ↓  validated by
verify_status_consistency.py (no contradiction errors)
```

---

## Acceptance Criteria

- [x] `alpha_gate_summary.json` never reports `alpha_gate_pass: true` when `frontend_tests_passed != true`
- [x] `STATUS.md` reports BLOCKED when `release_gate.json.alpha_gate_passed == false`
- [x] `verify_status_consistency.py` catches the PASS/BLOCKED contradiction
- [x] `.nvmrc` pins Node 20
- [x] Stale CI workflows removed
- [x] Five new proof-honesty tests added
