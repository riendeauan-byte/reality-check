#!/usr/bin/env python3
"""Compare background-removal methods on a single frame. -> labeled montage PNG.
Usage: compare.py <frame.png> <out_montage.png>"""
import sys
from PIL import Image, ImageDraw
from rembg import remove, new_session

frame, out = sys.argv[1], sys.argv[2]
img = Image.open(frame).convert("RGB")


def checker(w, h, sq=20):
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (225, 225, 225) if ((x // sq + y // sq) % 2 == 0) else (135, 135, 135)
    return im


def comp(rgba):
    rgba = rgba.convert("RGBA")
    bg = checker(*rgba.size)
    bg.paste(rgba, (0, 0), rgba)
    return bg


cells = []


def run(name, model, **kw):
    try:
        sess = new_session(model)
        o = remove(img, session=sess, **kw)
        cells.append((name, comp(o)))
        print("ok:", name, flush=True)
    except Exception as e:
        print("FAIL:", name, repr(e), flush=True)


run("1 u2net_human (current)", "u2net_human_seg")
run("2 isnet-general", "isnet-general-use")
run("3 u2net_human +alpha-matte", "u2net_human_seg", alpha_matting=True,
    alpha_matting_foreground_threshold=240, alpha_matting_background_threshold=10,
    alpha_matting_erode_size=8)
run("4 birefnet-general", "birefnet-general")

if not cells:
    print("no methods succeeded"); sys.exit(1)

pad, lblh = 12, 22
cw = max(c[1].width for c in cells)
ch = max(c[1].height for c in cells)
W = len(cells) * (cw + pad) + pad
H = ch + lblh + 2 * pad
mont = Image.new("RGB", (W, H), (28, 28, 28))
d = ImageDraw.Draw(mont)
x = pad
for name, im in cells:
    mont.paste(im, (x, pad + lblh))
    d.text((x + 2, pad + 4), name, fill=(255, 255, 255))
    x += cw + pad
mont.save(out)
print("montage ->", out, f"({len(cells)} methods)")
