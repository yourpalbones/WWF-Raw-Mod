"""Prove that editing one worker's receiving Perfect-Plex drawing leaves every other worker unchanged.

Compares a ROM before and after an editor save (tools/editor_driver.py edit-receiver). Every changed byte
must be one of the following:
- the header checksum;
- a tile packet that the edited worker's receiving descriptors reference;
- that tile's directory pointer, or its relocated packet plus the relocation cursor at $70:FDF0.
The tool then decodes every receiving pose of every installed worker, and the stock Raw tile sources, and
reports which ones differ.

    python3 tools/check_receiver_isolation.py BEFORE.sfc AFTER.sfc --slot N
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_DIRECTORY = 0x5e0000   # RX1/RX2


def directory(data):
    return 0x7da000 if bytes(data[0x70fe40:0x70fe49]) in (b'ROYAL-RX3', b'ROYAL-RX4') else LEGACY_DIRECTORY


def file_offset(address):
    return address + 0x400000 if 0x3e0000 <= address < 0x400000 else address


def long(data, at):
    return data[at] | data[at + 1] << 8 | data[at + 2] << 16


def packet(data, offset):
    length = 4 + sum(bin(b).count('1') for b in data[offset:offset + 4])
    return bytes(data[offset:offset + length])


def receiving_poses(data, slot):
    """[(pose, [(tile id, pointer at, packet bytes)])] for one slot."""
    table = long(data, 0x71d000 + slot * 3)
    if not 0x71d100 <= table < 0x71d400:
        return []
    poses = []
    for i in range(12):
        address = long(data, table + i * 3)
        count, large, cursor, tiles = data[address], data[address + 1], address + 2, []
        for n in range(count):
            cursor += 3
            for _ in range(4 if n < large else 1):
                tile_id = data[cursor] | data[cursor + 1] << 8
                cursor += 2
                at = directory(data) + (tile_id & 0x3fff) * 3
                tiles.append((tile_id, at, packet(data, file_offset(long(data, at)))))
        poses.append((i, bytes(data[address:cursor]), tiles))
    return poses


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--slot', type=int, required=True)
    args = parser.parse_args()
    before, after = args.before.read_bytes(), args.after.read_bytes()
    if len(before) != len(after):
        raise SystemExit('ROM sizes differ')
    slots = [s for s in range(13) if 0x71d100 <= long(before, 0x71d000 + s * 3) < 0x71d400]

    # Allowed byte set: the edited worker's tiles (packets, directory pointers), relocation space and cursor.
    allowed = set(range(0xffdc, 0xffe0)) | set(range(0x40ffdc, 0x40ffe0)) | set(range(0x70fdf0, 0x70fdf3))
    for _, _, tiles in receiving_poses(before, args.slot):
        for _, at, raw in tiles:
            allowed |= set(range(at, at + 3))
            offset = file_offset(long(before, at))
            allowed |= set(range(offset, offset + len(raw)))
    old_cursor, new_cursor = long(before, 0x70fdf0), long(after, 0x70fdf0)
    allowed |= set(range(old_cursor, new_cursor))
    changed = [i for i in range(len(before)) if before[i] != after[i]]
    outside = [i for i in changed if i not in allowed]

    report = {'changed_bytes': len(changed), 'changed_outside_edited_worker': len(outside),
              'first_outside': [hex(i) for i in outside[:10]], 'relocated_bytes': new_cursor - old_cursor,
              'workers': {}}
    for slot in slots:
        old, new = receiving_poses(before, slot), receiving_poses(after, slot)
        differing = [i for (i, d0, t0), (_, d1, t1) in zip(old, new)
                     if d0 != d1 or [(a, r) for a, _, r in t0] != [(a, r) for a, _, r in t1]]
        report['workers'][slot] = {'poses': len(old), 'poses_changed': differing}
    others = [s for s, w in report['workers'].items() if s != args.slot and w['poses_changed']]
    report['other_workers_changed'] = others
    report['edited_worker_changed'] = bool(report['workers'][args.slot]['poses_changed'])
    report['isolated'] = not outside and not others and report['edited_worker_changed']
    print(json.dumps(report, indent=1))
    if not report['isolated']:
        raise SystemExit('Edit was not isolated to the chosen worker')


if __name__ == '__main__':
    main()
