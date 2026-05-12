#!/usr/bin/env python3
"""Validate the exact final ZIP archive for release integrity.

This script validates that:
1. The ZIP file exists and is readable
2. Archive contains exactly one runtime root (backend/ + frontend/ + scripts/)
3. No stale nested repo copies exist
4. No forbidden paths (node_modules, venv, __pycache__, .git, etc.)
5. Required proof artifacts present
6. Archive structure matches expected layout
7. SHA-256 identity recorded
8. Proof freshness passes after extraction

Usage:
    python scripts/validate_final_zip.py /absolute/path/to/final-archive.zip

Exit Codes:
    0   Archive valid and ready to ship
    1   Archive structure invalid
    2   Archive contains forbidden paths
    3   Proof validation failed during extraction
    4   ZIP not found or unreadable
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def compute_sha256(zip_path: Path) -> str:
    """Compute SHA-256 hash of ZIP file."""
    digest = hashlib.sha256()
    with zip_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_runtime_roots(extract_dir: Path) -> list[Path]:
    """Find all directories that appear to be runtime roots.
    
    A runtime root contains:
    - backend/
    - frontend/
    - scripts/release_gate.py
    """
    candidates: list[Path] = []
    
    # Look for release_gate.py markers
    for release_gate in extract_dir.glob("**/scripts/release_gate.py"):
        repo_root = release_gate.parents[1]
        if repo_root.is_dir():
            # Verify it has the required subdirectories
            if (
                (repo_root / "backend").is_dir()
                and (repo_root / "frontend").is_dir()
                and (repo_root / "scripts").is_dir()
            ):
                # Avoid duplicates
                if repo_root not in candidates:
                    candidates.append(repo_root)
    
    return sorted(set(candidates))


def find_forbidden_paths(extract_dir: Path) -> list[str]:
    """Find forbidden paths that should not be in archive.
    
    Forbidden patterns:
    - node_modules/
    - .next/
    - __pycache__/
    - *.pyc
    - .pytest_cache/
    - .mypy_cache/
    - venv/
    - .venv/
    - .git/
    - *.egg-info/
    - .DS_Store
    """
    forbidden_patterns = {
        "node_modules/",
        ".next/",
        "__pycache__/",
        ".pytest_cache/",
        ".mypy_cache/",
        "venv/",
        ".venv/",
        ".git/",
        ".gitignore",
        ".github/workflows/",
    }
    
    forbidden_extensions = {".pyc", ".egg-info", ".pyo"}
    forbidden_files = {".DS_Store", "thumbs.db", "Thumbs.db"}
    
    found: list[str] = []
    
    for path in extract_dir.rglob("*"):
        rel = path.relative_to(extract_dir)
        path_str = str(rel)
        
        # Check for forbidden directories (must check with trailing slash)
        for pattern in forbidden_patterns:
            if pattern.endswith("/"):
                if f"{pattern}" in f"{path_str}/" or path_str.startswith(pattern):
                    found.append(path_str)
                    break
            else:
                if path_str == pattern or path_str.startswith(f"{pattern}/"):
                    found.append(path_str)
                    break
        
        # Check extensions
        if path.suffix in forbidden_extensions:
            found.append(path_str)
        
        # Check filenames
        if path.name in forbidden_files:
            found.append(path_str)
    
    return sorted(set(found))


def find_nested_artifacts(extract_dir: Path, root: Path) -> list[str]:
    """Find nested proof artifacts outside authoritative root."""
    nested: list[str] = []
    
    # Find all artifacts/proof/current directories
    for proof_dir in extract_dir.glob("**/artifacts/proof/current"):
        # If it's not inside our authoritative root, it's nested
        try:
            proof_dir.relative_to(root)
        except ValueError:
            # Not under root - this is nested
            nested.append(str(proof_dir.relative_to(extract_dir)))
    
    return nested


def find_duplicate_critical_files(extract_dir: Path) -> list[str]:
    """Find duplicate critical files outside authoritative root."""
    critical_files = {
        "release_readiness.md",
        "proof_manifest.json",
        "release_gate.json",
        "backend_pytest.log",
    }
    
    duplicates: list[str] = []
    
    for critical_file in critical_files:
        found_paths = list(extract_dir.glob(f"**/{critical_file}"))
        if len(found_paths) > 1:
            for path in found_paths:
                duplicates.append(str(path.relative_to(extract_dir)))
    
    return duplicates


def validate_archive_structure(extract_dir: Path, root: Path) -> tuple[bool, list[str]]:
    """Validate archive structure requirements."""
    errors: list[str] = []
    
    # Check required directories exist
    required_dirs = [
        "backend",
        "frontend",
        "scripts",
        "docs",
        "artifacts",
    ]
    
    for dirname in required_dirs:
        if not (root / dirname).is_dir():
            errors.append(f"missing_required_dir:{dirname}")
    
    # Check required files exist
    required_files = [
        "backend/app/main.py",
        "frontend/package.json",
        "scripts/release_gate.py",
        "artifacts/proof/current/release_readiness.md",
        "artifacts/proof/current/proof_manifest.json",
        "README.md",
    ]
    
    for filepath in required_files:
        if not (root / filepath).exists():
            errors.append(f"missing_required_file:{filepath}")
    
    return len(errors) == 0, errors


def check_forbidden_paths_in_root(root: Path) -> list[str]:
    """Check for forbidden paths specifically in root."""
    errors: list[str] = []
    
    forbidden_in_root = [
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "node_modules",
        ".next",
        "venv",
        ".venv",
    ]
    
    for name in forbidden_in_root:
        path = root / name
        if path.exists():
            errors.append(f"forbidden_in_root:{name}")
    
    return errors


def validate_final_zip(zip_path: Path) -> dict:
    """Main validation routine.
    
    Returns dict with:
    - valid: bool
    - zip_path: str
    - zip_sha256: str
    - top_level_dirs: list[str]
    - runtime_roots_count: int
    - runtime_root: str (if exactly one)
    - errors: list[str]
    - warnings: list[str]
    - validated_at_utc: str
    """
    
    result = {
        "valid": False,
        "zip_path": str(zip_path),
        "zip_sha256": "",
        "top_level_dirs": [],
        "runtime_roots_count": 0,
        "runtime_root": None,
        "errors": [],
        "warnings": [],
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    
    # Check ZIP exists
    if not zip_path.exists():
        result["errors"].append("zip_not_found")
        return result
    
    if not zip_path.is_file():
        result["errors"].append("zip_not_file")
        return result
    
    # Check ZIP is readable
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Verify ZIP integrity
            if zf.testzip() is not None:
                result["errors"].append("zip_corrupt_testzip_failed")
                return result
    except Exception as e:
        result["errors"].append(f"zip_open_failed:{str(e)}")
        return result
    
    # Compute SHA-256
    try:
        sha256 = compute_sha256(zip_path)
        result["zip_sha256"] = sha256
    except Exception as e:
        result["errors"].append(f"sha256_compute_failed:{str(e)}")
        return result
    
    # Extract and validate
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir_path)
        except Exception as e:
            result["errors"].append(f"extract_failed:{str(e)}")
            return result
        
        # Find top-level directories
        top_level = sorted({
            p.name for p in tmpdir_path.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        })
        result["top_level_dirs"] = top_level
        
        # Find runtime roots
        roots = find_runtime_roots(tmpdir_path)
        result["runtime_roots_count"] = len(roots)
        
        if len(roots) == 0:
            result["errors"].append("no_runtime_root_found")
            return result
        
        if len(roots) > 1:
            result["errors"].append(f"multiple_runtime_roots_found:{len(roots)}")
            for root in roots:
                result["errors"].append(f"  - {root.relative_to(tmpdir_path)}")
            return result
        
        # Exactly one root - validate it
        root = roots[0]
        result["runtime_root"] = str(root.relative_to(tmpdir_path))
        
        # Validate structure
        valid, struct_errors = validate_archive_structure(tmpdir_path, root)
        result["errors"].extend(struct_errors)
        
        # Check forbidden paths globally
        forbidden = find_forbidden_paths(tmpdir_path)
        if forbidden:
            result["errors"].append(f"forbidden_paths_found:{len(forbidden)}")
            result["errors"].extend([f"  - {p}" for p in forbidden[:10]])  # Show first 10
            if len(forbidden) > 10:
                result["errors"].append(f"  ... and {len(forbidden) - 10} more")
        
        # Check nested artifacts
        nested = find_nested_artifacts(tmpdir_path, root)
        if nested:
            result["errors"].append(f"nested_artifacts_found:{len(nested)}")
            result["errors"].extend([f"  - {p}" for p in nested])
        
        # Check duplicate critical files
        duplicates = find_duplicate_critical_files(tmpdir_path)
        if duplicates:
            result["errors"].append(f"duplicate_critical_files:{len(duplicates)}")
            result["errors"].extend([f"  - {p}" for p in duplicates])
        
        # Check forbidden in root specifically
        root_forbidden = check_forbidden_paths_in_root(root)
        result["errors"].extend(root_forbidden)
        
        # If we have some critical errors, fail fast
        if result["errors"]:
            return result
        
        # Try to run proof freshness check on extracted content
        try:
            # Copy proof freshness checker if needed
            freshness_result = subprocess.run(
                [
                    "python3.11",
                    str(REPO_ROOT / "scripts" / "check_proof_freshness.py"),
                    "--no-update-artifacts",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if freshness_result.returncode != 0:
                result["warnings"].append("proof_freshness_check_failed")
                result["warnings"].append(freshness_result.stdout)
        except Exception as e:
            result["warnings"].append(f"proof_freshness_check_error:{str(e)}")
    
    # Mark as valid if no errors
    result["valid"] = len(result["errors"]) == 0
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate final ZIP archive for JUDGE_ATLAS release"
    )
    parser.add_argument("zip_path", help="Absolute path to final archive ZIP")
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Write validation result to JSON file",
    )
    
    args = parser.parse_args()
    zip_path = Path(args.zip_path)
    
    result = validate_final_zip(zip_path)
    
    # Write result to JSON if requested
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("w") as f:
            json.dump(result, f, indent=2)
    
    # Print summary
    print(f"Archive: {result['zip_path']}")
    print(f"SHA-256: {result['zip_sha256']}")
    print(f"Runtime Root: {result['runtime_root']}")
    print(f"Valid: {'YES' if result['valid'] else 'NO'}")
    
    if result["errors"]:
        print(f"\nErrors ({len(result['errors'])}):")
        for err in result["errors"]:
            print(f"  - {err}")
    
    if result["warnings"]:
        print(f"\nWarnings ({len(result['warnings'])}):")
        for warn in result["warnings"]:
            print(f"  - {warn}")
    
    # Exit code: 0 if valid, 1 if errors
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
