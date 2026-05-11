from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "archive_validation_paths.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("archive_validation_paths", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_archive_validation_finds_direct_judge_main_root(tmp_path: Path) -> None:
    module = _load_module()
    extract_dir = tmp_path / "extract"
    expected = extract_dir / "JUDGE-main"
    expected.mkdir(parents=True)

    assert module.resolve_judge_main_root(extract_dir) == expected


def test_archive_validation_finds_nested_judge_main_root(tmp_path: Path) -> None:
    module = _load_module()
    extract_dir = tmp_path / "extract"
    expected = extract_dir / "JUDGE_ATLAS-main" / "JUDGE-main"
    expected.mkdir(parents=True)

    assert module.resolve_judge_main_root(extract_dir) == expected


def test_archive_validation_fails_when_no_judge_main_found(tmp_path: Path) -> None:
    module = _load_module()
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()

    try:
        module.resolve_judge_main_root(extract_dir)
    except FileNotFoundError as exc:
        assert "could not locate JUDGE-main" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_archive_validation_fails_when_multiple_judge_main_dirs_found(
    tmp_path: Path,
) -> None:
    module = _load_module()
    extract_dir = tmp_path / "extract"
    (extract_dir / "JUDGE-main").mkdir(parents=True)
    (extract_dir / "JUDGE_ATLAS-main" / "JUDGE-main").mkdir(parents=True)

    try:
        module.resolve_judge_main_root(extract_dir)
    except RuntimeError as exc:
        assert "multiple JUDGE-main candidates" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_archive_validation_prints_resolved_judge_main_path(tmp_path: Path) -> None:
    extract_dir = tmp_path / "extract"
    expected = extract_dir / "JUDGE_ATLAS-main" / "JUDGE-main"
    expected.mkdir(parents=True)

    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--extract-dir", str(extract_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0
    assert proc.stdout.strip() == str(expected)