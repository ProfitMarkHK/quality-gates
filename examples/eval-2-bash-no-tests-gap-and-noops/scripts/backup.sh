#!/usr/bin/env bash
set -euo pipefail

SRC="${1:-/data}"
DEST="${2:-/backups}"

mkdir -p "$DEST"
tar czf "$DEST/backup-$(date +%F).tar.gz" "$SRC"
echo "backup written to $DEST"
