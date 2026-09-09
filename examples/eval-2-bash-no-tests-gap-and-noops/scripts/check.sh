#!/usr/bin/env bash
# Quality-gate runner: runs every automated gate, exits non-zero on any failure.
set -euo pipefail

cd "$(dirname "$0")/.."

fail=0

if ! command -v shellcheck >/dev/null 2>&1; then
  echo "FAIL: shellcheck not installed (required for gate 3). Install it: https://www.shellcheck.net" >&2
  exit 1
fi

echo "==> gate 3: shellcheck scripts/*.sh"
if ! shellcheck scripts/*.sh; then
  fail=1
fi

echo "==> gate 3 (syntax): bash -n on each script"
for f in scripts/*.sh; do
  if ! bash -n "$f"; then
    echo "FAIL: bash -n $f" >&2
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  echo "quality gates FAILED" >&2
  exit 1
fi

echo "quality gates passed"
