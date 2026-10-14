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
FLIP_PIVOT = 8  # measured: flipped object x = origin - dx - size + 8 (docs/perfect-plex-native-trace.md)
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


def summary_range(values):
    values = [v for v in values if v is not None]
    return {'min': min(values), 'max': max(values), 'frames': len(values)} if values else None


def health_changes(context):
    """Each change of the receiver's health across the capture: [frame, before, after]."""
    out = []
    for previous, current in zip(context, context[1:]):
        if current['health'][1] != previous['health'][1]:
            out.append([current['frame'], previous['health'][1], current['health'][1]])
    return out


def after_move(context):
    """What each actor displays once both have left the Perfect-Plex actions."""
    moved = [i for i, c in enumerate(context) if c['actions'] == [600, 540]]
    if not moved:
        return None
    tail = [c for c in context[moved[-1] + 1:] if c['actions'][0] != 600 and c['actions'][1] != 540]
    return {'frames': len(tail),
            'actions': dict(Counter(str(c['actions']) for c in tail)),
            'attacker_pose_shown': dict(Counter(str(c['attacker_perfect_plex_pose']) for c in tail)),
            'receiver_pose_shown': dict(Counter(str(c['receiver_perfect_plex_pose']) for c in tail)),
            'receiver_trailing_palette6': dict(Counter(c['receiver_trailing_palette6'] for c in tail)),
            'receiver_palette6_foreign': dict(Counter(c['receiver_palette6_foreign'] for c in tail))}


def measure(capture, rom, royal, slot):
    recipes = json.loads((ROOT / 'data/perfect-receivers.json').read_text())
    # Royal-drawn receivers are registered against their Royal recipe. Receivers drawn from their own native
    # sequence (no same-identity Royal counterpart, or Scott Hall's gear over Razor) have no Royal reference;
    # their placement is checked against the editor preview instead (tools/check_preview_native.py).
    own_native = slot not in RECEIVER_SLOT_ROYAL or (slot == 5 and bytes(rom[0x4bf000:0x4bf00f]) == b'SCOTT-HALL-GEAR')
    worker = None if own_native else recipes['workers'][RECEIVER_SLOT_ROYAL[slot]]
    canonical = rom[0x70fe40:0x70fe49] in (b'ROYAL-RX2', b'ROYAL-RX3')
    attacker_desc = [descriptor(rom, long(rom, 0x710000 + (1000 + i) * 3)) for i in range(12)]
    table = long(rom, 0x71d000 + slot * 3)
    receiver_desc = [descriptor(rom, long(rom, table + i * 3)) for i in range(12)]
    # Builder palette mapping (as in build_perfect_receivers.py), to compare colour indices.
    word = lambda data, at: int.from_bytes(data[at:at + 2], 'little')
    palette_base = 0x700000 + word(rom, 0x2cf212)
    rgb = lambda c: [c >> s & 31 for s in (0, 5, 10)]
    colors = [word(royal, 0x17c26 + RECEIVER_SLOT_ROYAL.get(slot, 2) * 32 + i * 2) for i in range(16)]
    target = [word(rom, palette_base + 64 + slot * 32 + i * 2) for i in range(16)]
    mapping = [0] + [min(range(1, 16), key=lambda j: sum((a - b) ** 2 for a, b in zip(rgb(c), rgb(target[j]))))
                     for c in colors[1:]]
    cache, rows, context = {}, [], []
    for wram_path in sorted(capture.glob('frame-*-wram.bin')):
        stem = str(wram_path)[:-len('-wram.bin')]
        frame = int(Path(stem).name.split('-')[1])
        read = lambda n: Path(f'{stem}-{n}.bin').read_bytes()
        wram, vram, oam, cgram, regs = (read(n) for n in ('wram', 'vram', 'oam', 'cgram', 'registers'))
        w = lambda a: int.from_bytes(wram[a:a + 2], 'little')
        actors = [{'action': w(0x6b4 + i), 'x': w(0x5f0 + i), 'y': w(0x600 + i), 'state': w(0xbec + i)} for i in (0, 2)]
        recs = [rec for rec, image in objects(vram, oam, cgram, regs[0x2101]) if image.getbbox() and rec['y'] < 224]
        by_pal = lambda p: [r for r in recs if r['palette'] == p]
        att, rcv = by_pal(ATTACKER_PALETTE), by_pal(RECEIVER_PALETTE)
        # Palette-6 objects that directly follow each actor's body objects in OAM (shadows and the PP-7 group).
        def trailing_shadow(body):
            if not body:
                return 0
            last, count = max(r['index'] for r in body), 0
            indices = {r['index']: r for r in recs}
            while (rec := indices.get(last + 1 + count)) and rec['palette'] == SHADOW_PALETTE:
                count += 1
            return count
        # PP-7: receiver palette-6 objects whose opaque shape matches none of the attacker's shadow tiles
        # (the attacker's shadow renders correctly), i.e. objects showing foreign VRAM content.
        def trailing(body):
            if not body:
                return []
            last, out, indices = max(r['index'] for r in body), [], {r['index']: r for r in recs}
            while (rec := indices.get(last + 1 + len(out))) and rec['palette'] == SHADOW_PALETTE:
                out.append(rec)
            return out
        def pixels(rec):
            px = oam_indices(vram, oam, rec, regs[0x2101])
            # Shadow tiles are recoloured per actor, so compare opaque masks (shapes), not colour indices.
            grid = tuple(int(bool(px.get((x, y), 0))) for y in range(rec['size']) for x in range(rec['size']))
            mirrored = tuple(int(bool(px.get((rec['size'] - 1 - x, y), 0)))
                             for y in range(rec['size']) for x in range(rec['size']))
            return grid, mirrored
        reference = {g for rec in trailing(att) for g in pixels(rec)}
        foreign = [rec for rec in trailing(rcv) if pixels(rec)[0] not in reference] if reference else []
        # Shadow placement: centre of the receiver's trailing palette-6 objects vs its body's opaque centre.
        def centre(recs_):
            xs = [rec['x'] + x for rec in recs_ for (x, y) in oam_indices(vram, oam, rec, regs[0x2101])]
            return (min(xs) + max(xs)) / 2 if xs else None
        body_centre, shadow_centre = centre(rcv), centre(trailing(rcv)[:4])
        context.append({'frame': frame, 'actions': [actors[0]['action'], actors[1]['action']],
                        'health': [w(0xa78), w(0xa7a)],
                        'receiver_shadow_offset': None if body_centre is None or shadow_centre is None
                        else round(shadow_centre - body_centre, 1),
                        'receiver_palette6_foreign': len(foreign),
                        'receiver_shadow_like_objects': len(trailing(rcv)) - len(foreign),
                        'receiver_palette6_foreign_objects': [[rec['index'], rec['x'], rec['y'], rec['tile']] for rec in foreign],
                        'x': [actors[0]['x'], actors[1]['x']],
                        'attacker_perfect_plex_pose': next((i for i, d in enumerate(attacker_desc) if match(att, d)), None),
                        'receiver_perfect_plex_pose': next((i for i, d in enumerate(receiver_desc) if match(rcv, d)), None),
                        'attacker_trailing_palette6': trailing_shadow(att),
                        'receiver_trailing_palette6': trailing_shadow(rcv)})
        if actors[0]['action'] != 600 and actors[1]['action'] != 540:
            continue
        row = {'frame': frame, 'attacker': actors[0], 'receiver': actors[1],
               'attacker_oam_first': min(r['index'] for r in att) < min(r['index'] for r in rcv) if att and rcv else None}
        am = [(i, m) for i, d in enumerate(attacker_desc) if (m := match(att, d))]
        rm = [(i, m) for i, d in enumerate(receiver_desc) if (m := match(rcv, d))]
        row['attacker_pose'] = am[0][0] if len(am) == 1 else None
        # Several steps can share one receiving drawing (own-art receivers hold one drawing for steps 2-9);
        # the receiver stream advances with the attacker's, so take the attacker's step when it is among them.
        if len(rm) > 1 and len(am) == 1 and any(i == am[0][0] for i, _ in rm):
            rm = [(i, m) for i, m in rm if i == am[0][0]]
        row['receiver_pose'] = rm[0][0] if len(rm) == 1 else None
        if len(am) == 1 and len(rm) == 1:
            a, r = am[0][1], rm[0][1]
            row['attacker_flipped'], row['receiver_flipped'] = a['flipped'], r['flipped']
            # Measured flip rule: a flipped object lands at origin - dx - size + FLIP_PIVOT, so the
            # match() value (oam_x + dx + size) is origin + FLIP_PIVOT for flipped actors.
            true = lambda m: m['origin_x'] - (FLIP_PIVOT if m['flipped'] else 0)
            camera = actors[0]['x'] - true(a)
            row['camera_x'] = camera
            row['attacker_origin_screen'] = true(a)
            row['receiver_actor_screen_x'] = actors[1]['x'] - camera
            row['receiver_object_term'] = r['origin_x'] - row['receiver_actor_screen_x']
            row['receiver_body_term'] = true(r) - row['receiver_actor_screen_x']
            row['vertical'] = {'attacker_origin_y': a['origin_y'], 'receiver_origin_y': r['origin_y']}
            # Registration vs Royal: the attacker maps Royal column x to descriptor column c = 145 - x,
            # drawn at O + c unflipped or O + FLIP_PIVOT - 1 - c flipped. A receiver part pixel at
            # x' = x - 145 is therefore registered at O - x' or O + FLIP_PIVOT - 1 + x'.
            if own_native:
                rows.append(row)
                continue
            pose = worker['poses'][rm[0][0]]
            o = true(a)
            if canonical:   # attacker drawings unmirrored: descriptor column c = Royal column u
                place = (lambda px: o + FLIP_PIVOT - 1 - px) if a['flipped'] else (lambda px: o + px)
            else:           # legacy RX1 / v0.16: attacker mirrored, c = 145 - x = -u
                place = (lambda px: o + FLIP_PIVOT - 1 + px) if a['flipped'] else (lambda px: o - px)
            registered = {(place(px), a['origin_y'] + py): v
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
        'receiver_source': 'own_native' if own_native else 'royal',
        'build_marker': rom[0x70fe40:0x70fe49].decode('latin-1'),
        'frames_measured': len(rows),
        'frames_fully_matched': sum('camera_x' in r for r in rows),
        'flip_pairs': {f'{k}': v for k, v in flips.items()},
        'receiver_object_terms': dict(Counter(r['receiver_object_term'] for r in rows if 'receiver_object_term' in r)),
        'receiver_body_terms': dict(Counter(r['receiver_body_term'] for r in rows if 'receiver_body_term' in r)),
        'actor_spacing': dict(Counter(r['receiver']['x'] - r['attacker']['x'] for r in rows if 'camera_x' in r)),
        'registration_errors': dict(Counter(r['receiver_registration_error_px'] for r in rows
                                            if 'receiver_registration_error_px' in r)),
        'attacker_oam_first': dict(Counter(str(r['attacker_oam_first']) for r in rows)),
        'receiver_trailing_palette6_during_move': dict(Counter(c['receiver_trailing_palette6'] for c in context
                                                               if c['actions'] == [600, 540])),
        'receiver_palette6_foreign_during_move': dict(Counter(c['receiver_palette6_foreign'] for c in context
                                                              if c['actions'] == [600, 540])),
        'receiver_shadow_like_objects_during_move': dict(Counter(c['receiver_shadow_like_objects'] for c in context
                                                                 if c['actions'] == [600, 540])),
        'frames_with_foreign_palette6_during_move': sum(1 for c in context
                                                        if c['actions'] == [600, 540] and c['receiver_palette6_foreign']),
        'receiver_shadow_offset_during_move': summary_range([c['receiver_shadow_offset'] for c in context
                                                             if c['actions'] == [600, 540]]),
        'receiver_health_changes': health_changes(context),
        'after_move': after_move(context),
        'rows': rows,
        'all_frames': context,
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
