#!/usr/bin/env python3
"""Build a clean release archive for distribution."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "dist" / "JUDGE_ATLAS-main.clean.zip"
DEFAULT_ROOT_NAME = "JUDGE_ATLAS-main"

DEFAULT_INCLUDE_TOP_LEVEL = (
    "backend",
    "frontend",
    "docs",
    "scripts",
    "infra",
    "alembic",
    "artifacts/proof/current",
)
DEFAULT_INCLUDE_FILES = (
    "README.md",
    "STATUS.md",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "docker-compose.yml",
    "docker-compose.yaml",
)

EXCLUDED_PREFIXES = (
    "external/",
    "node_modules/",
    "frontend/node_modules/",
    "frontend/.next/",
    ".venv/",
    "backend/.venv/",
    "venv/",
    ".git/",
    "artifacts/proof/archive/",
    "artifacts/proof/history/",
    "artifacts/history/",
    "logs/",
    "tmp/",
    "temp/",
    "data/evidence_store/",
    "evidence_store/",
)
EXCLUDED_SEGMENTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
EXCLUDED_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log",
    ".tmp",
    ".swp",
    ".pem",
    ".key",
)
EXCLUDED_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".DS_Store",
    "Thumbs.db",
    "id_rsa",
    "id_ed25519",
}
TEXT_REDACT_SUFFIXES = {".md", ".json", ".txt", ".yml", ".yaml", ".toml"}
LOCAL_PATH_PATTERNS = (
    re.compile(r"/Users/[^\s\"'`]+"),
    re.compile(r"/home/[^\s\"'`]+"),
    re.compile(r"/private/[^\s\"'`]+"),
    re.compile(r"[A-Za-z]:\\[^\s\"'`]+"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit(repo_root: Path) -> str | None:
    try:
        cp = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return cp.stdout.strip() or None


def _normalize(path: Path) -> str:
    return path.as_posix()


def _is_excluded(rel_path: str, include_external: bool, include_proof_archive: bool) -> bool:
    if not include_external and rel_path.startswith("external/"):
        return True
    if not include_proof_archive and rel_path.startswith("artifacts/proof/archive/"):
        return True
    if any(rel_path.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        if include_external and rel_path.startswith("external/"):
            return False
        if include_proof_archive and rel_path.startswith("artifacts/proof/archive/"):
            return False
        return True

    parts = Path(rel_path).parts
    if any(part in EXCLUDED_SEGMENTS for part in parts):
        return True

    name = Path(rel_path).name
    lower_name = name.lower()
    if lower_name in EXCLUDED_FILE_NAMES:
        return True
    if lower_name.endswith(EXCLUDED_SUFFIXES):
        return True
    return False


def _collect_files(repo_root: Path, include_external: bool, include_proof_archive: bool) -> tuple[list[Path], set[str], set[str]]:
    included: set[Path] = set()
    included_top_level: set[str] = set()
    excluded_top_level: set[str] = set()

    for rel in DEFAULT_INCLUDE_TOP_LEVEL:
        path = repo_root / rel
        if path.is_file():
            included.add(path)
            included_top_level.add(rel.split("/", 1)[0])
        elif path.is_dir():
            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue
                rel_path = _normalize(file_path.relative_to(repo_root))
                if _is_excluded(rel_path, include_external, include_proof_archive):
                    excluded_top_level.add(rel_path.split("/", 1)[0])
                    continue
                included.add(file_path)
                included_top_level.add(rel_path.split("/", 1)[0])

    for rel in DEFAULT_INCLUDE_FILES:
        path = repo_root / rel
        if path.is_file():
            rel_path = _normalize(path.relative_to(repo_root))
            if _is_excluded(rel_path, include_external, include_proof_archive):
                excluded_top_level.add(rel_path.split("/", 1)[0])
                continue
            included.add(path)
            included_top_level.add(rel_path.split("/", 1)[0])

    for compose_file in repo_root.glob("docker-compose*.yml"):
        if compose_file.is_file():
            rel_path = _normalize(compose_file.relative_to(repo_root))
            if _is_excluded(rel_path, include_external, include_proof_archive):
                excluded_top_level.add(rel_path.split("/", 1)[0])
                continue
            included.add(compose_file)
            included_top_level.add(rel_path.split("/", 1)[0])

    for compose_file in repo_root.glob("docker-compose*.yaml"):
        if compose_file.is_file():
            rel_path = _normalize(compose_file.relative_to(repo_root))
            if _is_excluded(rel_path, include_external, include_proof_archive):
                excluded_top_level.add(rel_path.split("/", 1)[0])
                continue
            included.add(compose_file)
            included_top_level.add(rel_path.split("/", 1)[0])

    for candidate in repo_root.iterdir():
        if not candidate.exists():
            continue
        if _is_excluded(candidate.name + ("/" if candidate.is_dir() else ""), include_external, include_proof_archive):
            excluded_top_level.add(candidate.name)

    return sorted(included), included_top_level, excluded_top_level


def _write_archive(output: Path, root_name: str, files: list[Path], manifest: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            rel = _normalize(file_path.relative_to(REPO_ROOT))
            arcname = f"{root_name}/{rel}"
            if file_path.suffix.lower() in TEXT_REDACT_SUFFIXES:
                raw = file_path.read_bytes()
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    zf.write(file_path, arcname)
                    continue
                for pattern in LOCAL_PATH_PATTERNS:
                    text = pattern.sub("[REDACTED_LOCAL_PATH]", text)
                zf.writestr(arcname, text.encode("utf-8"))
            else:
                zf.write(file_path, arcname)
        zf.writestr(
            f"{root_name}/RELEASE_MANIFEST.json",
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        )


def build_archive(output: Path, root_name: str, include_external: bool, include_proof_archive: bool) -> dict:
    output_display = (
        _normalize(output.relative_to(REPO_ROOT))
        if output.is_absolute() and output.is_relative_to(REPO_ROOT)
        else str(output)
    )

    files, included_top_level, excluded_top_level = _collect_files(
        REPO_ROOT,
        include_external=include_external,
        include_proof_archive=include_proof_archive,
    )

    command_parts = [
        "python3",
        "scripts/build_release_archive.py",
        "--output",
        output_display,
        "--root-name",
        root_name,
    ]
    if include_external:
        command_parts.append("--include-external")
    if include_proof_archive:
        command_parts.append("--include-proof-archive")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(REPO_ROOT),
        "root_name": root_name,
        "included_top_level_paths": sorted(included_top_level),
        "excluded_top_level_paths": sorted(excluded_top_level),
        "proof_path": "artifacts/proof/current",
        "alpha_status": "PASS",
        "production_ready": False,
        "archive_sha256": "computed_after_build",
        "validator_command": (
            f"python3 scripts/validate_release_archive.py --archive {output_display} --expected-root {root_name}"
        ),
        "build_command": " ".join(command_parts),
    }

    _write_archive(output, root_name, files, manifest)
    first_hash = _sha256(output)
    manifest["archive_sha256"] = first_hash
    _write_archive(output, root_name, files, manifest)

    final_hash = _sha256(output)
    return {
        "output": str(output),
        "root_name": root_name,
        "archive_sha256": final_hash,
        "file_count": len(files) + 1,
        "included_top_level_paths": sorted(included_top_level),
        "excluded_top_level_paths": sorted(excluded_top_level),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output zip path")
    parser.add_argument("--root-name", default=DEFAULT_ROOT_NAME, help="Top-level directory name")
    parser.add_argument(
        "--include-external",
        action="store_true",
        help="Include external/ tree in archive",
    )
    parser.add_argument(
        "--include-proof-archive",
        action="store_true",
        help="Include artifacts/proof/archive/ in archive",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    result = build_archive(
        output=output,
        root_name=args.root_name,
        include_external=args.include_external,
        include_proof_archive=args.include_proof_archive,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Built clean release archive: {result['output']}")
        print(f"archive_sha256={result['archive_sha256']}")
        print(f"file_count={result['file_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
