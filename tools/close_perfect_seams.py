"""Close the see-through seams between Mr. Perfect's semantic-pass pieces and the pieces they are drawn with.

The semantic pass (tools/match_perfect_poses.py --semantic) gives a Raw-only Bret drawing the Royal Perfect frame of a
matched neighbour, placed with that neighbour's transform. Bret's Raw pieces overlap at the waist; Royal's frames meet
edge to edge. Where Raw's profile draws such a piece a few pixels off the neighbour's position (Raw's standing pose
raises the torso 3 px over the legs, for one), the composite opens a see-through band across the stomach.

For every profile that uses a semantic piece, a hole is a pixel solid in Bret's composite, see-through in Perfect's,
with Perfect's body within HOLE_REACH rows directly above and below it. Each semantic piece may move by up to RANGE px:
1. Pinned: a piece whose Royal upper/lower frame pair also appears in a profile built only from exact silhouette
   matches takes the shift that reproduces that exact relation (Royal's own composite).
2. Every other piece takes, by coordinate descent over all its profiles, the shift minimising
   W_HOLE * holes + W_DIFF * |Perfect xor Bret| + W_SHIFT * |shift| (the xor term keeps the pose on Raw's body).
The result is written as reviewed overrides (source 'seam') in data/perfect-pose-review.json; tools/match_perfect_poses
.effective() then places those pieces at the new transform, and tools/update_perfect_pose_manifest.py publishes it.
Piece pixels come from Royal (placed exactly as the converter places them) and from BUILT for every other piece, so
the result does not depend on whether BUILT already carries earlier seam overrides. Nothing is written to any ROM.

    python3 tools/close_perfect_seams.py BUILT.sfc ROYAL.sfc ROYAL_WRAM.bin [--review data/perfect-pose-review.json]
        [--report data/perfect-seam-report.json] [--check]

BUILT is an import with Mr. Perfect (any poses revision). --check only reports; nothing is written.
"""
import argparse
import json
from pathlib import Path

import royal_rumble_sprites as royal
from match_perfect_poses import effective, place, REVIEW
from raw_parts import resolve_part, raster
from raw_profiles import profiles, entries, SHADOW

ROOT = Path(__file__).resolve().parents[1]
BRET, PERFECT = 1, 12
HOLE_REACH, RANGE, SWEEPS = 5, 4, 4
W_HOLE, W_DIFF, W_SHIFT = 3.0, 0.25, 2.0


def name(pid):
    return f"{'s' if pid & 0x8000 else 'p'}{(pid & 0x7FFF) // 3}"


def pid_of(row):
    return (row['index'] * 3) | (0x8000 if row['kind'] == 'secondary' else 0)


def holes(perfect, bret):
    return {(x, y) for (x, y) in bret - perfect
            if any((x, y - k) in perfect for k in range(1, HOLE_REACH + 1))
            and any((x, y + k) in perfect for k in range(1, HOLE_REACH + 1))}


def solve(built, royal_rom, royal_wram, rows, review):
    """Semantic rows, shifts {pid: (dx, dy)}, pins, and the per-profile hole counts before and after. review must not
    hold seam overrides: shifts are measured from the semantic placements."""
    base = {pid_of(r): r for r in effective(rows, review) if r.get('semantic')}
    frames = royal.catalog(royal_rom, royal_wram, 1)
    seams = {k: v for k, v in (review.get('seam_overrides') or {}).items()}
    # Only pieces the converter draws from their semantic transform can move (an exact-silhouette donor wins over a
    # match in tools/convert_perfect_poses.py): BUILT must hold the semantic placement or an earlier seam shift of it.
    for pid, r in list(base.items()):
        art = royal.raster(frames[r['royal_index']])
        built_points = set(raster(resolve_part(built, PERFECT, pid)['parts']))
        options = [(0, 0)] + ([tuple(seams[name(pid)]['shift'])] if name(pid) in seams else [])
        if not any(set(place(art, r['flip'], r['dx'] + sx, r['dy'] + sy)) == built_points for sx, sy in options):
            del base[pid]
    pixels = {}

    def piece(slot, pid):
        if (slot, pid) not in pixels:
            if slot == PERFECT and pid in base:
                r = base[pid]
                pixels[slot, pid] = set(place(royal.raster(frames[r['royal_index']]), r['flip'], r['dx'], r['dy']))
            else:
                try:
                    pixels[slot, pid] = set(raster(resolve_part(built, slot, pid)['parts']))
                except (ValueError, IndexError, KeyError):
                    pixels[slot, pid] = None
        return pixels[slot, pid]

    profs = {}
    for address in profiles(built):
        ents = [e for e in entries(built, address) if e[0] != SHADOW]
        if not any(p in base for p, _, _ in ents):
            continue
        if any(piece(PERFECT, p) is None or piece(BRET, p) is None for p, _, _ in ents):
            continue
        bret = set()
        for p, ox, oy in ents:
            bret |= {(x + ox, y + oy) for x, y in piece(BRET, p)}
        profs[address] = (ents, bret)
    users = {}
    for address, (ents, _) in profs.items():
        for p, _, _ in ents:
            if p in base:
                users.setdefault(p, set()).add(address)

    # 1. Pins from exact relations: Royal origin of each piece = profile offset + transform.
    exact = {pid_of(r): r for r in effective(rows, review) if not r.get('semantic')}
    placed = {**exact, **base}
    relations = {}
    for address in profiles(built):
        ents = [e for e in entries(built, address) if e[0] != SHADOW and e[0] in placed]
        for pu, ux, uy in ents:
            for pl, lx, ly in ents:
                if pu & 0x8000 or not pl & 0x8000:
                    continue
                u, l = placed[pu], placed[pl]
                key = (u['royal_index'], u['flip'], l['royal_index'], l['flip'])
                rel = (u['dx'] + ux - l['dx'] - lx, u['dy'] + uy - l['dy'] - ly)
                relations.setdefault(key, []).append((pu, pl, rel, pu in exact and pl in exact))
    pins = {}
    for key, uses in relations.items():
        refs = {rel for _, _, rel, ok in uses if ok}
        if len(refs) != 1:
            continue
        ref = refs.pop()
        for pu, pl, rel, ok in uses:
            if ok or rel == ref:
                continue
            move = pu if pu in base else pl
            sign = 1 if move == pu else -1
            want = (sign * (ref[0] - rel[0]), sign * (ref[1] - rel[1]))
            if pins.setdefault(move, want) != want:
                raise ValueError(f'{name(move)}: exact references disagree')

    shift = {p: pins.get(p, (0, 0)) for p in base}

    def composite(address, trial=None):
        ents, _ = profs[address]
        out = set()
        for p, ox, oy in ents:
            sx, sy = (trial or {}).get(p, shift.get(p, (0, 0)))
            out |= {(x + ox + sx, y + oy + sy) for x, y in piece(PERFECT, p)}
        return out

    def cost(address, trial):
        a, b = composite(address, trial), profs[address][1]
        return W_HOLE * len(holes(a, b)) + W_DIFF * len(a ^ b)

    unshifted = {}
    for address in profs:
        ents, bret = profs[address]
        a = set()
        for p, ox, oy in ents:
            a |= {(x + ox, y + oy) for x, y in piece(PERFECT, p)}
        unshifted[address] = len(holes(a, bret))
    for _ in range(SWEEPS):
        changed = 0
        for p in sorted(users):
            if p in pins:
                continue
            best = min(((sum(cost(a, {p: (dx, dy)}) for a in users[p]) + W_SHIFT * (abs(dx) + abs(dy)), (abs(dx) + abs(dy), dx, dy))
                        for dx in range(-RANGE, RANGE + 1) for dy in range(-RANGE, RANGE + 1)))
            move = best[1][1:]
            if move != shift[p]:
                shift[p] = move
                changed += 1
        if not changed:
            break
    after = {address: len(holes(composite(address), profs[address][1])) for address in profs}
    return base, shift, pins, unshifted, after


def write_review(path, review):
    """The review file, kept readable: lists on one line, one line per override."""
    lines = []
    for key, value in review.items():
        if key == 'overrides' and value:
            body = ',\n'.join(f'  {json.dumps(k)}: {json.dumps(v)}' for k, v in value.items())
            lines.append(f' {json.dumps(key)}: {{\n{body}\n }}')
        elif isinstance(value, dict) and value:
            body = ',\n'.join(f'  {json.dumps(k)}: {json.dumps(v)}' for k, v in value.items())
            lines.append(f' {json.dumps(key)}: {{\n{body}\n }}')
        else:
            lines.append(f' {json.dumps(key)}: {json.dumps(value)}')
    path.write_text('{\n' + ',\n'.join(lines) + '\n}\n')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('built', type=Path); p.add_argument('royal_rom', type=Path); p.add_argument('royal_wram', type=Path)
    p.add_argument('--matches', type=Path, default=ROOT / 'data/perfect-pose-matches.json')
    p.add_argument('--review', type=Path, default=REVIEW)
    p.add_argument('--report', type=Path, default=ROOT / 'data/perfect-seam-report.json')
    p.add_argument('--check', action='store_true')
    a = p.parse_args()
    rows = json.loads(a.matches.read_text())['rows']
    review = json.loads(a.review.read_text())
    # Seam overrides are recomputed from the semantic placements; other overrides stay as reviewed.
    overrides = review.get('overrides', {})
    review['overrides'] = {k: v for k, v in overrides.items() if v.get('source') != 'seam'}
    review['seam_overrides'] = {k: v for k, v in overrides.items() if v.get('source') == 'seam'}
    base, shift, pins, before, after = solve(a.built.read_bytes(), a.royal_rom.read_bytes(), a.royal_wram.read_bytes(),
                                             rows, review)
    moved = {p: s for p, s in shift.items() if s != (0, 0)}
    report = {'about': 'tools/close_perfect_seams.py: see-through pixels (holes) per profile that uses a semantic piece, '
                       'before and after the seam shifts; pinned pieces reproduce an exact Royal relation.',
              'holes_before': sum(before.values()), 'holes_after': sum(after.values()), 'profiles': len(before),
              'pinned': {name(p): list(s) for p, s in sorted(pins.items())},
              'shifts': {name(p): list(s) for p, s in sorted(moved.items())},
              'per_profile': {f'{k:06X}': [before[k], after[k]] for k in sorted(before)}}
    print(json.dumps({k: v for k, v in report.items() if k != 'per_profile'}))
    del review['seam_overrides']
    if a.check:
        return
    for p, (sx, sy) in sorted(moved.items()):
        r = base[p]
        semantic = next(x['semantic'] for x in rows if (x['kind'], x['index']) == (r['kind'], r['index']))
        review['overrides'][name(p)] = {'royal_index': r['royal_index'], 'flip': r['flip'], 'dx': r['dx'] + sx,
                                        'dy': r['dy'] + sy, 'iou': semantic['iou'], 'source': 'seam',
                                        'shift': [sx, sy], 'pinned': p in pins}
    write_review(a.review, review)
    a.report.write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    main()
