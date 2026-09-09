#!/usr/bin/env bash
set -euo pipefail

ARCHIVE="$1"
DEST="${2:-/data}"

mkdir -p "$DEST"
tar xzf "$ARCHIVE" -C "$DEST"
echo "restored $ARCHIVE to $DEST"
