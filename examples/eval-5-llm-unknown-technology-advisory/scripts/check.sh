#!/usr/bin/env bash
# Single-command quality-gates runner for pyservice.
# Runs every automated gate; exits non-zero on any failure.
# Mirrors .github/workflows/ci.yml (which installs ruff, mypy, pytest via pip
# and runs the bare `ruff` / `mypy` / `pytest` commands); the `python3 -m`
# form below invokes the same tools and also works without console-script
# shims on PATH.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> ruff check ."
python3 -m ruff check . 2>/dev/null || ruff check .

echo "==> mypy src"
python3 -m mypy src

echo "==> pytest"
python3 -m pytest -q

echo "All automated gates passed."
