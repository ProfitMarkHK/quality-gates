#!/usr/bin/env bash
# Run every automated quality gate. Exits non-zero on any failure.
# Prerequisite (as in .github/workflows/ci.yml and README.md):
#   pip install -e . ruff mypy pytest
set -euo pipefail
cd "$(dirname "$0")/.."
ruff check .
python3 -m mypy src
python3 -m pytest
