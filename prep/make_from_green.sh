#!/usr/bin/env bash
# Turn green-screen (#00FF00) renders in "manual renders/" into transparent
# WebM clips, AUTO-CROPPED tight to content so the subject sits flush.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
MR="$DIR/manual renders"
CLIPS="$DIR/clips"
PY="$DIR/prep/venv/bin/python"
FPS=18; H=540; MAXLEN=60
mkdir -p "$CLIPS"

shopt -s nullglob
for f in "$MR"/*.mov "$MR"/*.mp4 "$MR"/*.MOV "$MR"/*.MP4; do
  [ -f "$f" ] || continue
  base=$(basename "$f"); base="${base%.*}"
  slug=$(echo "$base" | tr ' ()/.' '_____' | tr -s '_')
  out="$CLIPS/$slug.webm"
  echo ">> $slug"
  tmp=$(mktemp -d); mkdir -p "$tmp/f" "$tmp/o"
  ffmpeg -y -loglevel error -t "$MAXLEN" -i "$f" -vf "scale=-2:$H,fps=$FPS" "$tmp/scaled.mp4"
  ffmpeg -y -loglevel error -i "$tmp/scaled.mp4" "$tmp/f/%05d.png"
  "$PY" "$DIR/prep/key_green_crop.py" "$tmp/f" "$tmp/o"
  ffmpeg -y -loglevel error -framerate "$FPS" -i "$tmp/o/%05d.png" -i "$tmp/scaled.mp4" \
    -map 0:v -map "1:a?" -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 30 \
    -c:a libopus -b:a 96k -shortest "$out"
  rm -rf "$tmp"
  echo "   -> $out  ($(du -h "$out" | cut -f1))"
done
echo "GREEN_DONE: $(ls "$CLIPS"/*.webm 2>/dev/null | wc -l | tr -d ' ') in pool"
