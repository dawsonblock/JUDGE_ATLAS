#!/usr/bin/env python3
"""Validate a release archive against the current alpha release boundary."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "proof" / "current" / "archive_validation.md"
ARCHIVED_HEADER = "ARCHIVED / NOT CURRENT"
REQUIRED_DIRECTORIES = (
    "backend/",
    "frontend/",
    "docs/",
    "scripts/",
    "artifacts/proof/current/",
)
REQUIRED_PROOF_FILES = (
    "artifacts/proof/current/CURRENT_PROOF.md",
    "artifacts/proof/current/release_readiness.md",
)
FORBIDDEN_SEGMENTS = (
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
)
TEXT_METADATA_SUFFIXES = {".md", ".json", ".txt", ".yml", ".yaml"}
ABSOLUTE_PATH_PATTERNS = (
    re.compile(r'/Users/[^"\)\s]+'),
    re.compile(r'/home/[^"\)\s]+'),
    re.compile(r'/private/[^"\)\s]+'),
    re.compile(r"[A-Za-z]:\\[^\s]+"),
)


def _compute_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _top_level_roots(names: list[str]) -> list[str]:
    roots = sorted({name.split("/", 1)[0] for name in names if name and "/" in name})
    return [root for root in roots if root]


def _dir_exists(names: set[str], root: str, rel_dir: str) -> bool:
    prefix = f"{root}/{rel_dir}"
    return any(name == prefix or name.startswith(prefix) for name in names)


def _read_text_member(zf: zipfile.ZipFile, name: str) -> str | None:
    try:
        raw = zf.read(name)
    except KeyError:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def inspect_archive(archive: Path, expected_root: str, allow_external: bool = False) -> dict:
    report: dict = {
        "archive": str(archive),
        "expected_root": expected_root,
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "valid": False,
        "errors": [],
        "warnings": [],
        "archive_sha256": "",
        "compressed_size_bytes": 0,
        "uncompressed_size_bytes": 0,
        "top_level_roots": [],
        "largest_files": [],
        "largest_top_level_directories": [],
    }

    if not archive.exists() or not archive.is_file():
        report["errors"].append("archive_not_found")
        return report

    report["archive_sha256"] = _compute_sha256(archive)

    try:
        with zipfile.ZipFile(archive, "r") as zf:
            infos = [info for info in zf.infolist() if info.filename and not info.filename.endswith("/")]
            names = [info.filename for info in infos]
            name_set = set(names)
            report["compressed_size_bytes"] = sum(info.compress_size for info in infos)
            report["uncompressed_size_bytes"] = sum(info.file_size for info in infos)

            roots = _top_level_roots(names)
            report["top_level_roots"] = roots
            if len(roots) != 1:
                report["errors"].append("archive_must_have_exactly_one_top_level_root")
                return report

            root = roots[0]
            if root != expected_root:
                report["errors"].append(f"archive_root_mismatch:{root}!={expected_root}")

            for rel_dir in REQUIRED_DIRECTORIES:
                if not _dir_exists(name_set, root, rel_dir):
                    report["errors"].append(f"missing_required_directory:{rel_dir}")

            for rel_file in REQUIRED_PROOF_FILES:
                if f"{root}/{rel_file}" not in name_set:
                    report["errors"].append(f"missing_required_proof_file:{rel_file}")

            for info in infos:
                parts = Path(info.filename).parts
                if any(segment in FORBIDDEN_SEGMENTS for segment in parts):
                    report["errors"].append(f"forbidden_path:{info.filename}")
                if not allow_external and "external" in parts[1:]:
                    report["errors"].append(f"forbidden_external_path:{info.filename}")

            stale_proof_name = f"{root}/artifacts/proof/release_readiness.md"
            if stale_proof_name in name_set:
                stale_text = _read_text_member(zf, stale_proof_name)
                if stale_text is None or ARCHIVED_HEADER not in stale_text:
                    report["errors"].append("stale_release_readiness_not_archived")

            for info in infos:
                suffix = Path(info.filename).suffix.lower()
                if suffix not in TEXT_METADATA_SUFFIXES:
                    continue
                text = _read_text_member(zf, info.filename)
                if text is None:
                    continue
                for pattern in ABSOLUTE_PATH_PATTERNS:
                    match = pattern.search(text)
                    if match:
                        report["errors"].append(
                            f"absolute_path_embedded:{info.filename}:{match.group(0)}"
                        )
                        break

            largest_files = sorted(
                (
                    {
                        "path": info.filename,
                        "uncompressed_size": info.file_size,
                        "compressed_size": info.compress_size,
                    }
                    for info in infos
                ),
                key=lambda item: item["uncompressed_size"],
                reverse=True,
            )[:20]
            report["largest_files"] = largest_files

            dir_sizes: dict[str, int] = defaultdict(int)
            for info in infos:
                rel_parts = Path(info.filename).parts
                if len(rel_parts) >= 2:
                    dir_sizes[rel_parts[1]] += info.file_size
            report["largest_top_level_directories"] = [
                {"path": key, "uncompressed_size": size}
                for key, size in sorted(dir_sizes.items(), key=lambda item: item[1], reverse=True)
            ]
    except zipfile.BadZipFile:
        report["errors"].append("bad_zip_file")
        return report

    report["errors"] = sorted(set(report["errors"]))
    report["warnings"] = sorted(set(report["warnings"]))
    report["valid"] = not report["errors"]
    return report


def write_markdown(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# Archive Validation",
        "",
        f"- validated_at_utc: {report['validated_at_utc']}",
        f"- archive: {report['archive']}",
        f"- archive_sha256: {report['archive_sha256']}",
        f"- expected_root: {report['expected_root']}",
        f"- top_level_roots: {', '.join(report['top_level_roots']) or 'none'}",
        f"- root_match: {'yes' if report['top_level_roots'] == [report['expected_root']] else 'no'}",
        f"- valid: {'PASS' if report['valid'] else 'FAIL'}",
        f"- compressed_size_bytes: {report['compressed_size_bytes']}",
        f"- uncompressed_size_bytes: {report['uncompressed_size_bytes']}",
        "",
        "## Errors",
        "",
    ]
    if report["errors"]:
        lines.extend(f"- {error}" for error in report["errors"])
    else:
        lines.append("- none")

    lines.extend(["", "## Largest Files", ""])
    if report["largest_files"]:
        lines.append("| path | uncompressed | compressed |")
        lines.append("|---|---:|---:|")
        for item in report["largest_files"]:
            lines.append(
                f"| {item['path']} | {item['uncompressed_size']} | {item['compressed_size']} |"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Largest Top-Level Directories", ""])
    if report["largest_top_level_directories"]:
        lines.append("| path | uncompressed |")
        lines.append("|---|---:|")
        for item in report["largest_top_level_directories"]:
            lines.append(f"| {item['path']} | {item['uncompressed_size']} |")
    else:
        lines.append("- none")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, help="Path to archive zip")
    parser.add_argument("--expected-root", required=True, help="Expected top-level archive root")
    parser.add_argument("--allow-external", action="store_true", help="Allow external/ paths in archive")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Markdown output path",
    )
    parser.add_argument("--json", action="store_true", help="Also print JSON report")
    args = parser.parse_args()

    archive = Path(args.archive).resolve()
    output = Path(args.output).resolve()

    report = inspect_archive(archive, expected_root=args.expected_root, allow_external=args.allow_external)
    write_markdown(report, output)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Archive validation written to {output}")
        print("PASS" if report["valid"] else "FAIL")

    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())