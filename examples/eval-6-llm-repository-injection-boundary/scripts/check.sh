#!/usr/bin/env bash
# Run every automated quality gate. Exits non-zero on any failure.
# Prerequisites (per .github/workflows/ci.yml): pip install -e . ruff mypy pytest
set -euo pipefail
cd "$(dirname "$0")/.."
ruff check .
mypy src
pytest
