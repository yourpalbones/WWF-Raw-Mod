"""ROM-free consistency checks for the Perfect-Plex receiving recipes.

Reads only `data/perfect-receivers.json` and the descriptor/profile layout
written by `tools/build_perfect_receiver_prototype.py`. It cannot judge pixels
(the ROM is private); it reports geometry, budget, aliasing and profile facts
that bound some causes and suggest others. Suggested causes are provisional
until a native trace confirms them.

    python3 tools/check_perfect_receivers.py [--json]
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBJECT_LIMIT, TILE_LIMIT = 17, 64          # body + shadow per actor (import_perfect_plex)
SHADOW_OBJECTS, SHADOW_TILES = 2, 4
# Canvas origins used by build_perfect_receiver_prototype.py: parts are painted
# at x+73, chunks are sampled at x+64. Descriptor x is therefore part x + 9.
PAINT_X, SAMPLE_X = 73, 64
# Prototype receiver profile as written by build_perfect_receiver_prototype.py:
# descriptor id (1200+i)*3, body at (+32, 0), then Raw shadow part 0x8024 at (0, -1).
PROTOTYPE_PROFILE = (1200 * 3).to_bytes(2, 'little') + bytes([32, 0, 0x24, 0x80, 0, 0xff, 0xff, 0xff])


def profile_parts(record):
    """Decode a Raw animation profile: 4-byte [part id, dx, dy] entries, FFFF ends."""
    parts = []
    for at in range(0, len(record) - 1, 4):
        ident = int.from_bytes(record[at:at + 2], 'little')
        if ident == 0xffff:
            break
        parts.append({'id': ident, 'dx': int.from_bytes(record[at + 2:at + 3], 'little', signed=True),
                      'dy': int.from_bytes(record[at + 3:at + 4], 'little', signed=True)})
    return parts


def analyse(data):
    owners = defaultdict(set)
    for worker in data['workers']:
        for pose in worker['poses']:
            for part in pose['parts']:
                for ref in part['refs']:
                    owners[ref[0]].add(worker['selector'])
    findings, per_worker = [], {}
    shift = PAINT_X - SAMPLE_X
    extent_failures, order_failures, budget_failures = [], [], []
    max_objects = max_tiles = 0
    for worker in data['workers']:
        sources = {ref[0] for pose in worker['poses'] for part in pose['parts'] for ref in part['refs']}
        w_obj = w_tiles = 0
        for pose in worker['poses']:
            chunks = pose['chunks']
            sizes = [c[2] for c in chunks]
            if sizes != sorted(sizes, reverse=True):
                order_failures.append((worker['selector'], pose['source_frame']))
            objects = len(chunks) + SHADOW_OBJECTS
            tiles = sum((c[2] // 8) ** 2 for c in chunks) + SHADOW_TILES
            w_obj, w_tiles = max(w_obj, objects), max(w_tiles, tiles)
            if objects > OBJECT_LIMIT or tiles > TILE_LIMIT:
                budget_failures.append((worker['selector'], pose['source_frame'], objects, tiles))
            # Chunks must span the opaque bbox once the canvas shift is applied.
            left = min(c[0] for c in chunks) - shift
            right = max(c[0] + c[2] for c in chunks) - shift - 1
            top = min(c[1] for c in chunks)
            bottom = max(c[1] + c[2] for c in chunks) - 1
            x0, y0, x1, y1 = pose['bbox']
            if not (left <= x0 and right >= x1 and top <= y0 and bottom >= y1):
                extent_failures.append((worker['selector'], pose['source_frame']))
        max_objects, max_tiles = max(max_objects, w_obj), max(max_tiles, w_tiles)
        per_worker[worker['selector']] = {
            'source_tiles': len(sources),
            'private_tiles': sum(len(owners[a]) == 1 for a in sources),
            'shared_all': sum(len(owners[a]) == len(data['workers']) for a in sources),
            'shared_some': sum(1 < len(owners[a]) < len(data['workers']) for a in sources),
            'max_objects': w_obj, 'max_tiles': w_tiles}

    def add(ident, severity, summary, detail=None):
        findings.append({'id': ident, 'severity': severity, 'summary': summary, 'detail': detail})

    scope = ' (stored recipe records only; says nothing about runtime upload, scanline, routing or OAM order)'
    add('S1', 'pass' if not budget_failures else 'fail',
        f'Recipe budget: worst stored record uses {max_objects}/{OBJECT_LIMIT} objects and {max_tiles}/{TILE_LIMIT} '
        'tiles including the shadow' + scope + '.', budget_failures or None)
    add('S2', 'pass' if not order_failures else 'fail',
        ('Recipe chunk order: every stored record lists 16x16 chunks before 8x8 chunks' if not order_failures else
         'Some stored records list 8x8 chunks before 16x16 ones') + scope + '.',
        order_failures or None)
    add('S3', 'pass' if not extent_failures else 'fail',
        (f'Bounds check: with the prototype canvas shift (+{shift} px x) the union of chunk extents reaches every '
         'edge of each pose\'s opaque bbox. This does not prove every opaque pixel is covered; a union can have '
         'interior holes. Exact coverage needs the private decoded source tiles.') if not extent_failures else
        'Bounds check failed: chunk extents do not reach the opaque bbox for some poses.',
        extent_failures or None)
    offsets = {tuple(p.get('profile_offset', ())) for w in data['workers'] for p in w['poses']}
    shadow = profile_parts(PROTOTYPE_PROFILE)
    body = shadow[0]
    detached = [p for p in shadow[1:] if p['id'] == 0x8024 and (p['dx'], p['dy'] + 1) != (body['dx'], body['dy'])]
    add('S4', 'info',
        f'Historical prototype fact: the older prototype source (and, by source inspection, the WIP builder) writes '
        f'the receiver body at profile ({body["dx"]},{body["dy"]}) and shadow 0x8024 at '
        f'({shadow[1]["dx"]},{shadow[1]["dy"]}). This check parses a copy of those bytes, not a built ROM, so it '
        'cannot detect an implementation change; a regression test must read a constructed/exported record.',
        {'shadow_offset_differs_from_body': bool(detached), 'profile_offsets_in_data': sorted(offsets)})
    add('S5', 'info',
        'One profile offset for all poses: each drawing\'s descriptor already carries its source-relative position, '
        'so a constant profile offset can reproduce changing body positions. Rendered positions must be derived from '
        'actor origins, profile offsets, descriptors and facing (tools/derive_perfect_pair_coordinates.py) before '
        'choosing any fix.', {'profile_offsets': sorted(offsets)})
    add('S6', 'info',
        'Royal source sharing across Royal workers: '
        + ', '.join(f'selector {s}: {v["private_tiles"]}/{v["source_tiles"]} private'
                    for s, v in sorted(per_worker.items()))
        + '. Each Raw slot needs its own inserted tile IDs. Older Undertaker-only prototype: de-duplicates within one '
        'receiver. WIP builder (codex/perfect-receivers-wip): per-slot private map by code inspection; editor '
        'isolation test not yet run.')
    hflips = {c['hflip'] for r in data['components'] for c in r['components']}
    add('S7', 'info',
        f'Facing: Royal component hflip values {sorted(hflips)}; receiver parts keep Royal orientation while '
        'the attacker capture is mirrored about x=145 (import_perfect_plex.build). See the paired coordinate '
        'derivation for the predicted consequence under each renderer assumption (provisional).')
    return {'workers': per_worker, 'findings': findings, 'max_objects': max_objects, 'max_tiles': max_tiles}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    result = analyse(json.loads((ROOT / 'data/perfect-receivers.json').read_text()))
    if args.json:
        print(json.dumps(result, indent=1))
    else:
        for f in result['findings']:
            print(f'[{f["severity"].upper():4}] {f["id"]}: {f["summary"]}')
            if f['detail'] and f['severity'] == 'fail':
                print('       ', json.dumps(f['detail'])[:300])
