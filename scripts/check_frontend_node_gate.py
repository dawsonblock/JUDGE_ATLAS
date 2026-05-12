#!/usr/bin/env python3
"""Fail-closed Node major-version gate for frontend proof.

Expected behavior:
- PASS only when Node major version matches required major (default: 20)
- Emit clear mismatch message for proof logs
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys


def _parse_major(node_version: str) -> int | None:
    match = re.match(r"^v?(\d+)", node_version.strip())
    if not match:
        return None
    return int(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description="Frontend Node version gate")
    parser.add_argument("--expected-major", type=int, default=20)
    args = parser.parse_args()

    proc = subprocess.run(
        ["node", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print("Node executable not available")
        return 1

    version = proc.stdout.strip() or "unknown"
    major = _parse_major(version)
    if major is None:
        print(f"Unable to parse Node version: {version}")
        return 1

    if major != args.expected_major:
        print(f"Frontend release gate requires Node {args.expected_major}.x. Current Node: {version}. Use nvm use {args.expected_major}.")
        return 1

    print(f"Node gate PASS: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
