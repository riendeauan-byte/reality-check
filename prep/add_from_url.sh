#!/usr/bin/env bash
# Add ONE clip from a URL: download -> trim -> remove background -> auto-crop to
# the subject -> transparent VP9/alpha WebM in clips/. Local + free (yt-dlp +
# ffmpeg + rembg). The clip joins the overlay's random pool immediately.
#
# Emits machine-readable progress for the dashboard UI:
#   RC:STAGE <name>   resolve|download|trim|matte|crop|encode
#   RC:DONE <file>    success, file is in clips/
#   RC:ERR <message>  failure (also exits non-zero)
#
# Usage: add_from_url.sh <url> [--start <time>] [--len <seconds>]
#   --start  ffmpeg time (e.g. 0:30 or 30); default 0
#   --len    seconds to keep; default/blank -> capped at MAXLEN
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLIPS="$DIR/clips"
SRC="$DIR/prep/src"
PY="$DIR/prep/venv/bin/python"
[ -x "$PY" ] || PY=python3
MODEL="u2net_human_seg"   # rembg model tuned for people
FPS=18
H=432                      # working frame height before crop; width follows aspect
MAXLEN=60                  # hard cap on seconds (disk + runtime)
OUTLINE_PX=6               # white sticker border around the subject, px (0 = off)
mkdir -p "$CLIPS" "$SRC"

url=""
START="0"
LEN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --start) START="${2:-0}"; shift 2 ;;
    --len)   LEN="${2:-}";   shift 2 ;;
    *)       url="$1";        shift ;;
  esac
done

err() { echo "RC:ERR $*"; exit 1; }

[ -n "$url" ] || err "no URL given"
[ -n "$LEN" ] || LEN="$MAXLEN"

echo "RC:STAGE resolve"
vid=$(yt-dlp --no-warnings --get-id "$url" 2>/dev/null || true)
[ -n "$vid" ] || err "could not read that URL"
out="$CLIPS/$vid.webm"
# Never clobber an existing clip with the same video id: suffix instead.
if [ -f "$out" ]; then
  n=2
  while [ -f "$CLIPS/$vid-$n.webm" ]; do n=$((n + 1)); done
  out="$CLIPS/$vid-$n.webm"
fi

echo "RC:STAGE download"
yt-dlp -q -f 'bv*+ba/b' -o "$SRC/$vid.%(ext)s" "$url" || err "download failed"
in=$(ls "$SRC/$vid".* 2>/dev/null | head -1 || true)
[ -n "$in" ] || err "download produced no file"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"; rm -f "$SRC/$vid".*' EXIT

echo "RC:STAGE trim"
ffmpeg -y -loglevel error -ss "$START" -t "$LEN" -i "$in" \
  -vf "scale=-2:$H,fps=$FPS" "$tmp/scaled.mp4" || err "trim/scale failed"
mkdir -p "$tmp/f" "$tmp/o"
ffmpeg -y -loglevel error -i "$tmp/scaled.mp4" "$tmp/f/%05d.png" || err "frame extract failed"
nf=$(ls "$tmp/f" 2>/dev/null | wc -l | tr -d ' ')
[ "${nf:-0}" -gt 0 ] || err "no frames (check start time / length)"

echo "RC:STAGE matte"
"$PY" "$DIR/prep/matte.py" "$tmp/f" "$tmp/o" "$MODEL" || err "background removal failed"

if [ "$OUTLINE_PX" -gt 0 ]; then
  echo "RC:STAGE outline"
  "$PY" "$DIR/prep/outline.py" "$tmp/o" "$OUTLINE_PX" || err "outline failed"
fi

echo "RC:STAGE crop"
crop=$("$PY" "$DIR/prep/alpha_bbox.py" "$tmp/o" 0.04) || err "crop calculation failed"
read -r cw ch cx cy <<<"$crop"
[ -n "${cw:-}" ] || err "crop calculation returned nothing"

echo "RC:STAGE encode"
ffmpeg -y -loglevel error -framerate "$FPS" -i "$tmp/o/%05d.png" -i "$tmp/scaled.mp4" \
  -map 0:v -map "1:a?" \
  -vf "crop=$cw:$ch:$cx:$cy,scale='min(360,iw)':-2:flags=lanczos,format=yuva420p" \
  -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 32 \
  -deadline good -cpu-used 2 -row-mt 1 -auto-alt-ref 0 \
  -c:a libopus -b:a 96k -shortest "$out" || err "encode failed"

echo "RC:DONE $(basename "$out")"
