#!/usr/bin/env python3
"""Add a thick white "sticker" outline around the matted subject.

For each RGBA frame: dilate the subject's alpha by N pixels, paint that grown
region solid white, then composite the original subject back on top. The result
is the subject ringed by a clean white border on a transparent background, the
look short-form reels use. Frames are overwritten in place.

Run it BEFORE the auto-crop so the crop box includes the new border.

Local + free (PIL + numpy + scipy). Usage:
  outline.py <frames_dir> [width_px]   # default width 12
"""
import glob
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

d = sys.argv[1]
width = int(sys.argv[2]) if len(sys.argv) > 2 else 12
WHITE = (255, 255, 255)
ALPHA_T = 16  # treat alpha above this as "subject" when growing the ring

frames = sorted(glob.glob(os.path.join(d, "*.png")))
if not frames:
    sys.exit("no frames")

for f in frames:
    arr = np.array(Image.open(f).convert("RGBA"))
    a = arr[..., 3]
    mask = a > ALPHA_T
    if not mask.any():
        continue  # empty frame, nothing to outline
    # Grow the mask by `width`: every background pixel within `width` of the
    # subject becomes part of the ring (distance to nearest subject pixel).
    grown = distance_transform_edt(~mask) <= width

    out = np.zeros_like(arr)
    out[grown] = (WHITE[0], WHITE[1], WHITE[2], 255)  # white ring, opaque

    # Composite the original subject over the white using its own alpha, so the
    # subject's anti-aliased edge blends onto the border instead of the void.
    af = (a.astype(np.float32) / 255.0)[..., None]
    out[..., :3] = (arr[..., :3] * af + out[..., :3] * (1 - af)).astype(np.uint8)
    # Opaque across the whole grown region; keep subject alpha where it's higher.
    out[..., 3] = np.maximum(np.where(grown, 255, 0), a).astype(np.uint8)

    Image.fromarray(out, "RGBA").save(f)

print(f"outlined {len(frames)} frames, {width}px white border")
