#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Build standalone GRACE executable for distribution
# Requires: pyinstaller
# ──────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"

echo "Building GRACE standalone executable..."

cd "$SCRIPT_DIR"
pyinstaller --clean --noconfirm GRACE.spec 2>&1

echo ""
echo "Done! Standalone executable at:"
echo "  $DIST_DIR/GRACE"
if [ -f "$DIST_DIR/GRACE" ]; then
    ls -lh "$DIST_DIR/GRACE"
fi
