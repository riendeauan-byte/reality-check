#!/usr/bin/env python3
"""Green-key (#00FF00) a folder of frames AND auto-crop transparent margins,
so the clip is tight to its visible content (subject + captions). Removes the
empty bottom/side space that made the subject float above the screen edge.
Usage: key_green_crop.py <in_dir> <out_dir>"""
import sys, glob, os
import numpy as np
from PIL import Image

indir, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
frames = sorted(glob.glob(os.path.join(indir, "*.png")))
if not frames:
    print("no frames"); sys.exit(1)


def is_content(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    green = (g > 90) & (g - r > 40) & (g - b > 40)
    return ~green


# pass 1: global content bounding box across all frames
H, W = np.asarray(Image.open(frames[0]).convert("RGB")).shape[:2]
x0, y0, x1, y1 = W, H, -1, -1
for f in frames:
    a = np.asarray(Image.open(f).convert("RGB"))
    m = is_content(a)
    cols = np.where(m.sum(0) > 5)[0]
    rows = np.where(m.sum(1) > 5)[0]
    if len(cols) == 0 or len(rows) == 0:
        continue
    x0 = min(x0, int(cols[0])); x1 = max(x1, int(cols[-1]))
    y0 = min(y0, int(rows[0])); y1 = max(y1, int(rows[-1]))

pad = 4
x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
x1 = min(W - 1, x1 + pad); y1 = min(H - 1, y1 + pad)
w = ((x1 - x0 + 1) // 2) * 2
h = ((y1 - y0 + 1) // 2) * 2
print(f"bbox x{x0} y{y0} {w}x{h} (from {W}x{H})", flush=True)

# pass 2: crop + key + green-spill suppression
for f in frames:
    a = np.asarray(Image.open(f).convert("RGB"))[y0:y0 + h, x0:x0 + w].astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = (g > 90) & (g - r > 40) & (g - b > 40)
    alpha = np.where(green, 0, 255).astype(np.uint8)
    out = a.copy()
    spill = g > (np.maximum(r, b) + 10)
    out[..., 1] = np.where(spill, np.maximum(r, b), g)  # despill edges
    Image.fromarray(np.dstack([out.astype(np.uint8), alpha]), "RGBA").save(
        os.path.join(outdir, os.path.basename(f)))
print("key_green_crop done", flush=True)
