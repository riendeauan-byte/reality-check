#!/usr/bin/env python3
"""Batch every manual-renders green-screen .mov -> clips/<slug>.webm (lean pass)."""
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "manual renders")
OUT = os.path.join(ROOT, "clips")
PY = os.path.join(ROOT, "prep", "venv", "bin", "python")
LEAN = os.path.join(ROOT, "prep", "make_lean.py")


def slug(name):
    s = os.path.splitext(os.path.basename(name))[0].lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "clip"


def main():
    movs = sorted(glob.glob(os.path.join(SRC, "*.mov")))
    os.makedirs(OUT, exist_ok=True)
    total = len(movs)
    ok = 0
    fail = []
    seen = {}
    for i, m in enumerate(movs, 1):
        s = slug(m)
        if s in seen:
            s = f"{s}-{i}"
        seen[s] = m
        out = os.path.join(OUT, s + ".webm")
        print(f"[{i}/{total}] {os.path.basename(m)} -> {s}.webm", flush=True)
        r = subprocess.run([PY, LEAN, m, out])
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 10000:
            ok += 1
        else:
            fail.append(os.path.basename(m))
    print(f"\n=== DONE {ok}/{total} ok ===", flush=True)
    if fail:
        print("FAILED:", ", ".join(fail), flush=True)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
