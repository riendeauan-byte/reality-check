#!/usr/bin/env bash
# Add YOUR edited clip to the overlay pool. The overlay needs a transparent
# video (VP9 + alpha in WebM); this converts whatever you give it.
#
# Usage:
#   ./import_clip.sh /path/to/clip.mov            # input already has transparency (alpha)
#   ./import_clip.sh /path/to/clip.mp4 --green    # input is on a GREEN screen -> key it out
#   ./import_clip.sh /path/to/clip.mov myname     # set the output filename
#
# CapCut tip: export with a TRANSPARENT background if your version supports it
# (gives a .mov with alpha). If not, put the subject on a solid green background
# and pass --green.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CLIPS="$ROOT/clips"
mkdir -p "$CLIPS"

in="${1:?usage: import_clip.sh <file> [--green] [name]}"; shift || true
GREEN=0; NAME=""
for a in "$@"; do
  case "$a" in
    --green) GREEN=1 ;;
    *) NAME="$a" ;;
  esac
done
name="${NAME:-$(basename "${in%.*}")}"
out="$CLIPS/$name.webm"

if [ "$GREEN" = 1 ]; then
  VF="colorkey=0x00FF00:0.30:0.10,format=yuva420p"
else
  VF="format=yuva420p"
fi

ffmpeg -y -i "$in" -map 0:v -map "0:a?" -vf "$VF" \
  -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 28 \
  -c:a libopus -b:a 96k -shortest "$out"

echo "added -> $out"
echo "It joins the random pool immediately (no restart needed)."
