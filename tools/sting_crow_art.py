"""Crow Sting, alternate art pass: Raw-styled Crow makeup and scorpion shirt on the native Undertaker donor.

This is a second, independent take on the Sting gear (the current one is tools/sting_rebuild_art.py, kept as is). It
keeps more of Raw's own drawing:
- Hair stays the donor's hand-drawn long hair, darkened through the palette (its dithering and highlights remain),
  instead of a flat black silhouette.
- The face is repainted inside the donor's own face: white paint with a grey shadow side, and the Crow marks as thin
  lines (brow points, eyes, cheek streaks, lips and chin lines). The donor's beard is painted over.
- Gloves and boots are black, with the shirt's own highlight; trousers lose their stripe; skin is a natural tan.
- The scorpion is a three-tone grey skeleton (pincers, segmented spine, ribs, tail) on front-facing shirts.

Head positions come from the registration in data/sting-rebuild-heads.json (templates, transforms and landmarks
from the earlier Sting work). The front and walking-profile faces are drawn explicitly (FACE_GRIDS); other heads
with landmarks get the same makeup placed from their landmarks; the few heads without landmarks keep the earlier
authored paint, in this palette. Pixels are only written where the donor drawing already has a pixel, so every
silhouette stays Raw's.

    from sting_crow_art import author, PALETTE
"""
from functools import lru_cache
import json
from pathlib import Path

from scott_frame_catalog import raster
from build_scott_hall_gear import components

ROOT = Path(__file__).resolve().parents[1]
SKIN = {7, 11, 12, 15}
HAIR = {9, 10}
BLACK, CLOTH_DARK, CLOTH, CLOTH_LIGHT = 1, 2, 3, 6
WHITE, PAINT_SHADOW = 5, 13
SCORPION_DARK, SCORPION_MID, SCORPION_LIGHT = 4, 14, 8


def bgr(r, g, b):
    return (r >> 3) | (g >> 3) << 5 | (b >> 3) << 10


# Slot palette (index: BGR555). Donor roles kept: 1 outline, 2/3/6 shirt and trousers, 7/11/12/15 skin, 9/10 hair.
PALETTE = {1: bgr(0, 0, 0), 2: bgr(10, 10, 14), 3: bgr(30, 30, 36), 4: bgr(104, 104, 112), 5: bgr(240, 240, 232),
           6: bgr(58, 58, 68), 7: bgr(184, 120, 80), 8: bgr(224, 224, 228), 9: bgr(20, 14, 12), 10: bgr(48, 32, 24),
           11: bgr(216, 160, 116), 12: bgr(136, 80, 52), 13: bgr(168, 168, 176), 14: bgr(160, 160, 168),
           15: bgr(240, 192, 148)}
# Donor colours folded into the outfit, freeing 4, 5, 8, 13 and 14: the trouser stripe (4, 5) and the purple gloves
# and boots (8 base, 13 shadow, 14 highlight).
REMAP = {4: CLOTH_DARK, 5: CLOTH, 8: CLOTH_DARK, 13: BLACK, 14: CLOTH}
CODES = {'K': BLACK, 'W': WHITE, 'G': PAINT_SHADOW, 'h': 9, 'H': 10}

# Explicit faces in template coordinates: origin (x, y) of the first character; '_' keeps the donor pixel.
FACE_GRIDS = {
    'front': ((-4, -38), ['_WWWWW_',
                          'WKWWWKG',
                          'WKKWKKG',
                          'WKWGWKG',
                          'GWWGWWG',
                          'GWWWWWG',
                          '_WKKKG_',
                          '_GKWKG_',
                          '_GWWWG_',
                          '__GGG__']),
    'profile-walking': ((4, -38), ['_WW___',
                                   'WWWWW_',
                                   'WWWKW_',
                                   'GWKKW_',
                                   'GWKKW_',
                                   'GWKWW_',
                                   'GWWWW_',
                                   'GWWKK_',
                                   '_GWKW_',
                                   '__GWK_']),
    'profile': ((6, -39), ['_WW___',
                           'WWWWW_',
                           'WWKWW_',
                           'GWKKW_',
                           'GWWKW_',
                           'GWWWW_',
                           'GWWKK_',
                           '_GWKW_',
                           '__GWK_']),
    'up-angled': ((-8, -28), ['GWWW___',
                              'WWWWW__',
                              'WKWKK__',
                              '_WKWKWW',
                              '_GWWWWW',
                              '__GWKKK',
                              '___GWK_']),
}
# Three-tone scorpion skeleton: pincers, carapace, segmented spine, ribs and tail ('l' light, 'm' mid, 'd' dark).
SCORPION = ['l...........l',
            'll.........ll',
            '.lm.......ml.',
            '..lm.....ml..',
            '...mm.l.mm...',
            '.....lml.....',
            '..dmd.l.dmd..',
            '.d...mlm...d.',
            '..dmd.l.dmd..',
            '.d...mlm...d.',
            '..dmd.l.dmd..',
            '.....mlm.....',
            '......l......',
            '......m......',
            '.......l.....']
SCORPION_CODES = {'l': SCORPION_LIGHT, 'm': SCORPION_MID, 'd': SCORPION_DARK}
# Front-facing shirts (reviewed in the earlier pass) and the sideways ones among them.
FRONT_TORSOS = {*range(1, 9), 16, 17, 18, 19, 20, 24, 33, 34, 35, 36, 37, 38, 47, 48}
SIDEWAYS = {18, 19, 20}
# Shared submission bodies with a low neckline: the shirt is filled inside these torso regions (earlier review).
SUBMISSION_TORSOS = {('primary', 623): [-4, -28, 6, -14], ('primary', 732): [-13, -61, -2, -48],
                     ('primary', 737): [-15, -39, -4, -28], ('primary', 738): [-1, -22, 5, -12],
                     ('secondary', 617): [0, -65, 6, -52], ('secondary', 618): [0, -65, 6, -52],
                     ('secondary', 619): [-6, -50, 1, -39], ('secondary', 620): [-6, -48, 3, -36],
                     ('secondary', 621): [-6, -40, 3, -28], ('secondary', 622): [1, -53, 6, -42],
                     ('secondary', 628): [-6, -40, 3, -28]}


@lru_cache(maxsize=1)
def atlas():
    return json.loads((ROOT / 'data/sting-rebuild-heads.json').read_text())


def author(frame):
    """{tile field: 64 palette indices} for one donor frame (scott_frame_catalog.catalog row)."""
    if len({v for part in frame['parts'] for ref in part['refs'] for v in ref['pixels'] if v}) <= 1:
        # Shadows are single-colour pieces drawn with the shared shadow palette: their index is its colour there.
        return {ref['field']: list(ref['pixels']) for part in frame['parts'] for ref in part['refs']}
    changes = {ref['field']: [REMAP.get(v, v) for v in ref['pixels']] for part in frame['parts'] for ref in part['refs']}
    points, mapping = raster(frame)

    def put(q, v):
        if q in mapping:
            ref, k = mapping[q]
            changes[ref['field']][k] = v

    key = (frame['kind'], frame['index'])
    identifier = str(frame['index']) if frame['kind'] == 'primary' else f"secondary:{frame['index']}"
    entry = atlas()['heads'].get(identifier)
    if entry:
        name = entry['template']
        template = atlas()['templates'][name]
        sx, sy, dx, dy = entry['transform']
        world = lambda x, y: (sx * x + dx, sy * y + dy)
        if name in FACE_GRIDS:
            (ox, oy), rows = FACE_GRIDS[name]
            for j, row in enumerate(rows):
                for i, c in enumerate(row):
                    if c != '_':
                        put(world(ox + i, oy + j), CODES[c])
        elif template.get('landmarks'):
            makeup(points, put, template, world)
        else:
            # Earlier authored paint, in this palette (its near-black hair 14 is hair here); no pixel is added.
            for x, y, value in template.get('paint', []):
                q = world(x, y)
                if value and q in points:
                    put(q, 9 if value == 14 else value)

    if frame['kind'] == 'primary' and frame['index'] in FRONT_TORSOS:
        garments = components(points, {2, 3, 6})
        if garments:
            cloth = max(garments, key=len)
            l, r = min(x for x, _ in cloth), max(x for x, _ in cloth)
            t, b = min(y for _, y in cloth), max(y for _, y in cloth)
            if len(cloth) >= 45 and r - l >= 7 and b - t >= 7:
                sideways = frame['index'] in SIDEWAYS and r - l > b - t + 4
                h, w = len(SCORPION), len(SCORPION[0])
                width, height = (h, w) if sideways else (w, h)
                ox, oy = (l + r - width + 1) // 2, (t + b - height + 1) // 2
                for y, row in enumerate(SCORPION):
                    for x, c in enumerate(row):
                        q = (ox + y, oy + w - 1 - x) if sideways else (ox + x, oy + y)
                        if c != '.' and q in cloth:
                            put(q, SCORPION_CODES[c])

    torso = SUBMISSION_TORSOS.get(key)
    if torso:
        l, t, r, b = torso
        for q, v in points.items():
            if l <= q[0] <= r and t <= q[1] <= b and v in SKIN:
                put(q, CLOTH_DARK if v in {7, 12} else CLOTH)
    return changes


def makeup(points, put, template, world):
    """Crow makeup on a registered head from its landmarks: the face (skin and beard between the eyes and the jaw)
    becomes white paint, shaded where the donor skin was dark; eyes, a brow point and a cheek streak above and below
    each eye, the lips and a chin line are black."""
    lm = template['landmarks']
    points_of = lambda k: [world(*p) for p in ([lm[k]] if lm.get(k) and isinstance(lm[k][0], int) else lm.get(k, []))]
    eyes, mouth, jaw = points_of('eyes'), points_of('mouth'), points_of('jaw')
    if not eyes or not mouth:
        return
    ex = sum(x for x, _ in eyes) / len(eyes); ey = sum(y for _, y in eyes) / len(eyes)
    mx = sum(x for x, _ in mouth) / len(mouth); my = sum(y for _, y in mouth) / len(mouth)
    length = max(((mx - ex) ** 2 + (my - ey) ** 2) ** 0.5, 1.0)
    down = ((mx - ex) / length, (my - ey) / length)
    side = (-down[1], down[0])
    reach = max(((x - ex) * down[0] + (y - ey) * down[1]) for x, y in jaw + mouth) + 0.5
    l, t, r, b = template['box']
    corners = [world(l, t), world(r, b)]
    x0, x1 = sorted(c[0] for c in corners); y0, y1 = sorted(c[1] for c in corners)
    face = set()
    for (x, y), v in points.items():
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        along = (x - ex) * down[0] + (y - ey) * down[1]
        across = abs((x - ex) * side[0] + (y - ey) * side[1])
        if -3.5 <= along <= reach and across <= 4.5 and (v in SKIN or (v in HAIR and along >= 1)):
            face.add((x, y))
    for q in face:
        put(q, PAINT_SHADOW if points[q] == 12 else WHITE)
    step = (round(down[0]), round(down[1]))
    for x, y in eyes:
        for k in (-1, 0, 1):
            q = (x + step[0] * k, y + step[1] * k)
            if q in points:
                put(q, BLACK)
    for q in mouth:
        if q in points:
            put(q, BLACK)
    centre = (round(mx) + step[0], round(my) + step[1])
    if centre in points:
        put(centre, BLACK)
