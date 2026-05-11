#!/usr/bin/env python3
"""Verify current proof artifacts are fresh for tracked proof-input paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROOF_INPUT_PATTERNS = [
    ".github/workflows/**/*",
    "backend/app/**/*",
    "backend/alembic/**/*",
    "backend/pyproject.toml",
    "demo/**/*",
    "frontend/**/*",
    "scripts/**/*",
    "docs/CURRENT_STATUS.md",
    "docs/DB_PROOF.md",
    "docs/LEGACY_AUTH_REMOVAL_PLAN.md",
    "docs/DEPENDENCY_REMEDIATION_PLAN.md",
    "docs/FRONTEND_SECURITY_TRIAGE.md",
    "docs/schema_audit.md",
    "README.md",
    "Makefile",
]

IGNORE_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
}

IGNORE_PATH_PREFIXES = [
    "artifacts/proof/current/",
    "artifacts/proof/history/",
    "artifacts/proof/v",
]

IGNORE_SUFFIXES = {".pyc"}


def _is_ignored(rel_path: str) -> bool:
    norm = rel_path.replace("\\", "/")
    parts = set(Path(norm).parts)
    if parts & IGNORE_DIR_NAMES:
        return True
    if any(norm.startswith(prefix) for prefix in IGNORE_PATH_PREFIXES):
        return True
    if Path(norm).suffix in IGNORE_SUFFIXES:
        return True
    return False


def _git_tracked_files(repo_root: Path) -> list[Path]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-z"],
        capture_output=True,
        text=False,
        check=False,
    )
    if proc.returncode != 0:
        return []

    tracked: list[Path] = []
    for raw in proc.stdout.split(b"\x00"):
        if not raw:
            continue
        rel = raw.decode("utf-8", errors="ignore")
        rel_norm = rel.replace("\\", "/")
        rel_path = PurePosixPath(rel_norm)
        if not any(rel_path.match(pattern) for pattern in PROOF_INPUT_PATTERNS):
            continue
        if _is_ignored(rel_norm):
            continue
        abs_path = repo_root / rel_norm
        if abs_path.is_file():
            tracked.append(abs_path)
    return tracked


def _iter_input_files(repo_root: Path) -> list[Path]:
    tracked_files = _git_tracked_files(repo_root)
    if tracked_files:
        return sorted(
            tracked_files,
            key=lambda p: str(p.relative_to(repo_root)).replace("\\", "/"),
        )

    files: set[Path] = set()
    for pattern in PROOF_INPUT_PATTERNS:
        for candidate in repo_root.glob(pattern):
            if not candidate.is_file():
                continue
            rel = str(candidate.relative_to(repo_root)).replace("\\", "/")
            if _is_ignored(rel):
                continue
            files.add(candidate)
    return sorted(files, key=lambda p: str(p.relative_to(repo_root)).replace("\\", "/"))


def compute_proof_input_tree_hash(repo_root: Path) -> tuple[str, list[str]]:
    hasher = hashlib.sha256()
    files = _iter_input_files(repo_root)
    rel_files: list[str] = []
    for file_path in files:
        rel = str(file_path.relative_to(repo_root)).replace("\\", "/")
        rel_files.append(rel)
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        with file_path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
        hasher.update(b"\0")
    return hasher.hexdigest(), rel_files


def _release_gate_path(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "proof" / "current" / "release_gate.json"


def _current_proof_path(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "proof" / "current" / "CURRENT_PROOF.md"


def check_against_artifacts(repo_root: Path) -> tuple[bool, str]:
    release_gate_path = _release_gate_path(repo_root)
    current_proof_path = _current_proof_path(repo_root)
    if not release_gate_path.exists():
        return False, f"missing {release_gate_path.relative_to(repo_root)}"
    if not current_proof_path.exists():
        return False, f"missing {current_proof_path.relative_to(repo_root)}"

    payload = json.loads(release_gate_path.read_text(encoding="utf-8"))
    expected_hash = payload.get("proof_input_tree_hash")
    algorithm = payload.get("proof_input_tree_hash_algorithm")
    if not expected_hash:
        return False, "release_gate.json missing proof_input_tree_hash"
    if algorithm != "sha256":
        return (
            False,
            "release_gate.json missing/invalid proof_input_tree_hash_algorithm",
        )

    actual_hash, _paths = compute_proof_input_tree_hash(repo_root)
    if actual_hash != expected_hash:
        return (
            False,
            (
                "proof input tree hash mismatch: "
                f"expected={expected_hash} actual={actual_hash}"
            ),
        )

    current_proof_text = current_proof_path.read_text(encoding="utf-8")
    expected_line = f"- proof_input_tree_hash: {actual_hash}"
    if expected_line not in current_proof_text:
        return False, "CURRENT_PROOF.md missing proof_input_tree_hash line"

    return True, "proof artifacts are fresh"


def check_against_expected(repo_root: Path, expected_hash: str) -> tuple[bool, str]:
    actual_hash, _paths = compute_proof_input_tree_hash(repo_root)
    if actual_hash != expected_hash:
        return (
            False,
            f"proof input tree hash mismatch: expected={expected_hash} actual={actual_hash}",
        )
    return True, "proof input tree hash matches expected value"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument(
        "--expected-hash",
        help="If provided, compare the computed proof-input hash against this value",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print proof-input hash metadata as JSON and exit",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    if not repo_root.is_dir():
        print(f"ERROR: root is not a directory: {repo_root}")
        return 2

    current_hash, input_files = compute_proof_input_tree_hash(repo_root)

    if args.print_json:
        payload = {
            "proof_input_tree_hash": current_hash,
            "proof_input_tree_hash_algorithm": "sha256",
            "proof_input_paths": PROOF_INPUT_PATTERNS,
            "proof_input_file_count": len(input_files),
        }
        print(json.dumps(payload, indent=2))
        return 0

    if args.expected_hash:
        ok, message = check_against_expected(repo_root, args.expected_hash)
    else:
        ok, message = check_against_artifacts(repo_root)

    if ok:
        print(f"PASS: {message}")
        print(f"proof_input_tree_hash={current_hash}")
        return 0

    print(f"FAIL: {message}")
    print(f"proof_input_tree_hash={current_hash}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
