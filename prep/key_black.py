#!/usr/bin/env python3
"""Make the BLACK background of CapCut renders transparent, using a
border-connected fill: only near-black pixels connected to the frame edge
become transparent, so interior black (clothing/hair) stays opaque.
Usage: key_black.py <in_dir> <out_dir> [threshold=40]"""
import sys, glob, os
import numpy as np
from scipy import ndimage
from PIL import Image

indir, outdir = sys.argv[1], sys.argv[2]
T = int(sys.argv[3]) if len(sys.argv) > 3 else 40
os.makedirs(outdir, exist_ok=True)
frames = sorted(glob.glob(os.path.join(indir, "*.png")))
print(f"keying {len(frames)} frames (T={T})", flush=True)

for i, f in enumerate(frames):
    im = Image.open(f).convert("RGB")
    a = np.asarray(im)
    near_black = (a[..., 0] < T) & (a[..., 1] < T) & (a[..., 2] < T)
    lbl, _ = ndimage.label(near_black)
    border = np.unique(np.concatenate([lbl[0, :], lbl[-1, :], lbl[:, 0], lbl[:, -1]]))
    border = border[border != 0]
    bg = np.isin(lbl, border)
    # feather 1px so the white-outline edge has no hard jaggies
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    alpha = ndimage.grey_erosion(alpha, size=(2, 2))  # pull in 1px to kill dark halo
    rgba = np.dstack([a, alpha])
    Image.fromarray(rgba, "RGBA").save(os.path.join(outdir, os.path.basename(f)))
    if i % 50 == 0:
        print(f"  {i}/{len(frames)}", flush=True)
print("key_black done", flush=True)
