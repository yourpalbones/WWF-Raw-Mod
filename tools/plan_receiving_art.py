"""Plan receiving drawings that follow a Royal pose but are painted with each wrestler's own Raw art.

Raw draws every worker on a shared base body: the same frame-part index shows the same body position in every
slot (silhouette agreement 0.94-0.98 across the stock roster). So a Royal receiving pose can be rebuilt from
Raw parts: cover the donor's drawing with the parts of its Raw counterpart that match it best (exact
colour-role agreement; Raw palette indices have the same role in every slot), then let any target slot draw
those same part indices. The target's own head, hair, skin and gear appear, including gear identities and
user edits, because the parts are resolved from the user's ROM at install time.

Output (data/receiving-art.json) holds only part IDs, flips and offsets for each donor pose; no pixels. Pixels
that no Raw part covers are filled from the donor drawing by colour role ('donor_fill').

    python3 tools/plan_receiving_art.py RAW_ROM ROYAL_ROM [--donor 3:1 ...] [--output data/receiving-art.json]
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

from raw_parts import resolve_part, raster, palette
from inspect_rom import tile
from royal_rumble_sprites import decode_tile

ROOT = Path(__file__).resolve().parents[1]
RAW_SHA256 = '0af7b0d3022acd24a1fb15865a076519f7f56e7a4b33f12b6d851b3a91e5388c'
ROYAL_SHA256 = '51c53e36ed0b959b0695fc6ef036fa7302d1c995eca35c28261d6f3cb77df0ca'
# Royal selector -> Raw counterpart slot (same identity in both games).
COUNTERPARTS = {3: 1, 2: 2, 9: 3, 8: 5, 10: 6, 7: 8, 1: 12}
SIZE = 160          # working canvas; canonical origin at (OX, OY)
OX, OY = 80, 120
MAX_PARTS = 4
PREFILTER = 80


def royal_pose(royal, receivers, selector, index, mapping, shift, cache):
    """Donor drawing in canonical facing (mirrored), as Raw counterpart palette indices."""
    out = np.zeros((SIZE, SIZE), np.int8)
    for part in reversed(receivers['workers'][selector]['poses'][index]['parts']):
        s = part['size']
        for y in range(s):
            for x in range(s):
                sx = s - 1 - x if part['hflip'] else x
                sy = s - 1 - y if part['vflip'] else y
                ref = part['refs'][(sy // 8) * (s // 8) + sx // 8]
                if ref is None:
                    continue
                key = tuple(ref)
                if key not in cache:
                    cache[key] = tile(decode_tile(royal, ref[0], bool(ref[1]))[0], 0, 4)
                v = cache[key][sy % 8 * 8 + sx % 8]
                if v:
                    out[OY + part['y'] + y, OX + shift - (part['x'] + x)] = mapping[v]
    return out


def part_image(raw, slot, part_id, flip):
    points = raster(resolve_part(raw, slot, part_id)['parts'], flip=flip)
    if not points:
        return None, None
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, y0 = min(xs), min(ys)
    img = np.zeros((max(ys) - y0 + 1, max(xs) - x0 + 1), np.int8)
    for (x, y), v in points.items():
        img[y - y0, x - x0] = v
    return img, (x0, y0)


def correlate(a, b):
    """Valid-free full cross-correlation of a (canvas) with b (template) via FFT."""
    return fftconvolve(a, b[::-1, ::-1], mode='valid')


def plan_pose(donor, candidates):
    """Greedy cover of the donor drawing by candidate parts. Returns placements and coverage."""
    mask = (donor > 0).astype(np.float32)
    dil = mask.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            dil = np.maximum(dil, np.roll(np.roll(mask, dy, 0), dx, 1))
    onehot = [(donor == v).astype(np.float32) for v in range(16)]
    uncovered = mask.copy()
    placements = []
    total = mask.sum()
    for _ in range(MAX_PARTS):
        best = None
        # Cheap silhouette prefilter (one correlation per candidate), then exact colour-role scoring.
        rough = []
        for c in candidates:
            pmask = c[4]
            if c[5] < 30:
                continue
            fit = correlate(uncovered, pmask) - 1.5 * (c[5] - correlate(dil, pmask))
            rough.append((float(fit.max()), c))
        rough.sort(key=lambda r: -r[0])
        for _, (part_id, flip, img, origin, pmask, n) in rough[:PREFILTER]:
            agree = sum(correlate(onehot[v] * uncovered, (img == v).astype(np.float32)) for v in range(1, 16))
            inside = correlate(dil, pmask)
            fresh = correlate(uncovered, pmask)
            outside = n - inside
            score = 2 * agree - 1.5 * outside - 0.25 * (fresh - agree)
            k = np.unravel_index(np.argmax(score), score.shape)
            if best is None or score[k] > best[0]:
                best = (float(score[k]), part_id, flip, k, float(agree[k]), float(fresh[k]), float(outside[k]), n, img, origin)
        if best is None:
            break
        score, part_id, flip, (ky, kx), agree, fresh, outside, n, img, origin = best
        # Accept only parts that agree on most of what they cover and add real coverage.
        if fresh < 0.08 * total or agree < 0.55 * fresh or outside > 0.25 * n:
            break
        placed = np.zeros_like(uncovered)
        placed[ky:ky + img.shape[0], kx:kx + img.shape[1]] = (img > 0)
        uncovered *= 1 - placed
        placements.append({'part': int(part_id), 'flip': bool(flip), 'x': int(kx - OX - origin[0]),
                           'y': int(ky - OY - origin[1]), 'agreement': round(float(agree / max(fresh, 1)), 3),
                           'covered': round(float(fresh / total), 3)})
    return placements, round(1 - float(uncovered.sum() / total), 3) if total else 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('raw', type=Path)
    parser.add_argument('royal', type=Path)
    parser.add_argument('--donor', action='append', help='ROYAL_SELECTOR:RAW_SLOT (default: all counterparts)')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/receiving-art.json')
    args = parser.parse_args()
    raw, royal = args.raw.read_bytes(), args.royal.read_bytes()
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or hashlib.sha256(royal).hexdigest() != ROYAL_SHA256:
        raise SystemExit('Expected the unmodified WWF Raw and Royal Rumble USA ROMs')
    receivers = json.loads((ROOT / 'data/perfect-receivers.json').read_text())
    shift = receivers['canonical']['mirror_shift']
    donors = [tuple(map(int, d.split(':'))) for d in args.donor] if args.donor else list(COUNTERPARTS.items())
    out = json.loads(args.output.read_text()) if args.output.exists() else {}
    out.update({'generated_by': 'tools/plan_receiving_art.py', 'canvas_origin': [OX, OY], 'method': __doc__.split('\n\n')[1]})
    out.setdefault('donors', {})
    word = lambda d, a: d[a] | d[a + 1] << 8
    cb = lambda c: [c >> s & 31 for s in (0, 5, 10)]
    for selector, slot in donors:
        colors = [word(royal, 0x17C26 + selector * 32 + i * 2) for i in range(16)]
        target = palette(raw, slot)
        mapping = [0] + [min(range(1, 16), key=lambda j: sum((a - b) ** 2 for a, b in zip(cb(c), cb(target[j]))))
                         for c in colors[1:]]
        candidates = []
        for part_id in [i * 3 for i in range(998)] + [0x8000 | i * 3 for i in range(722)]:   # profile IDs
            for flip in (False, True):
                try:
                    img, origin = part_image(raw, slot, part_id, flip)
                except ValueError:
                    continue
                if img is not None:
                    pmask = (img > 0).astype(np.float32)
                    candidates.append((part_id, flip, img, origin, pmask, float(pmask.sum())))
        cache, poses = {}, []
        for index in range(len(receivers['workers'][selector]['poses'])):
            donor = royal_pose(royal, receivers, selector, index, mapping, shift, cache)
            placements, coverage = plan_pose(donor, candidates)
            poses.append({'pose': index, 'parts': placements, 'own_art_coverage': float(coverage)})
            print(selector, slot, index, coverage, [(p['part'], p['flip'], p['agreement']) for p in placements], flush=True)
        out['donors'][str(selector)] = {'counterpart_slot': slot, 'colour_map': mapping, 'poses': poses}
    args.output.write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
