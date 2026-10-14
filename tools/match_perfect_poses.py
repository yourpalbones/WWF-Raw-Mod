"""Match Raw Bret pieces to Royal Bret frames so Royal Perfect's same frame can replace the adapted Raw art.

Mr. Perfect's slot reuses Raw Bret's 1,720 frame pieces. Royal Rumble draws Bret and Perfect on the same frame
indices and coordinates (812 of 828 frames share their bounding-box origin), so a Raw Bret piece whose silhouette
matches a Royal Bret frame can be replaced by Royal Perfect's frame at the same index, placed by the same
transform. This tool measures, per Raw piece:

- the best Royal Bret frame (index >= 16; lower indices are shadows) and facing, by silhouette IoU;
- the placement (flip, dx, dy) mapping Royal coordinates onto the Raw piece;
- colour-role agreement at that placement (Royal colours mapped to Raw Bret's palette);
- the hash of the adapted piece as the importer renders it today (used to detect user edits on upgrade).

Acceptance: IoU >= 0.95, or IoU >= 0.88 with colour agreement >= 0.6 (reviewed visually, see
docs/complete-wrestler-art.md). A Royal Perfect frame drawn only from tiles Royal Bret's frame also uses is
generic art (Royal recolours it by palette, e.g. brown hair on Perfect) and is never accepted. Output holds frame indices and metrics only, no pixels.

    python3 tools/match_perfect_poses.py RAW.sfc ROYAL.sfc ROYAL_WRAM.bin --output data/perfect-pose-matches.json
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

import royal_rumble_sprites as royal
from raw_parts import resolve_index, raster, palette

ADAPTED_COLOURS = [0, 1, 4, 8, 4, 8, 13, 2, 14, 7, 6, 3, 2, 15, 14, 11]   # editor/royal-import-core.js
THRESHOLDS = {'iou': 0.95, 'iou_with_colour': 0.88, 'colour': 0.6}


def accepted(iou, colour, shared):
    return not shared and (iou >= THRESHOLDS['iou'] or (iou >= THRESHOLDS['iou_with_colour'] and colour >= THRESHOLDS['colour']))


def generic_frames(royal_rom, royal_wram):
    """Royal indices whose Perfect frame uses no tile of its own (all shared with Bret's frame)."""
    perfect, bret = royal.catalog(royal_rom, royal_wram, 1), royal.catalog(royal_rom, royal_wram, 3)
    tiles = lambda f: {r['source'] for p in f['parts'] for r in p['refs']}
    return {i for i in range(len(perfect)) if tiles(perfect[i]) and tiles(perfect[i]) <= tiles(bret[i])}


def fnv(points):
    """FNV-1a over 'x,y,v;' in (y, x) order; editor/royal-import-core.js computes the same value."""
    h = 0x811c9dc5
    for (x, y), v in sorted(points.items(), key=lambda p: (p[0][1], p[0][0])):
        for c in f'{x},{y},{v};'.encode():
            h = ((h ^ c) * 0x01000193) & 0xffffffff
    return h


def grid(points):
    xs = [x for x, y in points]; ys = [y for x, y in points]
    left, top = min(xs), min(ys)
    m = np.zeros((max(ys) - top + 1, max(xs) - left + 1), np.int16)
    for (x, y), v in points.items():
        m[y - top, x - left] = v
    return m, left, top


def place(points, flip, dx, dy):
    """Royal frame coordinates -> Raw piece coordinates."""
    return {((dx - x) if flip else (x + dx), y + dy): v for (x, y), v in points.items()}


def match(raw_rom, royal_rom, royal_wram):
    bret = royal.catalog(royal_rom, royal_wram, 3)
    generic = generic_frames(royal_rom, royal_wram)
    rgb = lambda c: [c >> s & 31 for s in (0, 5, 10)]
    rc = [int.from_bytes(royal_rom[0x17c26 + 3 * 32 + i * 2:0x17c28 + 3 * 32 + i * 2], 'little') for i in range(16)]
    tp = palette(raw_rom, 1)
    cmap = [0] + [min(range(1, 16), key=lambda j: sum((a - b) ** 2 for a, b in zip(rgb(c), rgb(tp[j])))) for c in rc[1:]]
    cands = []
    for f in bret:
        if f['index'] < 16:
            continue
        pts = {k: cmap[v] for k, v in royal.raster(f).items()}
        if len(pts) < 20:
            continue
        m, left, top = grid(pts)
        for flip in (False, True):
            g = m[:, ::-1] if flip else m
            cands.append((f['index'], flip, (g > 0).astype(np.float32), g, left, top, m.shape[1]))
    rows = []
    for kind, n in (('primary', 998), ('secondary', 722)):
        for i in range(n):
            pts = raster(resolve_index(raw_rom, 1, kind, i)['parts'])
            row = {'kind': kind, 'index': i, 'adapted_hash': fnv({k: ADAPTED_COLOURS[v] for k, v in pts.items()})}
            if not pts:
                rows.append(row); continue
            a, al, at = grid(pts)
            am = (a > 0).astype(np.float32); area = am.sum()
            best = None
            for idx, flip, bm, g, left, top, width in cands:
                if abs(bm.sum() - area) > 0.4 * area:
                    continue
                c = fftconvolve(bm, am[::-1, ::-1], mode='full')
                k = np.argmax(c); inter = c.flat[k]
                iou = inter / (bm.sum() + area - inter)
                if best is None or iou > best[0]:
                    oy, ox = np.unravel_index(k, c.shape)
                    best = (float(iou), idx, flip, int(ox) - (a.shape[1] - 1), int(oy) - (a.shape[0] - 1), g, left, top, width)
            if best is None:
                rows.append(row); continue
            iou, idx, flip, ox, oy, g, left, top, width = best
            # Raw grid (y, x) sits on Royal grid (y + oy, x + ox). Royal grid column X is Royal x = left + X, or
            # left + width - 1 - X when flipped. Express as Raw x = dx +/- Royal x.
            dy = at - oy - top
            dx = (al - ox + left + width - 1) if flip else (al - ox - left)
            agree = tot = 0
            for y in range(a.shape[0]):
                for x in range(a.shape[1]):
                    if a[y, x]:
                        Y, X = y + oy, x + ox
                        if 0 <= Y < g.shape[0] and 0 <= X < g.shape[1] and g[Y, X]:
                            tot += 1; agree += int(a[y, x] == g[Y, X])
            colour = agree / max(tot, 1)
            # Self-check: the placed Royal Bret frame overlaps the Raw piece with the measured IoU.
            placed = place(royal.raster(bret[idx]), flip, dx, dy)
            check = len(set(placed) & set(pts)) / len(set(placed) | set(pts))
            if abs(check - iou) > 0.002:
                raise ValueError(f'Placement check failed for {kind}/{i}: {check:.3f} vs {iou:.3f}')
            row.update(royal_index=idx, flip=flip, dx=dx, dy=dy, iou=round(iou, 3), colour=round(colour, 3),
                       generic=idx in generic, accepted=accepted(iou, colour, idx in generic))
            rows.append(row)
        print(kind, 'done', flush=True)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('raw_rom', type=Path); p.add_argument('royal_rom', type=Path); p.add_argument('royal_wram', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    rows = match(a.raw_rom.read_bytes(), a.royal_rom.read_bytes(), a.royal_wram.read_bytes())
    a.output.write_text(json.dumps({'version': 1, 'thresholds': THRESHOLDS, 'rows': rows}, separators=(',', ':')) + '\n')
    print({'pieces': len(rows), 'matched': sum('royal_index' in r for r in rows),
           'accepted': sum(r.get('accepted', False) for r in rows)})


if __name__ == '__main__':
    main()
