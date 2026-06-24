#!/usr/bin/env python3
"""
preprocess.py — Stage 1 of the Aladtec-schedule -> Excel pipeline.

Rasterizes a scanned, image-only Aladtec monthly-calendar PDF, fixes each
page's orientation, finds the 7 day-of-week columns, and crops one tall image
per (page, weekday). Those column images are what get transcribed in stage 2.

Usage:
    python3 preprocess.py --pdf INPUT.pdf --out WORKDIR [--dpi 400]

Outputs under WORKDIR:
    oriented/pNN.png      upright landscape page renders
    cols/pNN_cC.png       column crops  (C: 0=Sun .. 6=Sat)
    edges.json            detected column x-edges per page

Requires: poppler-utils (pdftoppm), tesseract-ocr, pillow, numpy.
"""
import argparse, json, os, subprocess, tempfile, sys
from PIL import Image
import numpy as np


def osd_rotation(png_path):
    """Return clockwise degrees tesseract thinks the page must rotate to be upright."""
    try:
        out = subprocess.run(['tesseract', png_path, 'stdout', '--psm', '0'],
                             capture_output=True, text=True, timeout=60).stdout
        for line in out.splitlines():
            if line.startswith('Rotate:'):
                return int(line.split(':')[1].strip())
    except Exception:
        pass
    return 0


def detect_vlines(img, frac=0.45):
    """Indices of strong vertical (dark) rules = day-column separators."""
    a = np.array(img.convert('L')); h, w = a.shape
    dark = a < 128
    col = dark.sum(axis=0)
    idx = [x for x in range(w) if col[x] > frac * h]
    if not idx:
        return []
    groups = [[idx[0]]]
    for i in idx[1:]:
        (groups[-1].append(i) if i - groups[-1][-1] <= 15 else groups.append([i]))
    return [int(np.mean(g)) for g in groups]


def build_template(per_page_lines, page_w):
    """From the cleanest page, derive 8 column edges (7 columns).

    Detected lines may be the 6 inner separators only, or all 8 edges (inner +
    both borders), depending on the scan. Pick the page with the most, evenly
    spaced lines and normalize to exactly 8 edges."""
    best = None
    for lines in per_page_lines.values():
        if len(lines) < 5:
            continue
        s = sorted(lines)
        diffs = np.diff(s)
        span = (max(diffs) - min(diffs)) if len(diffs) else 1e9
        score = (len(s), -span)
        if best is None or score > best[0]:
            best = (score, s)
    if best is None:                      # nothing clean; even split
        cw = page_w / 7.0
        return [int(cw * i) for i in range(8)]
    lines = best[1]
    cw = int(np.median(np.diff(lines)))   # column width
    n = len(lines)
    if n >= 8:
        edges = lines[:8]                 # lines already ARE the edges
    elif n == 7:
        edges = lines + [lines[-1] + cw]  # missing one border
    elif n == 6:
        edges = [lines[0] - cw] + lines + [lines[-1] + cw]  # 6 inner separators
    else:
        edges = [lines[0] + cw * (i - 0) for i in range(8)]  # extrapolate
    return edges[:8]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--dpi', type=int, default=400)
    ap.add_argument('--margin', type=int, default=14, help='px padding kept on each column edge')
    a = ap.parse_args()

    os.makedirs(os.path.join(a.out, 'oriented'), exist_ok=True)
    os.makedirs(os.path.join(a.out, 'cols'), exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['pdftoppm', '-r', str(a.dpi), '-png', a.pdf,
                        os.path.join(tmp, 'p')], check=True)
        raws = sorted(f for f in os.listdir(tmp) if f.endswith('.png'))
        if not raws:
            sys.exit('pdftoppm produced no pages')

        # orient every page upright-landscape
        oriented = {}
        for i, f in enumerate(raws, 1):
            src = os.path.join(tmp, f)
            r = osd_rotation(src)                 # clockwise degrees
            im = Image.open(src)
            if r:
                im = im.rotate((360 - r) % 360, expand=True)  # PIL rotates CCW
            if im.size[1] > im.size[0]:           # still portrait -> calendar is landscape
                im = im.rotate(90, expand=True)
            op = os.path.join(a.out, 'oriented', f'p{i:02d}.png')
            im.save(op); oriented[i] = op

        per_page_lines = {i: detect_vlines(Image.open(p)) for i, p in oriented.items()}
        any_w = Image.open(next(iter(oriented.values()))).size[0]
        template = build_template(per_page_lines, any_w)

        edges_out = {}
        for i, p in oriented.items():
            im = Image.open(p); w, h = im.size
            lines = per_page_lines[i]
            edges = []
            for c in template:
                near = [L for L in lines if abs(L - c) < 55]
                edges.append(int(np.mean(near)) if near else c)
            edges[0] = max(0, edges[0]); edges[-1] = min(w, edges[-1])
            edges_out[i] = {'edges': edges, 'w': w, 'h': h}
            for ci in range(7):
                x0 = max(0, edges[ci] - a.margin); x1 = min(w, edges[ci + 1] + a.margin)
                im.crop((x0, 0, x1, h)).save(
                    os.path.join(a.out, 'cols', f'p{i:02d}_c{ci}.png'))

        json.dump(edges_out, open(os.path.join(a.out, 'edges.json'), 'w'), indent=1)
        print(f'pages={len(oriented)}  column images={len(oriented)*7}  -> {a.out}/cols')


if __name__ == '__main__':
    main()
