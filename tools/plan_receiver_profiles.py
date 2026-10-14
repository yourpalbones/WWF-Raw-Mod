"""Choose each own-art receiver's Perfect-Plex drawings from the wrestler's own Raw poses, following Royal's move.

For every step the target is the Royal donor's receiving drawing exactly as Royal Rumble places it against
Mr. Perfect (data/perfect-receivers.json, canonical facing), split into upper body (component 0) and lower body
(component 1) for reference only: the two components are the Royal pose pieces each step is built from, not
anatomy. Royal draws only what shows: during the facelock and hold the receiver's head and torso are behind
Mr. Perfect. So the comparison is of the composite: Mr. Perfect's own drawing for that step (the native capture
the finisher comes from, same anchor) is in front, and a candidate's pixels behind him are free. The candidates
are every Raw profile an animation stream references (tools/raw_profiles.py), drawn with the receiver's own
parts, in four facings (as drawn, mirrored, upside down, both). Every pixel is classed by its actual colour as
skin and hair (warm tones) or gear (the rest), with dark outline pixels agreeing with either; the score is the
class-aware overlap of what stays visible, at the best offset. Gear where Royal shows skin costs, so an upright
body cannot stand in for an inverted lift and the head stays where Royal draws it. Royal's anchors (body_dx, shadow_dx) are kept, so the receiver sits where
Royal puts it.

The plan holds profile addresses, facings and offsets only; the importer draws them from the user's ROM, so the
receiver's own head, gear and edits appear (editor/receiving-art.js ownProfiles).

    python3 tools/plan_receiver_profiles.py RAW.sfc ROYAL.sfc --output data/receiver-profile-plan.json [--slot 11]
    python3 tools/plan_receiver_profiles.py RAW.sfc ROYAL.sfc --art GEAR_MOD.sfc --gear --slot 7   # gear identity

Each step keeps the best-scoring candidate the importer can store: after Mr. Perfect's pixels are removed it must
fit the 144-pixel canvas, Raw's descriptor range and the actor's object budget (15 objects, 60 tiles).
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

from plan_receiving_art import royal_pose, SIZE, OX, OY
from raw_parts import resolve_part, raster
from raw_profiles import profiles, entries, SHADOW

ROOT = Path(__file__).resolve().parents[1]
# Own-art slot -> Royal donor selector whose build is closest (Royal roster: 0 Savage, 1 Perfect, 2 Undertaker,
# 3 Bret, 4 Tatanka, 5 Crush, 6 Flair, 7 Shawn, 8 Razor, 9 Yokozuna, 10 Lex, 11 DiBiase). Slot 5 is own art only
# with Scott Hall's gear (stock Razor uses Royal Razor).
DONORS = {0: 7, 4: 5, 7: 6, 9: 7, 10: 2, 11: 3}
GEAR_DONORS = {5: 8, 7: 10, 9: 7, 10: 2}       # Scott Hall, Sting, Syxx, Kevin Nash


def colour_class(rgb):
    """1 skin or hair (warm), 2 gear, 3 dark outline (agrees with anything)."""
    r, g, b = rgb
    if r * 0.3 + g * 0.59 + b * 0.11 < 40:
        return 3
    return 1 if r >= 100 and r > g > b and r - b >= 40 else 2


def classes(colours):
    return [0] + [colour_class(tuple((c >> s & 31) * 255 // 31 for s in (0, 5, 10))) for c in colours[1:]]


def attacker(royal, finisher, step, shift, cache):
    """Mr. Perfect's drawing for the step on the planning canvas (mirrored like the receivers)."""
    from royal_rumble_sprites import decode_tile
    from inspect_rom import tile
    out = np.zeros((SIZE, SIZE), np.float32)
    for part in finisher[step]['parts']:
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
                if cache[key][sy % 8 * 8 + sx % 8]:
                    X, Y = OX + shift - (part['x'] + x), OY + part['y'] + y
                    if 0 <= X < SIZE and 0 <= Y < SIZE:
                        out[Y, X] = 1
    return out


def target(royal, receivers, selector, step, shift, cache):
    """(skin mask, gear mask, outline mask) of the donor drawing on the planning canvas, by colour class."""
    colours = [royal[0x17C26 + selector * 32 + i * 2] | royal[0x17C27 + selector * 32 + i * 2] << 8 for i in range(16)]
    drawing = royal_pose(royal, receivers, selector, step, classes(colours), shift, cache)
    return [(drawing == k).astype(np.float32) for k in (1, 2, 3)]


OWN = {'primary': 527, 'secondary': 426}   # higher indices resolve through the shared table: another wrestler's art


def candidate(raw, slot, address, shadows, cls):
    """{(x, y): colour class} for a profile drawn with the slot's own parts (shadows left out); None if the profile
    uses any shared common-range part, which would draw another wrestler's art."""
    points = {}
    for part, dx, dy in reversed(entries(raw, address)):
        if part == SHADOW or part in shadows:
            continue
        if (part & 0x7FFF) // 3 >= OWN['secondary' if part & 0x8000 else 'primary']:
            return None
        try:
            for xy, v in raster(resolve_part(raw, slot, part)['parts'], dx, dy).items():
                points[xy] = cls[v]
        except Exception:
            return None
    return points or None


def facings(points):
    for h in (False, True):
        for v in (False, True):
            yield h, v, {((-x - 1) if h else x, (-y - 1) if v else y): l for (x, y), l in points.items()}


def grids(points):
    xs = [x for x, y in points]; ys = [y for x, y in points]
    x0, y0 = min(xs), min(ys)
    g = [np.zeros((max(ys) - y0 + 1, max(xs) - x0 + 1), np.float32) for _ in range(3)]
    for (x, y), k in points.items():
        g[k - 1][y - y0, x - x0] = 1
    return g, x0, y0


def best(skin, gear, line, points, front):
    """(score, dx, dy): candidate pixel (x, y) lands on canonical (x + dx, y + dy). 'front' (Mr. Perfect) hides
    what is behind it; Royal's own receiver pixels under him are left out of the target too."""
    (cs, cg, cline), x0, y0 = grids(points)
    keep = 1 - front
    skin, gear, line = skin * keep, gear * keep, line * keep
    tall = np.maximum(np.maximum(skin, gear), line); call = np.maximum(np.maximum(cs, cg), cline)
    corr = lambda a, b: fftconvolve(a, b[::-1, ::-1], mode='full')
    agree = corr(skin, cs) + corr(gear, cg) + corr(line, call) + corr(tall - line, cline)
    visible = call.sum() - corr(front, call)
    union = tall.sum() + visible - corr(tall, call)
    score = agree / np.maximum(union, 1)
    k = np.unravel_index(int(np.argmax(score)), score.shape)
    # full-mode index k -> template top-left at canvas (k - (shape - 1))
    ky, kx = k[0] - (cs.shape[0] - 1), k[1] - (cs.shape[1] - 1)
    return float(score[k]), int(kx - x0 - OX), int(ky - y0 - OY)


def shadow_parts(raw, slot, addresses):
    """Part IDs drawn in a single colour (the shadow variants)."""
    out = set()
    for a in addresses:
        for part, _, _ in entries(raw, a):
            if part in out or part == SHADOW:
                continue
            try:
                values = set(raster(resolve_part(raw, slot, part)['parts']).values())
            except Exception:
                continue
            if len(values) <= 1:
                out.add(part)
    return out


def storable(points, front):
    """Placed candidate {(X, Y): value} -> canonical image (144x144) without Mr. Perfect's pixels, or None when it
    leaves the canvas, Raw's descriptor range or the actor's object budget."""
    from PIL import Image
    from build_shawn_superkick_animation import pack
    image = Image.new('P', (144, 144))
    for (x, y), v in points.items():
        if front[OY + y, OX + x] if 0 <= OX + x < SIZE and 0 <= OY + y < SIZE else False:
            continue
        if not (-64 <= x < 64 and -105 <= y < 23):
            return None
        image.putpixel((72 + x, 105 + y), v)
    if not any(pack_ok(o) for o in pack(image, 144)):
        return None
    return image


def pack_ok(option):
    (objects, tiles), _ = option
    return objects + 2 <= 17 and tiles + 4 <= 64


def plan(raw, royal, slot, selector, receivers, finisher, keep=5, art=None):
    shift = receivers['canonical']['mirror_shift']
    cache = {}
    art = art or raw
    addresses = profiles(raw)
    shadows = shadow_parts(art, slot, addresses)
    from raw_parts import palette
    cls = classes(palette(art, slot))
    drawn = {a: candidate(art, slot, a, shadows, cls) for a in addresses}
    drawn = {a: p for a, p in drawn.items() if p and len(p) >= 200}
    steps = []
    for step in range(len(receivers['workers'][selector]['poses'])):
        skin, gear, line = target(royal, receivers, selector, step, shift, cache)
        front = attacker(royal, finisher, step, shift, cache)
        area = skin.sum() + gear.sum() + line.sum()
        ranked = []
        for a, pts in drawn.items():
            if not 0.6 <= len(pts) / area <= 2.5:
                continue
            for h, v, f in facings(pts):
                score, dx, dy = best(skin, gear, line, f, front)
                ranked.append((score, a, h, v, dx, dy))
        ranked.sort(key=lambda r: -r[0])
        chosen = []
        for s, a, h, v, dx, dy in ranked:
            values = {}
            for part, pdx, pdy in reversed(entries(raw, a)):
                if part == SHADOW or part in shadows:
                    continue
                for (x, y), val in raster(resolve_part(art, slot, part)['parts'], pdx, pdy).items():
                    values[(((-x - 1) if h else x) + dx, ((-y - 1) if v else y) + dy)] = val
            if storable(values, front) is None:
                continue
            chosen.append({'profile': a, 'hflip': h, 'vflip': v, 'dx': dx, 'dy': dy, 'score': round(s, 3)})
            if len(chosen) >= keep:
                break
        steps.append(chosen)
        print(f"slot {slot} step {step}: {chosen[0]['score']:.3f} {chosen[0]['profile']:06x} h={chosen[0]['hflip']} v={chosen[0]['vflip']}", flush=True)
    return steps


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('raw', type=Path); p.add_argument('royal', type=Path)
    p.add_argument('--output', type=Path, default=ROOT / 'data/receiver-profile-plan.json')
    p.add_argument('--slot', type=int, action='append')
    p.add_argument('--art', type=Path, help='ROM whose art the receiver is drawn with (a gear mod); default RAW')
    p.add_argument('--gear', action='store_true', help="store as the slot's gear-identity plan")
    a = p.parse_args()
    raw, royal = a.raw.read_bytes(), a.royal.read_bytes()
    art = a.art.read_bytes() if a.art else raw
    receivers = json.loads((ROOT / 'data/perfect-receivers.json').read_text())
    text = (ROOT / 'editor/royal-import-layouts.js').read_text()
    finisher = json.loads(text[text.index('=') + 1:text.rindex(';')])['finisher']
    out = json.loads(a.output.read_text()) if a.output.exists() else {'method': __doc__.split('\n\n')[0], 'slots': {}}
    donors = GEAR_DONORS if a.gear else DONORS
    for slot in a.slot or sorted(donors):
        entry = {'donor': donors[slot], 'steps': plan(raw, royal, slot, donors[slot], receivers, finisher, art=art)}
        slot_plan = out['slots'].setdefault(str(slot), {})
        if a.gear:
            slot_plan['gear'] = entry
        else:
            slot_plan.update(entry)
        a.output.write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
