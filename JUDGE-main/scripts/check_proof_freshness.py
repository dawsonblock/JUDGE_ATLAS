#!/usr/bin/env python3
"""Verify proof freshness using a deterministic proof-input manifest.

Default validation reads the stored manifest from
``artifacts/proof/current/release_gate.json`` and verifies:
1) listed files are present,
2) listed-file hash matches stored hash,
3) newly discovered proof-relevant files are reported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PROOF_INPUT_PATTERNS = [
    "README.md",
    "Makefile",
    ".github/workflows/**/*",
    "backend/app/**/*",
    "backend/alembic/**/*",
    "backend/pyproject.toml",
    "backend/alembic.ini",
    "backend/requirements*.txt",
    "demo/**/*",
    "frontend/**/*",
    "frontend/package.json",
    "frontend/package-lock.json",
    "package.json",
    "package-lock.json",
    "scripts/**/*",
    "docs/CURRENT_STATUS.md",
    "docs/DB_PROOF.md",
    "docs/FRONTEND_SECURITY_TRIAGE.md",
    "docs/schema_audit.md",
    "docs/LEGACY_AUTH_REMOVAL_PLAN.md",
    "docs/DEPENDENCY_REMEDIATION_PLAN.md",
    "docs/REPAIR_PROOF.md",
    "docs/REPAIR_BASELINE.md",
    "docs/SECURITY.md",
    "docs/PROOF.md",
    "docs/SOURCES.md",
    "docs/AI_PIPELINE.md",
    "artifacts/proof/CURRENT_PROOF.md",
]

IGNORE_PATH_PREFIXES = {
    ".git/",
    ".venv/",
    "backend/.venv/",
    "frontend/node_modules/",
    "node_modules/",
    "artifacts/proof/current/",
    "artifacts/proof/history/",
}

IGNORE_GLOB_PATTERNS = {
    "artifacts/proof/v*/**",
    "artifacts/proof/**/*.log",
    "**/dist/**",
    "**/build/**",
    "**/*.tsbuildinfo",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.log",
    "**/*.tmp",
    "**/*.pid",
    # Database and SQLite volatile files
    "**/*.db",
    "**/*.db-shm",
    "**/*.db-wal",
    "**/*.sqlite",
    "**/*.sqlite3",
    "**/*.sqlite-shm",
    "**/*.sqlite-wal",
    "demo/**/*.db",
    "demo/**/*.sqlite",
    "demo/**/*.sqlite3",
    "demo/demo.sqlite3",
    "backend/app/tests/*.db",
    "backend/app/tests/*.sqlite",
    "backend/app/tests/*.sqlite3",
    "**/.DS_Store",
}


def _normalize_rel_path(path: str) -> str:
    return path.replace("\\", "/")


def _is_ignored(rel_path: str) -> bool:
    norm = _normalize_rel_path(rel_path)
    if any(norm.startswith(prefix) for prefix in IGNORE_PATH_PREFIXES):
        return True
    if "/.next/" in f"/{norm}" or norm.startswith(".next/"):
        return True
    if norm.startswith("artifacts/proof/v"):
        return True
    path_obj = Path(norm)
    if any(path_obj.match(pattern) for pattern in IGNORE_GLOB_PATTERNS):
        return True
    return False


def discover_proof_input_files(repo_root: Path) -> list[str]:
    files: set[str] = set()
    for pattern in PROOF_INPUT_PATTERNS:
        for candidate in repo_root.glob(pattern):
            if not candidate.is_file():
                continue
            rel = _normalize_rel_path(str(candidate.relative_to(repo_root)))
            if _is_ignored(rel):
                continue
            files.add(rel)
    return sorted(files)


def _hash_files(repo_root: Path, rel_files: list[str]) -> tuple[str, list[str]]:
    hasher = hashlib.sha256()
    missing: list[str] = []
    for rel in rel_files:
        file_path = repo_root / rel
        if not file_path.is_file():
            missing.append(rel)
            continue
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\n")
        hasher.update(str(file_path.stat().st_size).encode("utf-8"))
        hasher.update(b"\n")
        with file_path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
        hasher.update(b"\n")
    return hasher.hexdigest(), missing


def compute_proof_input_tree_hash(repo_root: Path) -> tuple[str, list[str]]:
    rel_files = discover_proof_input_files(repo_root)
    digest, _missing = _hash_files(repo_root, rel_files)
    return digest, rel_files


def _release_gate_path(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "proof" / "current" / "release_gate.json"


def _current_proof_path(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "proof" / "current" / "CURRENT_PROOF.md"


def _release_gate_payload(repo_root: Path) -> dict:
    release_gate_path = _release_gate_path(repo_root)
    if not release_gate_path.exists():
        raise FileNotFoundError(str(release_gate_path.relative_to(repo_root)))
    return json.loads(release_gate_path.read_text(encoding="utf-8"))


def validate_stored_manifest(
    repo_root: Path,
    strict_extra_files: bool = False,
) -> dict:
    payload = _release_gate_payload(repo_root)
    expected_hash = payload.get("proof_input_tree_hash")
    algorithm = payload.get("proof_input_tree_hash_algorithm")
    if "proof_input_file_list" not in payload:
        return {
            "status": "FAIL",
            "expected_hash": expected_hash,
            "actual_hash": None,
            "proof_input_tree_hash_algorithm": algorithm,
            "file_count": 0,
            "missing_files": [],
            "extra_files": [],
            "stored_file_count": 0,
            "discovered_file_count": len(discover_proof_input_files(repo_root)),
            "stored_file_list": [],
            "discovered_file_list": discover_proof_input_files(repo_root),
            "message": "release_gate.json missing/invalid proof_input_file_list",
        }

    stored_file_list = payload.get("proof_input_file_list")
    discovered_file_list = discover_proof_input_files(repo_root)
    extra_files = sorted(set(discovered_file_list) - set(stored_file_list))

    result = {
        "status": "PASS",
        "expected_hash": expected_hash,
        "actual_hash": None,
        "proof_input_tree_hash_algorithm": algorithm,
        "file_count": len(stored_file_list),
        "missing_files": [],
        "extra_files": extra_files,
        "stored_file_count": len(stored_file_list),
        "discovered_file_count": len(discovered_file_list),
        "stored_file_list": stored_file_list,
        "discovered_file_list": discovered_file_list,
        "message": "proof artifacts are fresh",
    }

    if not expected_hash:
        result["status"] = "FAIL"
        result["message"] = "release_gate.json missing proof_input_tree_hash"
        return result

    if algorithm != "sha256":
        result["status"] = "FAIL"
        result["message"] = (
            "release_gate.json missing/invalid proof_input_tree_hash_algorithm"
        )
        return result

    if not isinstance(stored_file_list, list) or not all(
        isinstance(path, str) for path in stored_file_list
    ):
        result["status"] = "FAIL"
        result["message"] = "release_gate.json missing/invalid proof_input_file_list"
        return result

    actual_hash, missing_files = _hash_files(repo_root, sorted(stored_file_list))
    result["actual_hash"] = actual_hash
    result["missing_files"] = missing_files

    if missing_files:
        result["status"] = "FAIL"
        result["message"] = (
            "missing listed proof input files: "
            + ", ".join(missing_files)
        )
        return result

    if actual_hash != expected_hash:
        result["status"] = "FAIL"
        result["message"] = (
            "proof input tree hash mismatch: "
            f"expected={expected_hash} actual={actual_hash}"
        )
        return result

    if extra_files and strict_extra_files:
        result["status"] = "FAIL"
        result["message"] = (
            "new proof-relevant files outside stored list: "
            + ", ".join(extra_files)
        )
        return result

    if extra_files:
        result["message"] = (
            "proof artifacts are fresh, but new proof-relevant files were discovered"
        )

    return result


def check_against_expected(repo_root: Path, expected_hash: str) -> dict:
    actual_hash, rel_files = compute_proof_input_tree_hash(repo_root)
    result = {
        "status": "PASS",
        "expected_hash": expected_hash,
        "actual_hash": actual_hash,
        "proof_input_tree_hash_algorithm": "sha256",
        "file_count": len(rel_files),
        "missing_files": [],
        "extra_files": [],
        "stored_file_count": len(rel_files),
        "discovered_file_count": len(rel_files),
        "stored_file_list": rel_files,
        "discovered_file_list": rel_files,
        "message": "proof input tree hash matches expected value",
    }
    if actual_hash != expected_hash:
        result["status"] = "FAIL"
        result["message"] = (
            f"proof input tree hash mismatch: expected={expected_hash} actual={actual_hash}"
        )
    return result


def metadata_payload(repo_root: Path) -> dict:
    digest, rel_files = compute_proof_input_tree_hash(repo_root)
    return {
        "status": "OK",
        "proof_input_tree_hash": digest,
        "proof_input_tree_hash_algorithm": "sha256",
        "proof_input_paths": PROOF_INPUT_PATTERNS,
        "proof_input_file_count": len(rel_files),
        "proof_input_file_list": rel_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument(
        "--expected-hash",
        help="If provided, compare the computed proof-input hash against this value",
    )
    parser.add_argument(
        "--strict-extra-files",
        action="store_true",
        help="Fail if newly discovered proof-relevant files are outside the stored list",
    )
    parser.add_argument(
        "--print-inputs",
        action="store_true",
        help="Print discovered and stored proof-input file lists",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable validation output",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Emit deterministic proof-input metadata without reading release_gate.json",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    if not repo_root.is_dir():
        print(f"ERROR: root is not a directory: {repo_root}")
        return 2

    if args.metadata_only:
        print(json.dumps(metadata_payload(repo_root), indent=2))
        return 0

    if args.expected_hash:
        result = check_against_expected(repo_root, args.expected_hash)
    else:
        try:
            result = validate_stored_manifest(
                repo_root,
                strict_extra_files=args.strict_extra_files,
            )
        except FileNotFoundError as exc:
            result = {
                "status": "FAIL",
                "expected_hash": None,
                "actual_hash": None,
                "proof_input_tree_hash_algorithm": "sha256",
                "file_count": 0,
                "missing_files": [str(exc)],
                "extra_files": [],
                "stored_file_count": 0,
                "discovered_file_count": len(discover_proof_input_files(repo_root)),
                "stored_file_list": [],
                "discovered_file_list": discover_proof_input_files(repo_root),
                "message": f"missing {exc}",
            }

    if args.print_inputs:
        print("=== discovered proof inputs ===")
        for rel in result["discovered_file_list"]:
            print(rel)
        print("=== stored proof inputs ===")
        for rel in result["stored_file_list"]:
            print(rel)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "PASS" else 1

    if result["status"] == "PASS":
        print(f"PASS: {result['message']}")
        print(f"proof_input_tree_hash={result['actual_hash']}")
        if result["extra_files"] and not args.strict_extra_files:
            print(
                "WARN: discovered proof-relevant files outside stored list: "
                + ", ".join(result["extra_files"])
            )
        return 0

    print(f"FAIL: {result['message']}")
    if result["actual_hash"]:
        print(f"proof_input_tree_hash={result['actual_hash']}")
    if result["extra_files"]:
        print("extra_discovered_files=" + ",".join(result["extra_files"]))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
