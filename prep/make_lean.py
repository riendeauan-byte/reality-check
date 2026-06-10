#!/usr/bin/env python3
"""
Lean green-screen -> transparent VP9/alpha WebM, one ffmpeg pass per clip.

Why this exists: the older pipeline dumped full RGBA PNG sequences to disk,
which blows up a near-full disk for dozens of clips. This samples a handful of
frames only to find (a) the real green key color and (b) a tight crop box, then
does a single ffmpeg pass: crop -> scale -> colorkey -> despill -> vp9 alpha.

Usage:
  make_lean.py <input.mov> <output.webm>
  make_lean.py --probe <input.mov>      # just print bbox + key color
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image

MAX_W = 640          # output width cap (300px CSS @2x retina = 600px; 640 is safe-sharp)
SAMPLES = 16         # frames sampled to compute crop + key color
PAD_FRAC = 0.02      # padding around detected subject, fraction of frame
CRF = 33             # VP9 quality (lower = better/bigger); 33 = compact, clean
AUDIO_K = "96k"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_dims(path):
    out = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-show_entries", "format=duration",
        "-of", "json", path,
    ]).stdout
    j = json.loads(out)
    w = int(j["streams"][0]["width"])
    h = int(j["streams"][0]["height"])
    dur = float(j["format"]["duration"])
    return w, h, dur


def is_green(r, g, b):
    # bright, clearly-green pixel: green dominant by a margin
    return g > 90 and (g - r) > 40 and (g - b) > 40


def analyze(path, w, h, dur):
    """Sample frames -> (crop x,y,cw,ch), median green key color."""
    with tempfile.TemporaryDirectory() as td:
        sw = 320
        sh = max(2, round(h * sw / w / 2) * 2)
        for i in range(SAMPLES):
            t = dur * (i + 0.5) / SAMPLES
            run([
                "ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.2f}",
                "-i", path, "-frames:v", "1",
                "-vf", f"scale={sw}:{sh}", os.path.join(td, f"{i:02d}.png"), "-y",
            ])
        minx = miny = 10**9
        maxx = maxy = -1
        greens = []
        for i in range(SAMPLES):
            fp = os.path.join(td, f"{i:02d}.png")
            if not os.path.exists(fp):
                continue
            im = Image.open(fp).convert("RGB")
            px = im.load()
            iw, ih = im.size
            # corners = background -> collect green color
            for cx, cy in [(2, 2), (iw - 3, 2), (2, ih - 3), (iw - 3, ih - 3)]:
                greens.append(px[cx, cy])
            # subject bbox = non-green pixels
            for y in range(0, ih, 2):
                row_hit = False
                for x in range(0, iw, 2):
                    r, g, b = px[x, y]
                    if not is_green(r, g, b):
                        if x < minx: minx = x
                        if x > maxx: maxx = x
                        if y < miny: miny = y
                        if y > maxy: maxy = y
                        row_hit = True
                _ = row_hit
    if maxx < 0:
        # nothing detected; use full frame
        minx, miny, maxx, maxy = 0, 0, sw - 1, sh - 1
    # scale bbox back to full res
    fx = w / sw
    fy = h / sh
    pad_x = int(w * PAD_FRAC)
    pad_y = int(h * PAD_FRAC)
    x0 = max(0, int(minx * fx) - pad_x)
    y0 = max(0, int(miny * fy) - pad_y)
    x1 = min(w, int((maxx + 1) * fx) + pad_x)
    y1 = min(h, int((maxy + 1) * fy) + pad_y)
    cw = max(2, (x1 - x0) // 2 * 2)
    ch = max(2, (y1 - y0) // 2 * 2)
    # median green
    greens.sort(key=lambda c: c[1])
    gr, gg, gb = greens[len(greens) // 2] if greens else (0, 255, 0)
    key = f"0x{gr:02X}{gg:02X}{gb:02X}"
    return (x0, y0, cw, ch), key


def encode(path, out, crop, key):
    x, y, cw, ch = crop
    vf = (
        f"crop={cw}:{ch}:{x}:{y},"
        f"scale='min({MAX_W},iw)':-2:flags=lanczos,"
        f"colorkey={key}:0.30:0.12,"
        f"despill=type=green:mix=0.5:expand=0.3,"
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
        path = args[1]
        w, h, dur = probe_dims(path)
        crop, key = analyze(path, w, h, dur)
        print(f"{w}x{h} {dur:.1f}s  crop={crop}  key={key}")
        return
    inp, out = args[0], args[1]
    w, h, dur = probe_dims(inp)
    crop, key = analyze(inp, w, h, dur)
    ok = encode(inp, out, crop, key)
    if ok:
        sz = os.path.getsize(out) // 1024
        print(f"OK  {os.path.basename(out)}  {sz}KB  crop={crop} key={key}")
    else:
        sys.exit(f"FAILED {inp}")


if __name__ == "__main__":
    main()
