#!/usr/bin/env python3
"""
Lean chroma-screen -> transparent VP9/alpha WebM, one ffmpeg pass per clip.

Keys ONLY the solid chroma background (green or magenta) and nothing else: a
tight colorkey on the canonical chroma color, no despill. Despill was removed
because it tinted the subject's light outline magenta and, combined with a loose
key, ate chroma-spill-contaminated grays out of the subject. Tight + no-despill
keeps the subject fully intact.

Samples a handful of frames only (to find the chroma color and a crop box), then
one ffmpeg pass: crop -> scale(360w) -> 24fps -> colorkey -> vp9 alpha. No PNG
frame dumps, so it stays light on disk.

Usage:
  make_lean.py <input.mov> <output.webm>
  make_lean.py --probe <input.mov>
"""
import json
import math
import os
import subprocess
import sys
import tempfile

from PIL import Image

MAX_W = 360          # output width cap (user spec: 360p)
FPS = 24             # output frame rate (user spec)
SAMPLES = 16         # frames sampled to compute crop + key color
PAD_FRAC = 0.02      # padding around detected subject
CRF = 32             # VP9 quality (lower = better/bigger)
AUDIO_K = "96k"
KEY_SIM = "0.20"     # colorkey similarity: tight, so only near-exact chroma goes
KEY_BLEND = "0.05"   # colorkey blend: small soft edge


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_dims(path):
    j = json.loads(run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-show_entries", "format=duration",
        "-of", "json", path,
    ]).stdout)
    w = int(j["streams"][0]["width"])
    h = int(j["streams"][0]["height"])
    dur = float(j["format"]["duration"])
    return w, h, dur


def sat(px):
    r, g, b = px
    return max(r, g, b) - min(r, g, b)


def snap_key(rgb):
    """Snap a sampled chroma toward the canonical screen color it clearly is."""
    r, g, b = rgb
    if g > r + 50 and g > b + 50:
        return (0, 255, 0)            # green screen
    if r > g + 50 and b > g + 50:
        return (255, 0, 255)          # magenta screen
    return rgb


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def analyze(path, w, h, dur):
    """Sample frames -> (crop x,y,cw,ch), canonical chroma key color."""
    with tempfile.TemporaryDirectory() as td:
        sw = 320
        sh = max(2, round(h * sw / w / 2) * 2)
        for i in range(SAMPLES):
            t = dur * (i + 0.5) / SAMPLES
            run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.2f}",
                 "-i", path, "-frames:v", "1", "-vf", f"scale={sw}:{sh}",
                 os.path.join(td, f"{i:02d}.png"), "-y"])
        vivid = []
        frames = []
        for i in range(SAMPLES):
            fp = os.path.join(td, f"{i:02d}.png")
            if not os.path.exists(fp):
                continue
            im = Image.open(fp).convert("RGB")
            frames.append(im)
            px = im.load()
            iw, ih = im.size
            # border ring = background; collect its vivid (high-saturation) pixels
            for x in range(0, iw, 3):
                for y in (0, 1, ih - 2, ih - 1):
                    p = px[x, y]
                    if sat(p) > 60:
                        vivid.append(p)
            for y in range(0, ih, 3):
                for x in (0, 1, iw - 2, iw - 1):
                    p = px[x, y]
                    if sat(p) > 60:
                        vivid.append(p)
    if vivid:
        vivid.sort(key=lambda p: p[1])  # by green channel; median is stable
        key = snap_key(vivid[len(vivid) // 2])
    else:
        key = (0, 255, 0)
    # subject bbox = pixels NOT close to the chroma key
    minx = miny = 10 ** 9
    maxx = maxy = -1
    sw2 = sh2 = None
    for im in frames:
        px = im.load()
        iw, ih = im.size
        sw2, sh2 = iw, ih
        for y in range(0, ih, 2):
            for x in range(0, iw, 2):
                if dist(px[x, y], key) > 110:
                    if x < minx: minx = x
                    if x > maxx: maxx = x
                    if y < miny: miny = y
                    if y > maxy: maxy = y
    if maxx < 0 or not sw2:
        return (0, 0, (w // 2) * 2, (h // 2) * 2), key
    fx, fy = w / sw2, h / sh2
    pad_x, pad_y = int(w * PAD_FRAC), int(h * PAD_FRAC)
    x0 = max(0, int(minx * fx) - pad_x)
    y0 = max(0, int(miny * fy) - pad_y)
    x1 = min(w, int((maxx + 1) * fx) + pad_x)
    y1 = min(h, int((maxy + 1) * fy) + pad_y)
    cw = max(2, (x1 - x0) // 2 * 2)
    ch = max(2, (y1 - y0) // 2 * 2)
    return (x0, y0, cw, ch), key


def encode(path, out, crop, key):
    x, y, cw, ch = crop
    hexkey = "0x%02X%02X%02X" % key
    vf = (
        f"crop={cw}:{ch}:{x}:{y},"
        f"scale='min({MAX_W},iw)':-2:flags=lanczos,"
        f"fps={FPS},"
        f"colorkey={hexkey}:{KEY_SIM}:{KEY_BLEND},"
        f"format=yuva420p"
    )
    cmd = [
        "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", path,
        "-vf", vf,
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
        "-crf", str(CRF), "-b:v", "0",
        "-deadline", "good", "-cpu-used", "2", "-row-mt", "1", "-auto-alt-ref", "0",
        "-c:a", "libopus", "-b:a", AUDIO_K,
        out,
    ]
    r = run(cmd)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
    return r.returncode == 0


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: make_lean.py <in.mov> <out.webm> | --probe <in.mov>")
    if args[0] == "--probe":
        w, h, dur = probe_dims(args[1])
        crop, key = analyze(args[1], w, h, dur)
        print(f"{w}x{h} {dur:.1f}s  crop={crop}  key=#{key[0]:02X}{key[1]:02X}{key[2]:02X}")
        return
    inp, out = args[0], args[1]
    w, h, dur = probe_dims(inp)
    crop, key = analyze(inp, w, h, dur)
    if encode(inp, out, crop, key):
        sz = os.path.getsize(out) // 1024
        print(f"OK  {os.path.basename(out)}  {sz}KB  key=#{key[0]:02X}{key[1]:02X}{key[2]:02X}")
    else:
        sys.exit(f"FAILED {inp}")


if __name__ == "__main__":
    main()
