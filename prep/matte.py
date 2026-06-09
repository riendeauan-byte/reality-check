#!/usr/bin/env python3
"""Background-remove a folder of PNG frames using rembg (local, free).
Usage: matte.py <in_dir> <out_dir> <model>"""
import sys, glob, os
from rembg import remove, new_session
from PIL import Image

indir, outdir, model = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(outdir, exist_ok=True)
sess = new_session(model)
frames = sorted(glob.glob(os.path.join(indir, "*.png")))
print(f"matting {len(frames)} frames with {model}")
for i, f in enumerate(frames):
    img = Image.open(f).convert("RGB")
    out = remove(img, session=sess)  # PIL RGBA, background transparent
    out.save(os.path.join(outdir, os.path.basename(f)))
    if i % 50 == 0:
        print(f"  {i}/{len(frames)}", flush=True)
print("matte done")
