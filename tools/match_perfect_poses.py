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
    python3 tools/match_perfect_poses.py RAW.sfc ROYAL.sfc ROYAL_WRAM.bin --output data/perfect-pose-matches.json --semantic

Semantic pass (--semantic, reads the existing output): many of Raw's Bret drawings are Raw redraws or insertions with
no exact Royal silhouette (Raw's idle stance, for one), so they stayed Bret. Raw's piece tables follow Royal's frame
order (matched pairs run in step: primary pieces with Royal upper-body frames, secondary with lower-body frames).
For each remaining piece in Bret's own range, the candidates are the Royal Perfect frames of the nearest accepted
neighbours in Raw's order, placed with the neighbour's own measured transform (Raw draws a wrestler's pieces about one
body origin), and any unused Royal frame between them, placed at its best overlap. The best overlap wins; the review
file (data/perfect-pose-review.json) holds the acceptance threshold and every rejection or override, decided by
looking at each piece and the composites that use it. Shadows and the common range are left alone.
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
OWN = {'primary': 527, 'secondary': 426}        # Bret's own range; higher indices resolve through the common table
REVIEW = Path(__file__).resolve().parents[1] / 'data/perfect-pose-review.json'


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


def best_placement(target, points):
    """Best-overlap placement of Royal points on a Raw piece: (iou, flip, dx, dy), Raw = place(points, flip, dx, dy)."""
    a, al, at = grid(target)
    am = (a > 0).astype(np.float32)
    best = None
    for flip in (False, True):
        b, bl, bt = grid({((-x) if flip else x, y): v for (x, y), v in points.items()})
        bm = (b > 0).astype(np.float32)
        c = fftconvolve(bm, am[::-1, ::-1], mode='full')
        k = int(np.argmax(c)); inter = float(c.flat[k])
        oy, ox = np.unravel_index(k, c.shape)
        ox, oy = int(ox) - (a.shape[1] - 1), int(oy) - (a.shape[0] - 1)
        iou = inter / float(am.sum() + bm.sum() - inter)
        if best is None or iou > best[0]:
            best = (iou, flip, al - bl - ox, at - bt - oy)
    return best


def overlap(a, b):
    a, b = set(a), set(b)
    return len(a & b) / max(1, len(a | b))


def head(points, hair):
    """Hair centroid normalised to the bounding box, or None when fewer than 8 hair pixels show."""
    xs = [x for x, y in points]; ys = [y for x, y in points]
    hp = [p for p, v in points.items() if v in hair]
    if len(hp) < 8:
        return None
    return ((sum(x for x, y in hp) / len(hp) - min(xs)) / max(1, max(xs) - min(xs)),
            (sum(y for x, y in hp) / len(hp) - min(ys)) / max(1, max(ys) - min(ys)))


BRET_HAIR, PERFECT_HAIR = {9}, {9, 12, 13}     # Raw Bret palette index; Royal Perfect palette indices (torso frames)


def semantic(rows, raw_rom, royal_rom, royal_wram, spread=2):
    """Royal Perfect counterparts for pieces with no exact Royal silhouette (see the module docstring)."""
    perfect = royal.catalog(royal_rom, royal_wram, 1)
    generic = generic_frames(royal_rom, royal_wram)
    anchors = {kind: sorted((r['index'], r) for r in rows if r['kind'] == kind and r.get('accepted') and r['index'] < OWN[kind])
               for kind in OWN}
    used = {r['royal_index'] for kind in OWN for _, r in anchors[kind]}
    # Upper or lower body: the kind of Raw piece each Royal frame best resembles (IoU >= 0.6). Frames of unknown or
    # mixed kind are never candidates, so a pair of legs cannot become a torso.
    votes = {}
    for r in rows:
        if r.get('royal_index') is not None and r['iou'] >= 0.6:
            votes.setdefault(r['royal_index'], {}).setdefault(r['kind'], 0)
            votes[r['royal_index']][r['kind']] += 1
    kind_of = {k: next(iter(v)) for k, v in votes.items() if len(v) == 1}
    for r in rows:
        kind, i = r['kind'], r['index']
        r.pop('semantic', None)
        if r.get('accepted') or i >= OWN[kind]:
            continue
        target = raster(resolve_index(raw_rom, 1, kind, i)['parts'])
        if len(set(target.values())) <= 1:          # empty or a shadow
            continue
        below = [a for j, a in anchors[kind] if j < i][-spread:]
        above = [a for j, a in anchors[kind] if j > i][:spread]
        options = []
        for a in below + above:
            pts = place(royal.raster(perfect[a['royal_index']]), a['flip'], a['dx'], a['dy'])
            options.append((overlap(target, pts), a['royal_index'], a['flip'], a['dx'], a['dy'], f"neighbour {kind[0]}{a['index']}"))
        if below and above:
            lo, hi = sorted((below[-1]['royal_index'], above[0]['royal_index']))
            for k in range(lo + 1, hi):
                if k < 16 or k in used or k in generic or len(royal.raster(perfect[k])) < 20:
                    continue
                iou, flip, dx, dy = best_placement(target, royal.raster(perfect[k]))
                options.append((iou, k, flip, dx, dy, 'between'))
        area = len(target)
        options = [o for o in options if kind_of.get(o[1]) == kind
                   and 0.6 <= len(royal.raster(perfect[o[1]])) / area <= 1.6]
        # A torso must keep its head where Raw draws it: rolled or inverted Raw drawings can overlap an upright
        # Royal torso well and still put the head on the wrong side.
        if kind == 'primary' and head(target, BRET_HAIR):
            ha = head(target, BRET_HAIR)
            def same_head(o):
                hb = head(place(royal.raster(perfect[o[1]]), o[2], o[3], o[4]), PERFECT_HAIR)
                return hb is None or ((ha[0] - hb[0]) ** 2 + (ha[1] - hb[1]) ** 2) ** 0.5 <= 0.35
            options = [o for o in options if same_head(o)]
        # A neighbour's frame keeps Raw's own body origin; an in-between frame must be clearly better to win.
        ranked = [(o[0] + (0.1 if o[5].startswith('neighbour') else 0), o) for o in options]
        if ranked:
            iou, k, flip, dx, dy, source = max(ranked, key=lambda t: t[0])[1]
            r['semantic'] = {'royal_index': k, 'flip': bool(flip), 'dx': int(dx), 'dy': int(dy), 'iou': round(iou, 3), 'source': source}
    return rows


def effective(rows, review=None):
    """Rows the converter replaces with Royal Perfect art: accepted silhouette matches, plus semantic counterparts at or
    above the review threshold that were not rejected (overrides replace the automatic choice)."""
    review = review if review is not None else (json.loads(REVIEW.read_text()) if REVIEW.exists() else {})
    rejected, overrides = set(review.get('rejected', [])), review.get('overrides', {})
    out = []
    for r in rows:
        if r.get('accepted'):
            out.append(r); continue
        name = f"{r['kind'][0]}{r['index']}"
        s = overrides.get(name) or r.get('semantic')
        if s and name not in rejected and (name in overrides or s['iou'] >= review.get('threshold', 1)):
            out.append({**r, 'royal_index': s['royal_index'], 'flip': s['flip'], 'dx': s['dx'], 'dy': s['dy'],
                        'accepted': True, 'semantic': True})
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('raw_rom', type=Path); p.add_argument('royal_rom', type=Path); p.add_argument('royal_wram', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--semantic', action='store_true', help='add the semantic pass to an existing output')
    a = p.parse_args()
    raw_rom, royal_rom, royal_wram = a.raw_rom.read_bytes(), a.royal_rom.read_bytes(), a.royal_wram.read_bytes()
    rows = json.loads(a.output.read_text())['rows'] if a.semantic else match(raw_rom, royal_rom, royal_wram)
    rows = semantic(rows, raw_rom, royal_rom, royal_wram)
    a.output.write_text(json.dumps({'version': 2, 'thresholds': THRESHOLDS, 'rows': rows}, separators=(',', ':')) + '\n')
    print({'pieces': len(rows), 'matched': sum('royal_index' in r for r in rows),
           'accepted': sum(r.get('accepted', False) for r in rows), 'semantic_candidates': sum('semantic' in r for r in rows),
           'effective': len(effective(rows))})


if __name__ == '__main__':
    main()
