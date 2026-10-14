"""Give Mr. Perfect's remaining Bret-drawn pieces Royal Perfect's own head.

Some of Raw's Bret drawings that Mr. Perfect's slot reuses have no Royal Perfect counterpart (poses Raw added). They
kept Bret's head, with the dark hair recoloured blond, which reads as Bret with yellow dots. Royal Rumble draws Bret
and Perfect on the same frame indices, in the same pose and at the same coordinates, so Royal is a book of paired
examples: Bret's head in a pose, and Perfect's head in that pose. For each such piece:

1. the head window is Bret's hair (tools/convert_perfect_poses.hair_changes finds it) plus 4 pixels on every side;
2. the source is the Royal Bret frame, in either facing, whose pixels in that window agree best with the piece
   (Royal Bret's colours mapped to the piece's palette, as the importer adapts Raw Bret's), searched within 6
   pixels of the alignment of the two hair centres; the score is agreeing pixels over the union of both drawings
   in the window;
3. inside the window, a pixel where the piece agrees with Royal Bret takes Royal Perfect's pixel at the same place,
   or none where Perfect draws nothing; Bret's hair where Royal Bret has something else takes Royal Perfect's pixel
   or none; where Royal Perfect draws more than Bret (fuller hair) and the piece is empty, Perfect's pixel is
   added. Outside the window, and wherever the piece differs from Royal Bret (an arm across the face), the piece
   stays as Raw draws it.

The output holds Royal frame indices, offsets and scores only; the importer applies the same rule to the user's
ROMs (editor/royal-import-core.js headRebuild).

    python3 tools/rebuild_perfect_heads.py RAW.sfc ROYAL.sfc ROYAL_WRAM.bin --output data/perfect-head-sources.json

Pieces listed in data/perfect-head-review.json 'rejected' (reviewed visually) keep the hair recolour.
"""
import argparse
import json
from pathlib import Path

import numpy as np

import royal_rumble_sprites as royal
from convert_perfect_poses import hair_changes
from raw_parts import resolve_index, raster, palette

ROOT = Path(__file__).resolve().parents[1]
ADAPTED_COLOURS = [0, 1, 4, 8, 4, 8, 13, 2, 14, 7, 6, 3, 2, 15, 14, 11]   # Raw Bret index -> Perfect palette
PAD, SEARCH = 4, 6
REVIEW = ROOT / 'data/perfect-head-review.json'


def colours(raw_rom, royal_rom):
    """Royal Bret palette index -> the adapted palette (via the nearest Raw Bret colour)."""
    c5 = lambda c: [c >> s & 31 for s in (0, 5, 10)]
    royal_bret = [int.from_bytes(royal_rom[0x17c26 + 3 * 32 + i * 2:0x17c28 + 3 * 32 + i * 2], 'little') for i in range(16)]
    raw_bret = palette(raw_rom, 1)
    nearest = [0] + [min(range(1, 16), key=lambda j: sum((a - b) ** 2 for a, b in zip(c5(c), c5(raw_bret[j]))))
                     for c in royal_bret[1:]]
    return [ADAPTED_COLOURS[v] for v in nearest]


def frame_points(points, flip, mapping=None):
    return {((-x) if flip else x, y): (mapping[v] if mapping else v) for (x, y), v in points.items()}


def hair(points):
    return {p for p, v in hair_changes(points).items() if v == 13}


def bbox(points):
    xs = [x for x, y in points]; ys = [y for x, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def grid(points, box):
    x0, y0, x1, y1 = box
    g = np.zeros((y1 - y0 + 1, x1 - x0 + 1), np.int16)
    for (x, y), v in points.items():
        if x0 <= x <= x1 and y0 <= y <= y1:
            g[y - y0, x - x0] = v
    return g


BLOND = {9, 13}       # Royal Perfect's hair colours


def sources(perfect, bret, mapping, generic):
    """[(index, flip, Royal Bret points (adapted colours), its hair)] for frames both workers draw. A generic Perfect
    frame (drawn with Bret's own tiles, recoloured by palette) has brown hair, so it is never a source; nor is a
    frame where Perfect's blond hair does not show."""
    out = []
    for k, points in bret.items():
        if k < 16 or k not in perfect or k in generic:
            continue
        if sum(v in BLOND for v in perfect[k].values()) < 12:
            continue
        for flip in (False, True):
            b = frame_points(points, flip, mapping)
            h = hair(b)
            if len(h) >= 6:
                out.append((k, flip, b, h))
    return out


def search(piece, frames, top=5):
    """(window, [(score, index, flip, dx, dy)]): Royal pixel (x + dx, y + dy) lies on piece pixel (x, y)."""
    h = hair(piece)
    if len(h) < 4:
        return None, []
    x0, y0, x1, y1 = bbox(h)
    window = (x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD)
    g = grid(piece, window)
    filled = g > 0
    rows, cols = g.shape
    ranked = []
    for k, flip, b, bh in frames:
        hx0, hy0, hx1, hy1 = bbox(bh)
        cx = round((hx0 + hx1) / 2 - (x0 + x1) / 2)
        cy = round((hy0 + hy1) / 2 - (y0 + y1) / 2)
        big = grid(b, (window[0] + cx - SEARCH, window[1] + cy - SEARCH, window[2] + cx + SEARCH, window[3] + cy + SEARCH))
        best = None
        for oy in range(2 * SEARCH + 1):
            for ox in range(2 * SEARCH + 1):
                r = big[oy:oy + rows, ox:ox + cols]
                score = ((r == g) & filled).sum() / max(((r > 0) | filled).sum(), 1)
                if best is None or score > best[0]:
                    best = (float(score), cx - SEARCH + ox, cy - SEARCH + oy)
        ranked.append((round(best[0], 4), k, flip, best[1], best[2]))
    ranked.sort(key=lambda r: (-r[0], r[1], r[2]))
    return window, ranked[:top]


def rebuild(piece, window, bret, perfect, dx, dy):
    """The piece with Royal Perfect's head (see the module docstring). bret, perfect: Royal frame points in the
    source's facing (bret in adapted colours)."""
    h = hair(piece)
    out = dict(piece)
    x0, y0, x1, y1 = window
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            p, q = (x, y), (x + dx, y + dy)
            b, r, v = piece.get(p), bret.get(q), perfect.get(q)
            if (b and r == b) or (b and p in h):
                if v:
                    out[p] = v
                else:
                    out.pop(p, None)
            elif not b and v and not r:
                out[p] = v
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('raw', type=Path); p.add_argument('royal', type=Path); p.add_argument('royal_wram', type=Path)
    p.add_argument('--manifest', type=Path, default=ROOT / 'editor/royal-import-layouts.js')
    p.add_argument('--output', type=Path, default=ROOT / 'data/perfect-head-sources.json')
    a = p.parse_args()
    raw_rom, royal_rom, wram = a.raw.read_bytes(), a.royal.read_bytes(), a.royal_wram.read_bytes()
    text = a.manifest.read_text()
    manifest = json.loads(text[text.index('=') + 1:text.rindex(';')])
    mapping = colours(raw_rom, royal_rom)
    perfect = {f['index']: royal.raster(f) for f in royal.catalog(royal_rom, wram, 1)}
    bret = {f['index']: royal.raster(f) for f in royal.catalog(royal_rom, wram, 3)}
    from match_perfect_poses import generic_frames
    frames = sources(perfect, bret, mapping, generic_frames(royal_rom, wram))
    rows = {}
    for f in manifest['frames']:
        if f['royal'] or f['kind'] != 'primary':     # heads are drawn in upper-body pieces
            continue
        piece = {k: ADAPTED_COLOURS[v] for k, v in raster(resolve_index(raw_rom, 1, f['kind'], f['index'])['parts']).items()}
        window, ranked = search(piece, frames)
        if ranked:
            score, k, flip, dx, dy = ranked[0]
            rows[f"{f['kind'][0]}{f['index']}"] = {'royal_index': k, 'flip': flip, 'dx': dx, 'dy': dy, 'window': list(window),
                                                  'score': score, 'alternatives': [list(r) for r in ranked[1:]]}
    a.output.write_text(json.dumps({'method': __doc__.split('\n\n')[0], 'colours': mapping, 'pad': PAD, 'search': SEARCH,
                                    'rows': rows}, indent=1) + '\n')
    print(len(rows), 'pieces with a Royal Perfect head source')


if __name__ == '__main__':
    main()
