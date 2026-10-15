"""Scott Hall, alternate art pass: black trunks with a red drip waistband, black kneepads with red drips, red boots,
black wristbands and black slicked-back hair, on the native Razor Ramon art (slot 5).

The current Scott gear (tools/build_scott_hall_gear.py) stays as it is; this is a second take. It starts from that
gear's reviewed segmentation, i.e. its decorate() output (trunk cloth black, boots red, kneepads black, Razor's gold
removed), and changes the details:
- trunks: the red marks, lettering and Razor's red waist line become one motif, a red waistband with drips hanging
  toward the legs (Raw keeps each pose's trunks in one piece, so each piece's trunk cloth gets the band);
- kneepads: black with a red top edge and drips toward the boots;
- Razor's gold wristbands become black bands (the current gear paints them as skin);
- the boots keep Razor's own darker red, which the drips share;
- the hair is near-black with a dark brown sheen; the moustache and jaw stubble (hair pixels against skin) are the dark
  brown. Razor's hair browns (9, 10) also shade his whole body, so only the hair inside the head moves to its own
  entries (Razor's freed gold, 6 and 8).
No vest (he did not wrestle in it). Pixels are only recoloured: every silhouette stays Raw's.

    from scott_alt_art import author, PALETTE
"""
from build_scott_hall_gear import decorate as current_decorate, components
from scott_frame_catalog import raster
from native_gear_art import anatomy


def bgr(r, g, b):
    return (r >> 3) | (g >> 3) << 5 | (b >> 3) << 10


# Slot 5 palette entries this pass sets (others keep Razor's: skin 7/11/12/15, outline 1).
PALETTE = {2: bgr(164, 16, 40), 3: bgr(204, 24, 48), 4: bgr(10, 10, 12), 5: bgr(44, 44, 50), 6: bgr(18, 14, 12),
           8: bgr(54, 42, 34), 13: bgr(40, 40, 40), 14: bgr(208, 208, 208)}
BLACK, CLOTH, CLOTH_LIGHT, RED_DARK, RED, HAIR, HAIR_SHEEN = 1, 4, 5, 2, 3, 6, 8
SKIN = {7, 9, 10, 11, 12, 15}
TRUNK_DRIPS = [2, 0, 3, 1, 0, 2, 0, 1, 3, 0]     # drip length below the waistband, column by column
PAD_DRIPS = [1, 0, 2, 0, 1, 1, 0, 2, 0]


def classes(frame):
    """The current gear's segmentation of a Razor piece: trunk cloth, kneepads, boots, gold it turned to skin."""
    points, mapping = raster(frame)
    base = current_decorate(frame)
    current = {q: base.get(mapping[q][0]['field'], mapping[q][0]['pixels'])[mapping[q][1]] for q in points}
    pads = {q for q, v in points.items() if v in {2, 3} and current[q] in {1, 5}} if frame['kind'] == 'secondary' else set()
    pads |= {q for q, v in points.items() if v in {2, 3} and current[q] in {2, 3} and frame['kind'] == 'secondary'
             and any((q[0] + dx, q[1] + dy) in pads for dx in (-1, 0, 1) for dy in (-1, 0, 1))}
    trunk = {q for q, v in points.items() if v in {2, 3, 4, 5, 6, 8} and current[q] in {4, 5, 8} and q not in pads}
    edge = {q for q, v in points.items() if v in {2, 3} and current[q] in {2, 3} and q not in pads}
    grow = [q for q in trunk]
    while grow:                     # Razor's red waist line (the current gear keeps it red) is trunk cloth too
        x, y = grow.pop()
        for n in ((x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            if n in edge and n not in trunk:
                trunk.add(n)
                grow.append(n)
    boots = {q for q, v in points.items() if v in {4, 5} and current[q] in {2, 3}}
    gold_off = {q for q, v in points.items() if v in {6, 8} and current[q] in SKIN}
    return points, mapping, base, trunk, pads, boots, gold_off


def author(frame):
    """{tile field: 64 palette indices} for every field this pass changes (scott_frame_catalog.catalog row)."""
    points, mapping, base, trunk, pads, boots, gold_off = classes(frame)
    out = {ref['field']: list(base.get(ref['field'], ref['pixels'])) for part in frame['parts'] for ref in part['refs']}

    def now(q):
        ref, k = mapping[q]
        return out[ref['field']][k]

    def put(q, v):
        if q in mapping:
            ref, k = mapping[q]
            out[ref['field']][k] = v

    for q in trunk:
        put(q, CLOTH_LIGHT if points[q] in {3, 5, 8} else CLOTH)
    for q in pads:
        put(q, CLOTH_LIGHT if points[q] == 3 else CLOTH)
    for q in gold_off:
        put(q, CLOTH_LIGHT if points[q] == 8 else CLOTH)

    skin = {q for q, v in points.items() if v in SKIN}
    scalp = hair(frame, points)
    for q in scalp:
        face = sum((q[0] + dx, q[1] + dy) in skin and (q[0] + dx, q[1] + dy) not in scalp
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1)) >= 3
        put(q, HAIR_SHEEN if face or points[q] == 10 else HAIR)    # moustache and stubble: dark brown, not black
    for q in points:
        if now(q) in {6, 8} and points[q] in {6, 8}:
            put(q, CLOTH_LIGHT if points[q] == 8 else CLOTH)     # any gold left over is black, never hair colour

    legs = boots | pads
    for group in components({q: 1 for q in trunk}, {1}):
        if len(group) >= 6:
            drip(group, away_from(group, legs), TRUNK_DRIPS, put)
    for group in components({q: 1 for q in pads}, {1}):
        if len(group) >= 5:
            drip(group, away_from(group, boots) if boots else (0, -1), PAD_DRIPS, put)
    return {f: v for f, v in out.items() if v != next(r['pixels'] for p in frame['parts'] for r in p['refs'] if r['field'] == f)}


def hair(frame, points):
    """Razor's hair: his browns (9, 10) dithered with black inside the head. Raw draws every wrestler on one base
    body, so the head bounds measured on the native Nash/Syxx frames (data/nwo-native-anatomy.json) hold for Razor;
    inside them, thin brown lines with skin around them are face shading and stay."""
    if frame['kind'] != 'primary' or frame.get('common'):
        return set()
    entry = anatomy().get(str(frame['index']))
    if not entry:
        return set()
    l, t, r, b = entry['bounds']
    return {q for q, v in points.items() if v in {9, 10} and l - 1 <= q[0] <= r + 1 and t - 1 <= q[1] <= b + 1
            and sum(points.get((q[0] + dx, q[1] + dy)) in {1, 9, 10} for dx in (-1, 0, 1) for dy in (-1, 0, 1)) >= 5}


def away_from(group, others):
    """Unit axis (dx, dy) from the others' centre toward this group: the waistband side. Upright when unknown."""
    if not others:
        return (0, -1)
    gx = sum(x for x, _ in group) / len(group); gy = sum(y for _, y in group) / len(group)
    ox = sum(x for x, _ in others) / len(others); oy = sum(y for _, y in others) / len(others)
    dx, dy = gx - ox, gy - oy
    if abs(dy) >= abs(dx):
        return (0, -1) if dy <= 0 else (0, 1)
    return (-1, 0) if dx <= 0 else (1, 0)


def drip(group, up, lengths, put):
    """A red band on the group's edge facing `up`, with drips of the given lengths running the other way."""
    ux, uy = up
    lanes = {}
    for x, y in group:
        lane, depth = (x, y * uy) if ux == 0 else (y, x * ux)       # depth grows toward `up`
        lanes.setdefault(lane, []).append((depth, (x, y)))
    first = min(lanes)
    depths = [d for cells in lanes.values() for d, _ in cells]
    cap = (max(depths) - min(depths) + 1) // 3                         # small cloth gets short drips
    for lane, cells in lanes.items():
        cells.sort(reverse=True)                                       # from the band edge inward
        n = min(lengths[(lane - first) % len(lengths)], cap)
        for i, (_, q) in enumerate(cells[:n + 1]):
            put(q, RED if i < n or n == 0 else RED_DARK)
