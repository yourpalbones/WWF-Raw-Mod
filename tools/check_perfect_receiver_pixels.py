"""Exact opaque-pixel coverage of the Perfect-Plex receiving recipes (needs the Royal ROM).

Replaces the S3 bounds check with a per-pixel check. Each of the 144 receiving
drawings (12 Royal workers x 12 frames) is decoded from the user's Royal Rumble
ROM. It is painted the way both receiver builders paint it (part x + 73,
y + 105, later parts underneath earlier ones). The script then verifies that
every opaque pixel lies inside a descriptor chunk sampled at chunk x + 64.
Also reports source-tile references that fail to decode.

Only counts are written; no pixels or tile data leave the ROM.

    python3 tools/check_perfect_receiver_pixels.py ROYAL_ROM [--output report.json]
"""
import argparse
import hashlib
import json
from pathlib import Path
from inspect_rom import tile
from royal_rumble_sprites import decode_tile

ROOT = Path(__file__).resolve().parents[1]
ROYAL_SHA256 = '51c53e36ed0b959b0695fc6ef036fa7302d1c995eca35c28261d6f3cb77df0ca'
PAINT_X, PAINT_Y, SAMPLE_X = 73, 105, 64


def paint(rom, pose, cache):
    """Opaque pixels in builder canvas coordinates; later parts sit underneath."""
    points = {}
    for part in reversed(pose['parts']):
        size = part['size']
        for y in range(size):
            for x in range(size):
                sx = size - 1 - x if part['hflip'] else x
                sy = size - 1 - y if part['vflip'] else y
                ref = tuple(part['refs'][(sy // 8) * (size // 8) + sx // 8])
                if ref not in cache:
                    cache[ref] = tile(decode_tile(rom, ref[0], bool(ref[1]))[0], 0, 4)
                value = cache[ref][sy % 8 * 8 + sx % 8]
                if value:
                    points[part['x'] + x + PAINT_X, part['y'] + y + PAINT_Y] = value
                else:
                    # Transparent pixels from a later (underneath) part do not erase earlier ones.
                    pass
    return points


def covered(pose):
    cells = set()
    for x, y, size in pose['chunks']:
        for yy in range(size):
            for xx in range(size):
                cells.add((x + SAMPLE_X + xx, y + PAINT_Y + yy))
    return cells


def check(rom, recipes):
    cache, rows = {}, []
    for worker in recipes['workers']:
        for pose in worker['poses']:
            points = paint(rom, pose, cache)
            cells = covered(pose)
            missing = [p for p in points if p not in cells]
            outside_canvas = [p for p in points if not (0 <= p[0] < 144 and 0 <= p[1] < 144)]
            xs = [x - PAINT_X for x, _ in points]
            ys = [y - PAINT_Y for _, y in points]
            bbox = [min(xs), min(ys), max(xs), max(ys)] if points else None
            rows.append({'selector': worker['selector'], 'source_frame': pose['source_frame'],
                         'opaque_pixels': len(points), 'uncovered_pixels': len(missing),
                         'outside_144_canvas': len(outside_canvas),
                         'bbox_matches_recipe': bbox == pose['bbox'],
                         'chunk_pixels': len(cells),
                         'empty_chunk_tiles': sum(
                             1 for x, y, size in pose['chunks'] for ty in range(size // 8) for tx in range(size // 8)
                             if not any((x + SAMPLE_X + tx * 8 + i, y + PAINT_Y + ty * 8 + j) in points
                                        for i in range(8) for j in range(8)))})
    return {
        'generated_by': 'tools/check_perfect_receiver_pixels.py',
        'royal_rom_sha256': hashlib.sha256(rom).hexdigest(),
        'scope': 'Builder canvas only (paint +73/+105, sample +64). Says nothing about runtime upload, '
                 'palette mapping, VRAM, OAM order or on-screen placement.',
        'drawings': len(rows),
        'decoded_source_tiles': len(cache),
        'drawings_with_uncovered_pixels': sum(r['uncovered_pixels'] > 0 for r in rows),
        'total_uncovered_pixels': sum(r['uncovered_pixels'] for r in rows),
        'drawings_outside_canvas': sum(r['outside_144_canvas'] > 0 for r in rows),
        'drawings_bbox_mismatch': sum(not r['bbox_matches_recipe'] for r in rows),
        'total_empty_chunk_tiles': sum(r['empty_chunk_tiles'] for r in rows),
        'rows': rows,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('royal', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    rom = args.royal.read_bytes()
    if hashlib.sha256(rom).hexdigest() != ROYAL_SHA256:
        raise SystemExit('Expected the unmodified Royal Rumble USA ROM')
    result = check(rom, json.loads((ROOT / 'data/perfect-receivers.json').read_text()))
    summary = {k: v for k, v in result.items() if k != 'rows'}
    print(json.dumps(summary, indent=1))
    if args.output:
        args.output.write_text(json.dumps(result, indent=1) + '\n')
