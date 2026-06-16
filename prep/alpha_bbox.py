#!/usr/bin/env python3
"""Union alpha bounding box across matted RGBA frames -> ffmpeg crop "w h x y".

After background removal the subject sits in a transparent frame, often small
and off-center. This finds the tightest box that contains the subject across the
whole clip (union of per-frame alpha bounding boxes), pads it a little, snaps to
even dimensions (VP9 needs even w/h), and prints it for ffmpeg's crop filter.

Faint rembg edge pixels are ignored by binarizing alpha first, so a soft halo
does not inflate the box to the full frame.

Usage: alpha_bbox.py <frames_dir> [pad_frac]   # prints: "w h x y"
"""
import glob
import os
import sys

from PIL import Image

d = sys.argv[1]
pad_frac = float(sys.argv[2]) if len(sys.argv) > 2 else 0.04
frames = sorted(glob.glob(os.path.join(d, "*.png")))
if not frames:
    sys.exit("no frames")

W, H = Image.open(frames[0]).size
minx = miny = 10 ** 9
maxx = maxy = -1
step = max(1, len(frames) // 120)  # sample up to ~120 frames; bbox is cheap but cap it
for f in frames[::step]:
    im = Image.open(f)
    if im.mode != "RGBA":
        continue
    a = im.split()[-1].point(lambda v: 255 if v > 16 else 0)  # drop faint edge pixels
    bb = a.getbbox()  # (left, top, right, bottom) of nonzero alpha; right/bottom exclusive
    if not bb:
        continue
    l, t, r, b = bb
    minx = min(minx, l)
    miny = min(miny, t)
    maxx = max(maxx, r)
    maxy = max(maxy, b)

if maxx < 0:  # nothing found (fully transparent) -> keep the full frame
    print(f"{W} {H} 0 0")
    sys.exit(0)

px, py = int(W * pad_frac), int(H * pad_frac)
x0 = max(0, minx - px)
y0 = max(0, miny - py)
x1 = min(W, maxx + px)
y1 = min(H, maxy + py)
w = max(2, (x1 - x0) // 2 * 2)
h = max(2, (y1 - y0) // 2 * 2)
x0 = min(x0, W - w)  # keep crop window inside the frame
y0 = min(y0, H - h)
print(f"{w} {h} {x0} {y0}")
