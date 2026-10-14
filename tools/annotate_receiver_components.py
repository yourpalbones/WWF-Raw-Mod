"""Label each Royal receiving object with the component it came from (0 = upper body, 1 = lower body).

tools/map_perfect_receivers.py flattens each Royal frame's two components into one object list, component by
component. This counts each component pose's objects in the Royal ROM (no WRAM needed) and records the split
in data/perfect-receivers.json ('component' per part). Used to choose upper- or lower-body colour roles.

    python3 tools/annotate_receiver_components.py ROYAL_ROM
"""
import argparse
import hashlib
import json
from pathlib import Path
from royal_rumble_sprites import ROYAL_SHA256, FRAME_COUNT, lorom_offset

ROOT = Path(__file__).resolve().parents[1]


def object_count(rom, selector, pose):
    base = int.from_bytes(rom[0xa5a + selector * 2:0xa5c + selector * 2], 'little')
    at = lorom_offset(0x900000 | base + pose * 2)
    entry = lorom_offset(0x918000 + int.from_bytes(rom[at:at + 2], 'little'))
    pointer = (rom[entry] | 128) << 16 | int.from_bytes(rom[entry + 1:entry + 3], 'little')
    count, seen = 0, set()
    while True:
        if pointer in seen or count > 64:
            raise ValueError('cyclic pose')
        seen.add(pointer)
        o = lorom_offset(pointer)
        y, x = rom[o:o + 2]
        if y & 128:
            pointer = ((rom[o + 2] | 128) << 16) | y << 8 | x
            continue
        if not y:
            return count
        count += 1
        pointer += 2 + (4 if x & 128 else 1) * 2


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('royal', type=Path)
    rom = p.parse_args().royal.read_bytes()
    if hashlib.sha256(rom).hexdigest() != ROYAL_SHA256:
        raise SystemExit('Expected the unmodified Royal Rumble USA ROM')
    path = ROOT / 'data/perfect-receivers.json'
    data = json.loads(path.read_text())
    for worker in data['workers']:
        for row, pose in zip(data['components'], worker['poses']):
            counts = [object_count(rom, worker['selector'], c['pose']) for c in row['components']]
            if sum(counts) != len(pose['parts']):
                raise SystemExit(f"Object count mismatch for worker {worker['selector']} frame {row['source_frame']}")
            labels = [i for i, n in enumerate(counts) for _ in range(n)]
            for part, label in zip(pose['parts'], labels):
                part['component'] = label
    path.write_text(json.dumps(data, separators=(',', ':')) + '\n')
    print('labelled', sum(len(p['parts']) for w in data['workers'] for p in w['poses']), 'objects')


if __name__ == '__main__':
    main()
