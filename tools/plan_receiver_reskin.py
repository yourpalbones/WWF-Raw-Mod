"""Rebuild Royal's Perfect-Plex receiving drawings from each own-art wrestler's own pixels.

Royal Rumble's receiving drawings are the move as it should look: the tie-up, the facelock, the lift with the
legs up, the bridge. Raw has no drawing of most of those poses for anyone, so a wrestler's own Raw poses can only
approximate them (tools/plan_receiver_profiles.py). This planner keeps Royal's drawing, pixel for pixel in shape
and placement, and takes every pixel's colour from the wrestler's own art at the matching place on their body:

- Examples: Raw draws every wrestler's piece i in the same pose, and Raw Bret's piece i was matched to Royal
  Bret's frame k (data/perfect-pose-matches.json, accepted rows). Royal draws every worker's frame k in the same
  pose. So the Royal donor's frame k and the wrestler's piece i are a pair: the same pose drawn as the donor and
  as the wrestler. Each pair is aligned by silhouette (overlap of at least 0.5) and used in both facings.
- For every pixel of Royal's receiving drawing, the 11x11 neighbourhood (centre-weighted) is compared with the
  donor's pixels in all pairs; the pixel takes the wrestler's pixel at the best-matching place. Neighbouring
  pixels keep copying from the same pair while that stays nearly as good, so arms, legs and heads come across as
  whole pieces of the wrestler's art.
- A mode filter within each of Royal's colour regions removes isolated pixels: each pixel takes the colour most
  of its neighbours in the same region took, copied from the neighbour that has it.

The plan stores, for every pixel of each Royal drawing (in drawing order), which wrestler piece and offset it
copies; the importer reads those pixels from the user's ROM (editor/receiving-art.js reskin), so gear identities
and edits come through. No pixels are stored.

    python3 tools/plan_receiver_reskin.py RAW.sfc ROYAL.sfc ROYAL_WRAM.bin --slot 11 [--output data/receiver-reskin-plan.json]
    python3 tools/plan_receiver_reskin.py RAW.sfc ROYAL.sfc ROYAL_WRAM.bin --art GEAR_MOD.sfc --gear --slot 7
"""
import argparse
import base64
import collections
import json
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

import royal_rumble_sprites as royal
from plan_receiving_art import royal_pose, SIZE, OX, OY
from plan_receiver_profiles import DONORS, GEAR_DONORS
from raw_parts import resolve_index, raster

ROOT = Path(__file__).resolve().parents[1]
OWN = {'primary': 527, 'secondary': 426}
R = 5                       # patch radius
SIGMA = 3.0                 # patch weight falloff
KAPPA = 1.0                 # a coherent copy wins while within (1 + KAPPA) x the best distance
YY, XX = np.mgrid[-R:R + 1, -R:R + 1]
WEIGHT = np.exp(-(XX ** 2 + YY ** 2) / (2 * SIGMA ** 2)).astype(np.float32).ravel()


def _grid(points):
    xs = [x for x, y in points]; ys = [y for x, y in points]
    x0, y0 = min(xs), min(ys)
    g = np.zeros((max(ys) - y0 + 1, max(xs) - x0 + 1), np.float32)
    for (x, y) in points:
        g[y - y0, x - x0] = 1
    return g, x0, y0


def align(a, b):
    """(IoU, dx, dy): points a moved by (dx, dy) overlap points b best."""
    ga, ax, ay = _grid(a); gb, bx, by = _grid(b)
    c = fftconvolve(gb, ga[::-1, ::-1], mode='full')
    k = np.unravel_index(int(np.argmax(c)), c.shape)
    iou = c[k] / (ga.sum() + gb.sum() - c[k])
    return float(iou), int(bx + k[1] - (ga.shape[1] - 1) - ax), int(by + k[0] - (ga.shape[0] - 1) - ay)


def pairs(art, slot, donor_frames, matches, min_iou=0.5):
    """[(kind, index, mirror, donor points, wrestler points)] in the wrestler piece's coordinates."""
    out = []
    for r in matches:
        if not r.get('accepted') or r['index'] >= OWN[r['kind']] or r['royal_index'] not in donor_frames:
            continue
        d = donor_frames[r['royal_index']]
        try:
            t = raster(resolve_index(art, slot, r['kind'], r['index'])['parts'])
        except Exception:
            continue
        if len(d) < 40 or len(t) < 40 or len(set(t.values())) <= 1:
            continue
        a = {((-x) if r['flip'] else x, y): v for (x, y), v in d.items()}
        iou, dx, dy = align(a, t)
        if iou < min_iou:
            continue
        a = {(x + dx, y + dy): v for (x, y), v in a.items()}
        for mirror in (False, True):
            m = (lambda x: -x - 1) if mirror else (lambda x: x)
            out.append((r['kind'], r['index'], mirror, {(m(x), y): v for (x, y), v in a.items()},
                        {(m(x), y): v for (x, y), v in t.items()}))
    return out


def index(examples):
    """Patch descriptors of the donor drawing at every place the wrestler draws: (patches, centres, sources)."""
    patches, centres, sources = [], [], []
    for e, (_, _, _, a, t) in enumerate(examples):
        xs = [x for x, y in set(a) | set(t)]; ys = [y for x, y in set(a) | set(t)]
        x0, y0 = min(xs) - R, min(ys) - R
        g = np.zeros((max(ys) - y0 + R + 1, max(xs) - x0 + R + 1), np.int8)
        for (x, y), v in a.items():
            g[y - y0, x - x0] = v
        p = np.array(sorted(t))
        cy, cx = p[:, 1] - y0, p[:, 0] - x0
        patches.append(np.stack([g[cy + dy, cx + dx] for dy in range(-R, R + 1) for dx in range(-R, R + 1)], 1))
        centres.append(g[cy, cx])
        sources.append(np.column_stack([np.full(len(p), e), p]))
    return np.concatenate(patches), np.concatenate(centres), np.concatenate(sources)


def synthesize(drawing, examples, idx):
    """{(x, y): (example, qx, qy)} for every pixel of the donor drawing {(x, y): donor index}."""
    patches, centres, sources = idx
    xs = [x for x, y in drawing]; ys = [y for x, y in drawing]
    x0, y0 = min(xs) - R, min(ys) - R
    g = np.zeros((max(ys) - y0 + R + 1, max(xs) - x0 + R + 1), np.int8)
    for (x, y), v in drawing.items():
        g[y - y0, x - x0] = v
    by_centre = {v: np.nonzero(centres == v)[0] for v in range(16)}
    chosen = {}
    for x, y in sorted(drawing, key=lambda p: (p[1], p[0])):
        q = g[y - y0 - R:y - y0 + R + 1, x - x0 - R:x - x0 + R + 1].ravel()
        cand = by_centre[int(g[y - y0, x - x0])]
        if not len(cand):
            cand = np.arange(len(patches))
        d = ((patches[cand] != q) * WEIGHT).sum(1)
        j = int(np.argmin(d))
        best = (float(d[j]), tuple(int(v) for v in sources[cand[j]]))
        coherent = None
        for dx, dy in ((-1, 0), (0, -1), (-1, -1), (1, -1), (-2, 0), (0, -2)):
            n = chosen.get((x + dx, y + dy))
            if not n:
                continue
            e, qx, qy = n[0], n[1] - dx, n[2] - dy
            if (qx, qy) not in examples[e][4]:
                continue
            a = examples[e][3]
            patch = np.array([a.get((qx + ax, qy + ay), 0) for ay in range(-R, R + 1) for ax in range(-R, R + 1)], np.int8)
            dc = float(((patch != q) * WEIGHT).sum())
            if coherent is None or dc < coherent[0]:
                coherent = (dc, (e, qx, qy))
        chosen[(x, y)] = coherent[1] if coherent and coherent[0] <= best[0] * (1 + KAPPA) + 0.5 else best[1]
    return chosen


def smooth(chosen, drawing, examples, radius=2, rounds=2):
    """Mode filter within each donor colour region; a changed pixel copies the neighbour that has the colour."""
    value = lambda s: examples[s[0]][4][(s[1], s[2])]
    for _ in range(rounds):
        new = {}
        for (x, y), s in chosen.items():
            b = drawing[(x, y)]
            votes, holder = collections.Counter(), {}
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    n = (x + dx, y + dy)
                    if drawing.get(n) == b and n in chosen:
                        v = value(chosen[n]); votes[v] += 1
                        holder.setdefault(v, chosen[n])
            v = votes.most_common(1)[0][0]
            new[(x, y)] = s if value(s) == v else holder[v]
        chosen = new
    return chosen


def plan(raw, royal_rom, wram, slot, selector, receivers, matches, art=None):
    art = art or raw
    shift = receivers['canonical']['mirror_shift']
    donor_frames = {f['index']: royal.raster(f) for f in royal.catalog(royal_rom, wram, selector)}
    examples = pairs(art, slot, donor_frames, matches)
    idx = index(examples)
    used, steps = {}, []
    for step in range(len(receivers['workers'][selector]['poses'])):
        canvas = royal_pose(royal_rom, receivers, selector, step, list(range(16)), shift, {})
        drawing = {(int(x) - OX, int(y) - OY): int(canvas[y, x]) for y, x in zip(*np.nonzero(canvas))}
        chosen = smooth(synthesize(drawing, examples, idx), drawing, examples)
        sources, ids = {}, []
        for x, y in sorted(drawing, key=lambda p: (p[1], p[0])):
            e, qx, qy = chosen[(x, y)]
            k = used.setdefault(e, len(used))
            ids.append(sources.setdefault((k, qx - x, qy - y), len(sources)))
        steps.append({'sources': [list(s) for s in sources],
                      'pixels': base64.b64encode(np.array(ids, '<u2').tobytes()).decode()})
        print(f'slot {slot} step {step}: {len(drawing)} pixels from {len(sources)} sources', flush=True)
    order = sorted(used, key=used.get)
    return {'donor': selector, 'examples': [[examples[e][0], examples[e][1], int(examples[e][2])] for e in order],
            'steps': steps}


def render(plan_entry, art, slot, receivers, royal_rom):
    """Reference rendering of a plan: [{(x, y): wrestler index}] per step (what the importer draws)."""
    shift = receivers['canonical']['mirror_shift']
    pieces = {}
    out = []
    for step, s in enumerate(plan_entry['steps']):
        canvas = royal_pose(royal_rom, receivers, plan_entry['donor'], step, list(range(16)), shift, {})
        order = sorted(((int(x) - OX, int(y) - OY) for y, x in zip(*np.nonzero(canvas))), key=lambda p: (p[1], p[0]))
        ids = np.frombuffer(base64.b64decode(s['pixels']), '<u2')
        image = {}
        for (x, y), i in zip(order, ids):
            e, dx, dy = s['sources'][i]
            kind, index, mirror = plan_entry['examples'][e]
            if (kind, index) not in pieces:
                pieces[(kind, index)] = raster(resolve_index(art, slot, kind, index)['parts'])
            qx, qy = x + dx, y + dy
            v = pieces[(kind, index)].get(((-qx - 1) if mirror else qx, qy))
            if v:
                image[(x, y)] = v
        out.append(image)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('raw', type=Path); p.add_argument('royal', type=Path); p.add_argument('royal_wram', type=Path)
    p.add_argument('--output', type=Path, default=ROOT / 'data/receiver-reskin-plan.json')
    p.add_argument('--slot', type=int, action='append')
    p.add_argument('--art', type=Path, help='ROM whose art the receiver is drawn with (a gear mod); default RAW')
    p.add_argument('--gear', action='store_true', help="store as the slot's gear-identity plan")
    a = p.parse_args()
    raw, royal_rom, wram = a.raw.read_bytes(), a.royal.read_bytes(), a.royal_wram.read_bytes()
    art = a.art.read_bytes() if a.art else raw
    receivers = json.loads((ROOT / 'data/perfect-receivers.json').read_text())
    matches = json.loads((ROOT / 'data/perfect-pose-matches.json').read_text())['rows']
    donors = GEAR_DONORS if a.gear else DONORS
    for slot in a.slot or sorted(donors):
        entry = plan(raw, royal_rom, wram, slot, donors[slot], receivers, matches, art)
        out = json.loads(a.output.read_text()) if a.output.exists() else {'method': __doc__.split('\n\n')[0], 'slots': {}}
        slot_plan = out['slots'].setdefault(str(slot), {})
        if a.gear:
            slot_plan['gear'] = entry
        else:
            slot_plan.update(entry)
        a.output.write_text(json.dumps(out, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
