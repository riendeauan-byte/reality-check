#!/usr/bin/env bash
# Batch every green-screen .mov in "manual renders/" into a transparent,
# auto-cropped, size-compact VP9/alpha WebM in clips/. One ffmpeg pass per
# clip, no PNG frame dumps, so it stays light on disk.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/prep/venv/bin/python"
[ -x "$PY" ] || PY=python3
exec "$PY" "$ROOT/prep/batch_lean.py"
