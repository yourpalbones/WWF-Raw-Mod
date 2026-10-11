"""Build ROM-address-only editor layouts from verified native OAM captures.

No ROM, tile bytes or palette bytes are included in the manifest.
"""
import argparse
import hashlib
import json
from pathlib import Path

from build_bret_gear import ORIGINAL_HASH, PALETTE
from decode_sprite_tile import decode_sprite_tile
from extract_oam import objects


def build(rom, snapshots, character="Bret Hart", palette_offset=PALETTE, seed_roots=()):
    if hashlib.sha256(rom).hexdigest() != ORIGINAL_HASH:
        raise ValueError('Requires the verified original USA ROM')
    sources, poses, compressed = {}, [], {}
    def read_trace(root, limit=None):
        calls = root / 'tile_calls.jsonl'
        if calls.exists():
            events = [json.loads(line) for line in calls.read_text().splitlines()]
        else:
            events = [{**json.loads(line), 'compressed': True} for line in (root / 'tiles.jsonl').read_text().splitlines()]
        for event in events:
            if limit is not None and event['frame'] > limit:
                continue
            offset = event['source'] & 0x3fffff
            packed = bool(event['compressed'])
            decoded, length = decode_sprite_tile(rom, offset) if packed else (rom[offset:offset + 32], 32)
            compressed[(event['destination'], decoded)] = (offset, length, packed)
    for root in seed_roots:
        read_trace(Path(root))
    for label, prefix in snapshots:
        prefix = Path(prefix)
        def read(name):
            return Path(str(prefix) + '-' + name + '.bin').read_bytes()
        vram, cgram, regs = read('vram'), read('cgram'), read('registers')
        if regs[0x2101] != 0 or cgram[256:288] != rom[palette_offset:palette_offset + 32]:
            raise ValueError('Unsupported object layout or palette')
        frame = int(prefix.name.split('-')[1])
        read_trace(prefix.parent, frame)
        parts = []
        for record, image in objects(vram, read('oam'), cgram, 0):
            if record['palette'] != 0 or not 0 <= record['y'] < 190 or not -20 <= record['x'] < 256 or not image.getbbox():
                continue
            tiles = []
            for ty in range(record['size'] // 8):
                for tx in range(record['size'] // 8):
                    number = ((record['tile'] & 0xf0) + ty * 16 + ((record['tile'] + tx) & 15)) & 255
                    decoded = vram[number * 32:number * 32 + 32]
                    if not any(decoded):
                        tiles.append(None)
                        continue
                    lookup = (0x7E2000 + number * 32, decoded)
                    packed = lookup in compressed
                    if packed:
                        offset, length, packed = compressed[lookup]
                    else:
                        offset, length = rom.find(decoded), 32
                        if offset < 0 or rom.find(decoded, offset + 1) >= 0:
                            raise ValueError(f'Unresolved or ambiguous tile {number} in {prefix}')
                    key = str(offset)
                    sources[key] = {'offset': offset, 'length': length, 'compressed': packed}
                    tiles.append(key)
            parts.append({**record, 'tiles': tiles})
        if not parts:
            raise ValueError('No wrestler objects found')
        # Deduplicate identical layouts, retaining native positions relative to actor.
        left, top = min(p['x'] for p in parts), min(p['y'] for p in parts)
        for p in parts:
            p['x'] -= left
            p['y'] -= top
        width = max(p['x'] + p['size'] for p in parts)
        height = max(p['y'] + p['size'] for p in parts)
        pose = {'capture': f'{prefix.parent.name}/{prefix.name}', 'label': label, 'width': width, 'height': height, 'parts': parts}
        if not any(p['parts'] == parts for p in poses):
            poses.append(pose)
    return {'version': 1, 'character': character, 'original_sha256': ORIGINAL_HASH,
            'palette_offset': palette_offset, 'scope': 'Captured standing and walking layouts; edited gameplay unverified',
            'sources': sources, 'poses': poses}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--snapshot', action='append', required=True, help='LABEL=PREFIX')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.rom.read_bytes(), [s.split('=', 1) for s in args.snapshot])
    args.output.write_text('window.RAW_EDITOR_MANIFEST = ' + json.dumps(result, indent=2) + ';\n')
    print(f"Resolved {len(result['sources'])} sources and {len(result['poses'])} layouts")

if __name__ == '__main__':
    main()
