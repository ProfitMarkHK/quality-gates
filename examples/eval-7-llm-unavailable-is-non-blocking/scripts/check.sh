#!/usr/bin/env bash
# Run every automated quality gate for pyservice.
# Exits non-zero on any failure; suitable for pre-commit hooks and CI.
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m ruff check .
python3 -m mypy src
python3 -m pytest
