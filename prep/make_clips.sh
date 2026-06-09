#!/usr/bin/env bash
# Build transparent WebM clips from YouTube URLs. Local + free. Disk-safe.
# Idempotent + additive: each clip is named <youtube_id>.webm; already-built ids skip.
# Usage: ./make_clips.sh <url1> <url2> ...
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLIPS="$DIR/clips"
SRC="$DIR/prep/src"
PY="$DIR/prep/venv/bin/python"
MODEL="u2net_human_seg"   # tuned for people
FPS=18
H=432                      # frame height; width follows aspect
MAXLEN=60                  # cap seconds (disk + runtime)
mkdir -p "$CLIPS" "$SRC"

for url in "$@"; do
  vid=$(yt-dlp --no-warnings --get-id "$url" 2>/dev/null || true)
  if [ -z "$vid" ]; then echo "  !! cannot resolve id: $url (skip)"; continue; fi
  out="$CLIPS/$vid.webm"
  if [ -f "$out" ]; then echo ">> $vid already built, skip"; continue; fi
  echo ">> $vid  $url"
  yt-dlp -q -f 'bv*+ba/b' -o "$SRC/$vid.%(ext)s" "$url"
  in=$(ls "$SRC/$vid".* | head -1)
  tmp=$(mktemp -d)
  ffmpeg -y -loglevel error -t "$MAXLEN" -i "$in" -vf "scale=-2:$H,fps=$FPS" "$tmp/scaled.mp4"
  mkdir -p "$tmp/f" "$tmp/o"
  ffmpeg -y -loglevel error -i "$tmp/scaled.mp4" "$tmp/f/%05d.png"
  "$PY" "$DIR/prep/matte.py" "$tmp/f" "$tmp/o" "$MODEL"
  ffmpeg -y -loglevel error -framerate "$FPS" -i "$tmp/o/%05d.png" -i "$tmp/scaled.mp4" \
    -map 0:v -map "1:a?" \
    -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 32 \
    -c:a libopus -b:a 96k -shortest "$out"
  rm -rf "$tmp"; rm -f "$SRC/$vid".*
  echo "   -> $out  ($(du -h "$out" | cut -f1))"
done
echo "ALL_CLIPS_DONE: $(ls "$CLIPS"/*.webm 2>/dev/null | wc -l | tr -d ' ') clips total"
