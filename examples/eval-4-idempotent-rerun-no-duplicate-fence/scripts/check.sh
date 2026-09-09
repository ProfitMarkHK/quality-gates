#!/usr/bin/env bash
# Single-command quality-gate runner for pyservice.
# Runs every automated gate; exits non-zero on any failure.
set -euo pipefail
cd "$(dirname "$0")/.."

ruff check .
mypy src
pytest
