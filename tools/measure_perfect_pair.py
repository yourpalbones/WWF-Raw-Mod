"""Measure the Perfect-Plex pair from native per-frame captures (OAM/VRAM/WRAM).

Inputs: a capture directory written by tools/run_headless.py with an interval of
one frame (frame-NNNNNN-{oam,vram,cgram,registers,wram}.bin), the ROM that was
running, and the unmodified Royal Rumble ROM.

For every captured frame this script does the following:
- Identifies each actor's objects by OBJ palette (attacker 0, receiver 1;
  shadows use palette 6) and reads the actor x/y from WRAM 05F0/0600.
- Matches the attacker's objects to one of its twelve descriptors
  (pointer table 71:0000 + (1000+i)*3). It matches the receiver's objects to
  one of the receiving descriptors in the WIP layout (71:D000 + slot*3 -> table).
- From the matched objects, derives the runtime flip, the reflection constant
  and the profile-dx sign, using screen = actor_x - camera.
- Compares the receiver's rendered placement with the Royal registration:
  the attacker pixel mapping 145 - x, applied to the receiver's Royal anchors.
- Compares every rendered receiver pixel's colour index against the builder's
  expected drawing, to detect stale or partially uploaded tiles.

Only numbers are written. No ROM bytes, pixels or memory dumps.

    python3 tools/measure_perfect_pair.py CAPTURE_DIR BUILT_ROM ROYAL_ROM --receiver-slot 2 --output report.json
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from extract_oam import objects
from inspect_rom import tile
from royal_rumble_sprites import decode_tile

ROOT = Path(__file__).resolve().parents[1]
ATTACKER_PALETTE, RECEIVER_PALETTE, SHADOW_PALETTE = 0, 1, 6
RECEIVER_SLOT_ROYAL = {1: 3, 2: 2, 3: 9, 5: 8, 6: 10, 8: 7, 12: 1}


def long(rom, at):
    return int.from_bytes(rom[at:at + 3], 'little')


def descriptor(rom, address):
    """Raw descriptor with absolute-position objects only (as the builders write them)."""
    count, large = rom[address], rom[address + 1]
    cursor, parts = address + 2, []
    for n in range(count):
        if rom[cursor] != 0:
            raise ValueError(f'Unexpected relative object encoding at {address:06x}')
        x, y = rom[cursor + 1], rom[cursor + 2]
        size = 16 if n < large else 8
        cursor += 3 + 2 * (4 if size == 16 else 1)
        dx = (x & 127) - 128 if x & 64 else x & 127
        parts.append({'dx': dx, 'dy': (y & 127) - 105, 'size': size, 'hflip': bool(x & 128)})
    return parts


def match(objs, parts):
    """Return per-object implied origins if objects match parts in order, else None."""
    if len(objs) != len(parts):
        return None
    if any(o['size'] != p['size'] for o, p in zip(objs, parts)):
        return None
    flips = {o['hflip'] for o in objs}
    if len(flips) != 1:
        return None
    flipped = flips.pop()
    # Unflipped: oam_x = Ox + dx.  Flipped: oam_x = Ox - dx - size + k  -> report Ox - k = oam_x + dx + size.
    xs = {(o['x'] - p['dx']) if not flipped else (o['x'] + p['dx'] + p['size']) for o, p in zip(objs, parts)}
    ys = {o['y'] - p['dy'] for o, p in zip(objs, parts)}
    if len(xs) != 1 or len(ys) != 1:
        return None
    return {'flipped': flipped, 'origin_x': xs.pop(), 'origin_y': ys.pop()}


def recipe_image(royal, pose, mapping, cache):
    points = {}
    for part in reversed(pose['parts']):
        size = part['size']
        for y in range(size):
            for x in range(size):
                sx = size - 1 - x if part['hflip'] else x
                sy = size - 1 - y if part['vflip'] else y
                ref = tuple(part['refs'][(sy // 8) * (size // 8) + sx // 8])
                if ref not in cache:
                    cache[ref] = tile(decode_tile(royal, ref[0], bool(ref[1]))[0], 0, 4)
                value = cache[ref][sy % 8 * 8 + sx % 8]
                if value:
                    points[part['x'] + x, part['y'] + y] = mapping[value]
    return points


def oam_indices(vram, oam, rec, obsel):
    base, select = (obsel & 3) << 14, ((obsel >> 3) & 3) << 13
    size, n, attr = rec['size'], rec['tile'] & 255, oam[rec['index'] * 4 + 3]
    out = {}
    for y in range(size):
        for x in range(size):
            sx = size - 1 - x if rec['hflip'] else x
            sy = size - 1 - y if rec['vflip'] else y
            number = ((n & 0xf0) + (sy // 8) * 16 + ((n + sx // 8) & 15)) & 255
            address = (base + (select + 8192 if attr & 1 else 0) + number * 32) & 65535
            v = tile(vram, address, 4)[(sy % 8) * 8 + sx % 8]
            if v:
                out[x, y] = v
    return out


def measure(capture, rom, royal, slot):
    recipes = json.loads((ROOT / 'data/perfect-receivers.json').read_text())
    worker = recipes['workers'][RECEIVER_SLOT_ROYAL[slot]]
    attacker_desc = [descriptor(rom, long(rom, 0x710000 + (1000 + i) * 3)) for i in range(12)]
    table = long(rom, 0x71d000 + slot * 3)
    receiver_desc = [descriptor(rom, long(rom, table + i * 3)) for i in range(12)]
    # Builder palette mapping (as in build_perfect_receivers.py), to compare colour indices.
    word = lambda data, at: int.from_bytes(data[at:at + 2], 'little')
    palette_base = 0x700000 + word(rom, 0x2cf212)
    rgb = lambda c: [c >> s & 31 for s in (0, 5, 10)]
    colors = [word(royal, 0x17c26 + RECEIVER_SLOT_ROYAL[slot] * 32 + i * 2) for i in range(16)]
    target = [word(rom, palette_base + 64 + slot * 32 + i * 2) for i in range(16)]
    mapping = [0] + [min(range(1, 16), key=lambda j: sum((a - b) ** 2 for a, b in zip(rgb(c), rgb(target[j]))))
                     for c in colors[1:]]
    cache, rows = {}, []
    for wram_path in sorted(capture.glob('frame-*-wram.bin')):
        stem = str(wram_path)[:-len('-wram.bin')]
        frame = int(Path(stem).name.split('-')[1])
        read = lambda n: Path(f'{stem}-{n}.bin').read_bytes()
        wram, vram, oam, cgram, regs = (read(n) for n in ('wram', 'vram', 'oam', 'cgram', 'registers'))
        w = lambda a: int.from_bytes(wram[a:a + 2], 'little')
        actors = [{'action': w(0x6b4 + i), 'x': w(0x5f0 + i), 'y': w(0x600 + i), 'state': w(0xbec + i)} for i in (0, 2)]
        if actors[0]['action'] != 600 and actors[1]['action'] != 540:
            continue
        recs = [rec for rec, image in objects(vram, oam, cgram, regs[0x2101]) if image.getbbox() and rec['y'] < 224]
        by_pal = lambda p: [r for r in recs if r['palette'] == p]
        att, rcv = by_pal(ATTACKER_PALETTE), by_pal(RECEIVER_PALETTE)
        row = {'frame': frame, 'attacker': actors[0], 'receiver': actors[1],
               'attacker_oam_first': min(r['index'] for r in att) < min(r['index'] for r in rcv) if att and rcv else None}
        am = [(i, m) for i, d in enumerate(attacker_desc) if (m := match(att, d))]
        rm = [(i, m) for i, d in enumerate(receiver_desc) if (m := match(rcv, d))]
        row['attacker_pose'] = am[0][0] if len(am) == 1 else None
        row['receiver_pose'] = rm[0][0] if len(rm) == 1 else None
        if len(am) == 1 and len(rm) == 1:
            a, r = am[0][1], rm[0][1]
            row['attacker_flipped'], row['receiver_flipped'] = a['flipped'], r['flipped']
            camera = actors[0]['x'] - a['origin_x']           # attacker unflipped: exact origin
            row['camera_x'] = camera
            row['attacker_origin_screen'] = a['origin_x']
            row['receiver_actor_screen_x'] = actors[1]['x'] - camera
            # Flipped receiver: origin_x = Ox_body - k where body origin = actor + profile term.
            row['receiver_body_term'] = r['origin_x'] - row['receiver_actor_screen_x']
            row['vertical'] = {'attacker_origin_y': a['origin_y'], 'receiver_origin_y': r['origin_y']}
            # Registration vs Royal: the attacker maps Royal column x to screen origin + (145 - x), so a
            # receiver part pixel at x' = x - 145 is registered at attacker origin - x'.
            pose = worker['poses'][rm[0][0]]
            registered = {(a['origin_x'] - px, a['origin_y'] + py): v
                          for (px, py), v in recipe_image(royal, pose, mapping, cache).items()}
            actual = {}
            for rec in reversed(rcv):
                for (x, y), v in oam_indices(vram, oam, rec, regs[0x2101]).items():
                    actual[rec['x'] + x, rec['y'] + y] = v
            best = None
            for dx in range(-80, 81):
                score = sum(1 for (x, y), v in actual.items() if registered.get((x - dx, y)) == v)
                if best is None or score > best[1]:
                    best = (dx, score)
            row['receiver_registration_error_px'] = best[0]
            row['receiver_pixels'] = len(actual)
            row['receiver_pixels_matching_recipe_after_shift'] = best[1]
            shadow = [rec for rec in recs if rec['palette'] == SHADOW_PALETTE]
            row['shadow_objects_x'] = sorted(rec['x'] for rec in shadow)
        rows.append(row)
    flips = Counter((r.get('attacker_flipped'), r.get('receiver_flipped')) for r in rows if 'camera_x' in r)
    return {
        'generated_by': 'tools/measure_perfect_pair.py',
        'rom_sha256': hashlib.sha256(rom).hexdigest(),
        'receiver_slot': slot,
        'frames_measured': len(rows),
        'frames_fully_matched': sum('camera_x' in r for r in rows),
        'flip_pairs': {f'{k}': v for k, v in flips.items()},
        'receiver_body_terms': dict(Counter(r['receiver_body_term'] for r in rows if 'receiver_body_term' in r)),
        'registration_errors': dict(Counter(r['receiver_registration_error_px'] for r in rows
                                            if 'receiver_registration_error_px' in r)),
        'attacker_oam_first': dict(Counter(str(r['attacker_oam_first']) for r in rows)),
        'rows': rows,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('capture', type=Path)
    parser.add_argument('rom', type=Path)
    parser.add_argument('royal', type=Path)
    parser.add_argument('--receiver-slot', type=int, default=2)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = measure(args.capture, args.rom.read_bytes(), args.royal.read_bytes(), args.receiver_slot)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=1))
    if args.output:
        args.output.write_text(json.dumps(result, indent=1) + '\n')
