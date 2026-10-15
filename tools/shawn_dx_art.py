"""Shawn Michaels in his red DX-era ring gear, on Raw's own Shawn art (slot 8).

Reference: vivid red tights with HBK hearts and DX X straps, the "degeneration X" heart-on-X on the seat, black
boots.

Raw already draws Shawn in full-length tights and laced boots, so most of the look is palette:
- tights (2, 3) vivid red, with Raw's own shading kept (2 is the shade, 3 the lit red);
- 4 and 5 (the side seam on his own pieces, the tights on the game's generic bodies) dark red and red;
- boots: 6 (their shaded body) near-black, so they read as black boots with the white (8) lacing.
The logos are drawn into the pixels, simplified to what reads at the game's scale:
- on each leg a white heart on the thigh and one on the shin, centred across the leg and pointing toward the boot,
  so they follow the leg through every pose (with the X straps where the thigh is wide enough to show them);
- on the seat of the back views, the white heart on a black X;
- on Shawn's own pieces and the generic lower bodies in full tights; pieces with bare legs or someone else's
  clothes (trunk bodies, the man in the red shirt) are left alone.
Only pixels already on the tights change; every silhouette stays Raw's.

    from shawn_dx_art import author, PALETTE
"""
from collections import deque

from scott_frame_catalog import raster


def bgr(r, g, b):
    return (r >> 3) | (g >> 3) << 5 | (b >> 3) << 10


PALETTE = {2: bgr(200, 12, 28), 3: bgr(232, 32, 40), 4: bgr(128, 0, 16), 5: bgr(232, 32, 40), 6: bgr(30, 30, 36),
           8: bgr(248, 248, 248)}
TIGHTS = {2, 3, 4, 5}
SKIN = {7, 9, 10, 11, 12, 15}     # 9/10 shade bare legs on the generic bodies
BOOT = {6, 8}
WHITE, BLACK = 8, 1

# Heart pointing down (its tip toward the boot); W white, X black strap, . untouched.
HEART7 = ['X.....X',      # a white heart; the black X straps show where they cross the tights
          '.XW.WX.',
          '.WWWWW.',
          '.WWWWW.',
          '..WWW..',
          '.X.W.X.',
          'X.....X']
HEART5 = ['.W.W.',
          'WWWWW',
          'WWWWW',
          '.WWW.',
          '..W..']
SEATS = (['XX.....XX',     # the seat of the back view: the heart on the black X (the DX emblem)
          '.XXW.WXX.',
          '..WWWWW..',
          '..WWWWW..',
          '.XXWWWXX.',
          'XX..W..XX'],
         ['X.W.W.X',
          '.XWWWX.',
          '..WWW..',
          '.X.W.X.',
          'X.....X'])
# Shawn's lower-body pieces drawn from behind: plan_back_views() on the original game (fixed here, since Add Mr. Perfect
# adds animation streams that reference more profiles).
BACK_VIEWS = {1, 9, 10, 15, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 85, 87, 88, 89, 90, 91, 107,
              108, 109, 111, 112, 115, 116, 134, 143, 144, 146, 147, 148, 190, 193, 208, 209, 238, 258, 266, 277, 288,
              289, 290, 291, 292, 294, 301, 306, 317, 324, 325, 337, 338, 350, 379, 380, 382, 384, 385, 393, 402, 412,
              413, 414, 415}
HEART3 = ['W.W',
          'WWW',
          '.W.']


def stamp(pattern, tip):
    """{(dx, dy): colour} for the pattern rotated so its tip points along tip=(x, y), centred on (0, 0)."""
    h, w = len(pattern), len(pattern[0])
    out = {}
    for y, row in enumerate(pattern):
        for x, c in enumerate(row):
            if c == '.':
                continue
            dx, dy = x - w // 2, y - h // 2
            if tip == (0, -1):
                dx, dy = dx, -dy
            elif tip == (1, 0):
                dx, dy = dy, dx
            elif tip == (-1, 0):
                dx, dy = -dy, dx
            out[dx, dy] = WHITE if c == 'W' else BLACK
    return out


def legs(points):
    """Split the tights into legs: breadth-first from each boot through tights pixels. Returns a list of
    (distance map {pixel: steps from the boot}, boot centre)."""
    boots = components({q for q, v in points.items() if v in BOOT})
    boots = [b for b in boots if len(b) >= 6]
    owner, dist, queue = {}, {}, deque()
    for n, boot in enumerate(boots):
        for x, y in boot:
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if points.get(q) in TIGHTS and q not in owner:
                    owner[q], dist[q] = n, 1
                    queue.append(q)
    while queue:
        x, y = queue.popleft()
        for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if points.get(q) in TIGHTS and q not in owner:
                owner[q], dist[q] = owner[(x, y)], dist[(x, y)] + 1
                queue.append(q)
    out = []
    for n, boot in enumerate(boots):
        mine = {q: d for q, d in dist.items() if owner[q] == n}
        if mine:
            out.append((mine, (sum(x for x, _ in boot) / len(boot), sum(y for _, y in boot) / len(boot))))
    return out


def components(cells):
    cells, out = set(cells), []
    while cells:
        seed = cells.pop()
        group, queue = {seed}, [seed]
        while queue:
            x, y = queue.pop()
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if q in cells:
                    cells.discard(q)
                    group.add(q)
                    queue.append(q)
        out.append(group)
    return out


def place(leg, boot, at, points, taken):
    """Stamp a logo on the leg at `at` steps from the boot. Returns {pixel: colour} or {}."""
    band = [q for q, d in leg.items() if abs(d - at) <= 1]
    if len(band) < 4:
        return {}
    cx = round(sum(x for x, _ in band) / len(band))
    cy = round(sum(y for _, y in band) / len(band))
    vx, vy = boot[0] - cx, boot[1] - cy
    tip = ((1 if vx > 0 else -1), 0) if abs(vx) > abs(vy) else (0, (1 if vy > 0 else -1))
    for pattern in (HEART7, HEART5, HEART3):
        marks = {(cx + dx, cy + dy): c for (dx, dy), c in stamp(pattern, tip).items()}
        # the whole logo on this leg's tights, clear of the other logo
        clear = {(x + dx, y + dy) for x, y in marks for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        if all(q in leg for q in marks) and not clear & set(taken):
            return marks
    return {}


def plan_back_views(rom, frames):
    """Shawn's lower-body pieces that mostly appear under a head drawn from behind (hair, no eye pixels inside the
    head bounds the shared base body gives, data/nwo-native-anatomy.json). Run on the original game, this gives
    BACK_VIEWS."""
    from native_gear_art import anatomy
    from raw_profiles import profiles, entries, SHADOW
    by = {(f['kind'], f['index']): f for f in frames}
    heads, votes = anatomy(), {}

    def behind(index):
        entry, frame = heads.get(str(index)), by.get(('primary', index))
        if not entry or not frame:
            return None
        l, t, r, b = entry['bounds']
        head = [v for (x, y), v in raster(frame)[0].items() if l <= x <= r and t <= y <= b]
        if len(head) < 40:
            return None
        return sum(v in (13, 14) for v in head) * 4 >= len(head) and BLACK not in head
    for address in profiles(rom):
        parts = [('secondary' if p & 0x8000 else 'primary', (p & 0x7FFF) // 3) for p, _, _ in entries(rom, address)
                 if p != SHADOW]
        views = [behind(i) for kind, i in parts if kind == 'primary' and i < 527]
        views = [v for v in views if v is not None]
        if views:
            for kind, i in parts:
                if kind == 'secondary':
                    votes.setdefault(i, [0, 0])[all(views)] += 1
    return {i for i, (front, back) in votes.items() if back > front}


def seat(points):
    """The DX emblem centred on the top of the tights, for upright legs (boots below)."""
    tights = [q for q, v in points.items() if v in TIGHTS]
    boots = [q for q, v in points.items() if v in BOOT]
    if not tights or not boots or sum(y for _, y in boots) / len(boots) < sum(y for _, y in tights) / len(tights) + 8:
        return {}
    top = min(y for _, y in tights)
    band = [(x, y) for x, y in tights if y <= top + 5]
    cx, cy = round(sum(x for x, _ in band) / len(band)), top + 4
    for pattern in SEATS:
        marks = {(cx + dx, cy + dy): c for (dx, dy), c in stamp(pattern, (0, 1)).items()}
        if all(points.get(q) in TIGHTS for q in marks):
            return marks
    return {}


def logos(points, back=False):
    marks = seat(points) if back else {}
    for leg, boot in legs(points):
        top = max(leg.values())
        if top < 7:
            continue
        spots = [round(top * 0.62)] if top < 16 else [round(top * 0.25) + 1, round(top * 0.68)]
        for at in spots:
            marks.update(place(leg, boot, at, points, marks))
    return marks


def author(frame):
    """{tile field: 64 palette indices} for every field this gear changes (scott_frame_catalog.catalog row)."""
    if frame.get('common') and frame['kind'] == 'primary':
        return {}       # the generic upper bodies: their tights can run on into a singlet
    points, mapping = raster(frame)
    skin = sum(v in SKIN for v in points.values())
    if skin * 5 > len(points):
        return {}       # bare legs (trunks bodies) or someone else: these are not Shawn's tights
    out = {}
    for q, colour in logos(points, frame['kind'] == 'secondary' and frame['index'] in BACK_VIEWS).items():
        ref, k = mapping[q]
        pixels = out.setdefault(ref['field'], list(ref['pixels']))
        pixels[k] = colour
    return {f: v for f, v in out.items()
            if v != next(r['pixels'] for p in frame['parts'] for r in p['refs'] if r['field'] == f)}
