#!/usr/bin/env bash
# Guard: fail if any .pyc or __pycache__ files are committed to git,
# or exist on-disk when running outside a git repository.
set -euo pipefail

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if git ls-files --cached | grep -qE '\.pyc$|__pycache__'; then
        echo "ERROR: Committed bytecode files detected:"
        git ls-files --cached | grep -E '\.pyc$|__pycache__'
        exit 1
    fi
else
    # Not in a git repo — only fail on distributed .pyc files.
    # Runtime __pycache__ directories are expected during proof execution.
    if find . \
        \( -type d \( -name "__pycache__" -o -name ".venv" -o -name "node_modules" -o -name ".next" \) -prune \) \
        -o -name "*.pyc" -print -quit | grep -q .; then
        echo "ERROR: Bytecode files found on disk (non-git context):"
        find . \
            \( -type d \( -name "__pycache__" -o -name ".venv" -o -name "node_modules" -o -name ".next" \) -prune \) \
            -o -name "*.pyc" -print | head -20
        exit 1
    fi
fi
echo "OK: No committed bytecode files"
