"""Find candidate pose correspondence from native Bret silhouettes in both games.

An identical silhouette is a useful candidate, not proof of animation semantics.
Inputs are private ROMs and WRAM snapshots; the report contains indices only.
"""
import argparse
import json
from pathlib import Path

import royal_rumble_sprites as royal
import scott_frame_catalog as raw
from build_bret_gear import ORIGINAL_HASH
import hashlib


def silhouette(points):
    if not points:
        return None
    left = min(x for x, y in points)
    top = min(y for x, y in points)
    return tuple(sorted((x - left, y - top) for x, y in points))


def compare(raw_rom, raw_wram, royal_rom, royal_wram):
    if hashlib.sha256(raw_rom).hexdigest() != ORIGINAL_HASH:
        raise ValueError('Requires original Raw USA for the Bret comparison')
    lookup = {}
    for frame in royal.catalog(royal_rom, royal_wram, 3):
        if frame['index'] >= 16:
            lookup.setdefault(silhouette(royal.raster(frame)), []).append(frame['index'])
    rows = []
    for frame in raw.catalog(raw_rom, raw_wram, 1):
        if not frame['common']:
            key = silhouette(raw.raster(frame)[0])
            rows.append({'kind': frame['kind'], 'raw_index': frame['index'],
                         'royal_candidates': lookup.get(key, []) if key else []})
    return {'method': 'Exact opaque silhouette, translated to bounding-box origin',
            'semantic_animation_mapping_verified': False,
            'rows': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('raw_rom', 'raw_wram', 'royal_rom', 'royal_wram', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    report = compare(*(getattr(args, name).read_bytes() for name in
                       ('raw_rom', 'raw_wram', 'royal_rom', 'royal_wram')))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Matched candidates for', sum(bool(row['royal_candidates']) for row in report['rows']),
          'of', len(report['rows']), 'Raw own pose entries')
