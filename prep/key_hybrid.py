#!/usr/bin/env python3
"""Make CapCut black-bg renders transparent WITHOUT holing dark clothing.
Cut a pixel only if it is near-black AND not part of the segmented person.
Keeps: person (incl. dark clothes/hair via model), white outline, bright captions.
Usage: key_hybrid.py <in_dir> <out_dir> [model=u2net_human_seg] [black_thresh=44]"""
import sys, glob, os
import numpy as np
from scipy import ndimage
from PIL import Image
from rembg import remove, new_session

indir, outdir = sys.argv[1], sys.argv[2]
model = sys.argv[3] if len(sys.argv) > 3 else "u2net_human_seg"
T = int(sys.argv[4]) if len(sys.argv) > 4 else 44
os.makedirs(outdir, exist_ok=True)
sess = new_session(model)
frames = sorted(glob.glob(os.path.join(indir, "*.png")))
print(f"keying {len(frames)} frames (model={model}, T={T})", flush=True)

for i, f in enumerate(frames):
    im = Image.open(f).convert("RGB")
    a = np.asarray(im)
    # person mask from the model (clean on a black background)
    mask = np.asarray(remove(im, session=sess, only_mask=True).convert("L"))
    person = ndimage.binary_dilation(mask > 30, iterations=3)
    near_black = (a[..., 0] < T) & (a[..., 1] < T) & (a[..., 2] < T)
    transparent = near_black & ~person          # only cut background black
    alpha = np.where(transparent, 0, 255).astype(np.uint8)
    alpha = ndimage.grey_erosion(alpha, size=(2, 2))  # 1px feather, kills dark halo
    Image.fromarray(np.dstack([a, alpha]), "RGBA").save(
        os.path.join(outdir, os.path.basename(f)))
    if i % 50 == 0:
        print(f"  {i}/{len(frames)}", flush=True)
print("key_hybrid done", flush=True)
