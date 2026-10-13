"""Independently inspect emitted Sting tiles, head scope and preserved music.

This checks ROM structure and declared pixel landmarks, not visual likeness.
Reviewed head masks may cross the neckline where authored hair covers shoulders.
"""
import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from build_bret_gear import planar
from build_nwo_gear import CONFIGS, programs
from inspect_rom import tile
from scott_frame_catalog import catalog, raster

ROOT = Path(__file__).resolve().parents[1]
SKIN = {7, 9, 10, 11, 12, 15}
FINISHER_TABLES = [0x2dd36f, 0x2dd387, 0x2dd39f, 0x2dd3b7, 0x2dd3cf, 0x2dd3e7]
DEATHLOCK = [('primary', i) for i in [623, 729, 730, 731, 732, 737, 738]] + [
    ('secondary', i) for i in [617, 618, 619, 620, 621, 622, 628]]


def cells(frame):
    """World coordinates for every tile cell, including hidden/transparent cells."""
    for part in frame['parts']:
        size = part['size']
        for y in range(size):
            for x in range(size):
                sx = size - 1 - x if part['hflip'] else x
                sy = size - 1 - y if part['vflip'] else y
                ref = part['refs'][(sy // 8) * (size // 8) + sx // 8]
                yield (part['x'] + x, part['y'] + y), ref, sy % 8 * 8 + sx % 8


def emitted(frame, rom, config):
    """Read actual descriptor references; do not call the art authoring function."""
    out = copy.deepcopy(frame)
    kind = frame['kind']
    table = config['primary_table'] if kind == 'primary' else config['secondary_table']
    pointers = config['pointers'] if kind == 'primary' else config['secondary_pointers']
    address = int.from_bytes(rom[table + frame['index'] * 3:table + frame['index'] * 3 + 3], 'little')
    bank = 0x60 if kind == 'primary' else 0x61
    assert address >> 16 == bank and address & 65535, (kind, frame['index'], 'descriptor address', hex(address))
    descriptor = bytearray(rom[address:address + frame['length']])
    assert len(descriptor) == frame['length']
    original = bytearray(rom[frame['offset']:frame['offset'] + frame['length']])
    for part in out['parts']:
        for ref in part['refs']:
            at = ref['relative']
            ident = int.from_bytes(descriptor[at:at + 2], 'little')
            assert ident >= 0xc000, (kind, frame['index'], 'stock tile reference', ident)
            source = int.from_bytes(rom[pointers + (ident & 0x3fff) * 3:pointers + (ident & 0x3fff) * 3 + 3], 'little')
            assert config['packets_start'] <= source and source + 32 <= config['packets_end'], (kind, frame['index'], hex(source))
            ref['pixels'] = tile(rom[source:source + 32], 0, 4)
            # All native OBJ positions, control bytes and flip bits must match.
            descriptor[at:at + 2] = original[at:at + 2]
    assert descriptor == original, (kind, frame['index'], 'native descriptor topology changed')
    return out


def region(frame, atlas):
    """Reviewed registered head area plus locations of explicit fallback masks."""
    result = set()
    key = str(frame['index']) if frame['kind'] == 'primary' else 'secondary:' + str(frame['index'])
    entry = atlas['heads'].get(key)
    if entry:
        seed = atlas['templates'][entry['template']]
        sx, sy, dx, dy = entry['transform']
        world = lambda x, y: (sx * x + dx, sy * y + dy)
        l, t, r, b = seed['box']
        # Older seeds use inclusive bounds; union with explicit paint also
        # supports replacement seeds authored with exclusive right/bottom.
        result.update(world(x, y) for y in range(t, b + 1) for x in range(l, r + 1))
        for name in ['paint', 'hair', 'face', 'face_shadow', 'eyes', 'cheeks', 'mouth', 'nose', 'occlusion']:
            result.update(world(q[0], q[1]) for q in seed.get(name, []))
    if not (frame['kind'] == 'secondary' and frame['index'] < 426):
        masks = {ref['field']: atlas.get('tile_masks', {}).get(hashlib.sha256(planar(ref['pixels'])).hexdigest(), {})
                 for part in frame['parts'] for ref in part['refs']}
        result.update(q for q, ref, k in cells(frame) if str(k) in masks[ref['field']])
    return result


def mechanics_checks():
    """Exercise overlap erasure, flipped placement and foreground occlusion."""
    import sting_rebuild_art as art
    import register_sting_heads as registrar
    lower = {'field': 100, 'relative': 5, 'pixels': [7] * 64}
    upper = {'field': 200, 'relative': 8, 'pixels': [0] * 64}
    # The foremost OBJ has both flips. An erased cell is initially opaque.
    upper['pixels'][(7 - 3) * 8 + (7 - 2)] = 9
    frame = {'kind': 'primary', 'index': 900, 'parts': [
        {'x': 0, 'y': 0, 'size': 8, 'hflip': True, 'vflip': True, 'refs': [upper]},
        {'x': 0, 'y': 0, 'size': 8, 'hflip': False, 'vflip': False, 'refs': [lower]}]}
    seed = {'piece': 900, 'box': [0, 0, 7, 7], 'replace_head': True,
            'paint': [[2, 3, 0], [4, 2, 5], [6, 1, 13]], 'occlusion': [[6, 1]]}
    fixture = {'heads': {'900': {'template': 'test', 'transform': [1, 1, 0, 0]}},
               'templates': {'test': seed}, 'tile_masks': {}}
    old_atlas, old_catalog = art.atlas, registrar.catalog
    try:
        art.atlas = lambda: fixture
        changes = art.author(frame)
        assert changes[100][3 * 8 + 2] == changes[200][(7 - 3) * 8 + (7 - 2)] == 0
        assert changes[200][(7 - 2) * 8 + (7 - 4)] == 5
        assert changes[100][2 * 8 + 4] == 7
        assert changes[200][(7 - 1) * 8 + (7 - 6)] == 0
        assert changes[100][1 * 8 + 6] == 7
        registrar.catalog = lambda *args: [frame]
        registered = registrar.register(b'', b'', {'test': seed})
        digest = hashlib.sha256(planar(lower['pixels'])).hexdigest()
        fallback = registered['tile_masks'][digest]
        assert str(3 * 8 + 2) not in fallback
        assert all(value != 0 for mask in registered['tile_masks'].values() for value in mask.values())
    finally:
        art.atlas, registrar.catalog = old_atlas, old_catalog
    return {'all_overlapping_objs_erased': True, 'flipped_foremost_obj_painted': True,
            'foreground_pixels_and_transparency_restored': True, 'erasure_not_transferred_by_tile_hash': True}


def landmarks(seed, points, palette):
    declared = seed['landmarks']
    eyes, nose, mouth = [list(map(tuple, declared[name])) for name in ['eyes', 'nose', 'mouth']]
    assert len(eyes) >= 2 and len(mouth) >= 2 and nose, 'Frontal eyes, nose and mouth must be explicit'
    assert all(points.get(q) == 1 for q in eyes + mouth), ('Emitted eye/lip differs from landmark', eyes, mouth)
    assert all(points.get(q) in {4, 5, 6, 8, 13} for q in nose), ('Nose tip must be a separate gray plane', nose)
    assert len({q[1] for q in eyes}) == 1, 'Front eyes must share their authored row'
    eye_y = eyes[0][1]
    left, right = min(x for x, y in eyes), max(x for x, y in eyes)
    assert right - left >= 2
    assert any(points.get((x, eye_y)) in {4, 5, 6, 8, 13} for x in range(left + 1, right)), 'Eye sockets merged into a black band'
    assert eye_y < min(y for x, y in nose) <= max(y for x, y in nose) < min(y for x, y in mouth), 'Nose/lip row order'
    assert max(x for x, y in mouth) - min(x for x, y in mouth) <= right - left + 2
    # Count actual emitted gray planes in the face crop, excluding black/hair.
    shades = set()
    for (x, y), value in points.items():
        if left - 1 <= x <= right + 1 and eye_y - 4 <= y <= max(y for x, y in mouth) + 2:
            rgb = tuple((palette[value] >> shift & 31) * 255 // 31 for shift in [0, 5, 10])
            if value in {4, 5, 6, 8, 13} and max(rgb) - min(rgb) <= 20:
                shades.add(rgb)
    assert len(shades) >= 4, ('Insufficient facial gray planes', sorted(shades))
    return {'eyes': eyes, 'nose': nose, 'mouth': mouth, 'gray_planes_in_face_crop': sorted(shades),
            'separate_eye_sockets_and_lower_nose_lips': True, 'visual_likeness_verified': False}


def audio_preserved(before, after):
    # Existing custom allocation, theme-to-bank assignments and upload pointers.
    assert before[0x3c0000:0x400000] == after[0x3c0000:0x400000], 'Custom MIDI allocations changed'
    assert before[0x11903:0x11948] == after[0x11903:0x11948], 'Audio bank directory or theme assignments changed'
    count_at = 236599
    count = int.from_bytes(before[count_at:count_at + 2], 'little')
    assert count == 94
    assert before[count_at:count_at + 2 + count * 7] == after[count_at:count_at + 2 + count * 7]
    blocks = []
    for i in range(count):
        at = count_at + 2 + i * 7
        length = int.from_bytes(before[at:at + 2], 'little')
        source = int.from_bytes(before[at + 2:at + 5], 'little') & 0x3fffff
        assert before[source:source + length] == after[source:source + length], ('Stock audio upload changed', i)
        blocks.append((source, length))
    return {'custom_midi_allocation_sha256': hashlib.sha256(after[0x3c0000:0x400000]).hexdigest(),
            'custom_midi_allocations_unchanged': True, 'theme_bank_directory_and_assignments_unchanged': True,
            'stock_sample_instrument_driver_uploads_checked': len(blocks), 'stock_audio_upload_bytes_unchanged': True}


def byte_scope(before, after, config):
    assert len(before) == len(after) == 0x800000
    allowed = bytearray(len(after))
    regions = [(config['frames_start'], config['frames_end']),
               (config['packets_start'], config['packets_end']),
               (config['pointers'], config['pointer_end']),
               (config['secondary_pointers'], config['secondary_pointer_end']),
               (config['primary_table'], config['primary_table'] + 998 * 3),
               (config['secondary_table'], config['secondary_table'] + 722 * 3),
               (config['signature_offset'], config['signature_offset'] + len(config['signature'])),
               (0xffdc, 0xffe0), (0x40ffdc, 0x40ffe0)]
    regions.extend((0x2cc5ba + i * 2, 0x2cc5bc + i * 2) for i in [4, 5, 13])
    for table in FINISHER_TABLES:
        assert before[table + 14:table + 16] == after[table + 14:table + 16] == after[table + 2:table + 4], 'Deathlock assignment changed'
    # Version change affects the marker only: every dispatcher/worker stays
    # byte-identical, including other wrestlers' code and installed hooks.
    for program in programs():
        at = program['offset']
        assert before[at:at + 256] == after[at:at + 256], ('Sprite program changed', hex(at))
        if 'hook' in program:
            at = program['hook']
            assert before[at:at + 4] == after[at:at + 4]
    for start, end in regions:
        allowed[start:end] = b'\x01' * (end - start)
    unexpected = [i for i, (old, new) in enumerate(zip(before, after)) if old != new and not allowed[i]]
    assert not unexpected, ('ROM change outside Sting tiles, palette, marker/checksum', [hex(i) for i in unexpected[:12]])
    assert after[config['signature_offset']:config['signature_offset'] + len(config['signature'])] == config['signature'].encode()
    changed = sum(old != new for old, new in zip(before, after))
    return {'changed_bytes': changed, 'outside_reserved_sting_regions_unchanged': True,
            'dispatchers_workers_and_hooks_unchanged': True, 'six_deathlock_assignments_preserved': True}


def verify(args):
    before, after = args.before.read_bytes(), args.after.read_bytes()
    config = CONFIGS[7]
    old_atlas = json.loads(args.before_atlas.read_text())
    atlas = json.loads(args.atlas.read_text())
    native = catalog(before, args.wram.read_bytes(), 2)
    assert len(native) == 1720
    palette_before = [int.from_bytes(before[0x2cc5ba + i * 2:0x2cc5bc + i * 2], 'little') for i in range(16)]
    palette_after = [int.from_bytes(after[0x2cc5ba + i * 2:0x2cc5bc + i * 2], 'little') for i in range(16)]
    palette_changes = [i for i in range(16) if palette_before[i] != palette_after[i]]
    assert set(palette_changes) <= {4, 5, 13}, ('Body/scorpion palette changed', palette_changes)
    lower = protected_cells = changed_head_cells = 0
    protected = Counter()
    emitted_frames = {}
    for frame in native:
        old = emitted(frame, before, config)
        new = emitted(frame, after, config)
        key = frame['kind'], frame['index']
        emitted_frames[key] = new
        scope = region(frame, old_atlas) | region(frame, atlas)
        old_refs = {ref['field']: ref for part in old['parts'] for ref in part['refs']}
        new_refs = {ref['field']: ref for part in new['parts'] for ref in part['refs']}
        is_lower = frame['kind'] == 'secondary' and frame['index'] < 426
        for q, ref, k in cells(frame):
            a, b = old_refs[ref['field']]['pixels'][k], new_refs[ref['field']]['pixels'][k]
            if is_lower or q not in scope:
                assert a == b, ('Pixel changed outside reviewed head masks', key, q, ref['relative'], k, a, b)
                assert palette_before[a] == palette_after[b], ('Protected body pixel changed color', key, q, a)
                protected_cells += 1
                protected['warm_skin' if a in SKIN else 'scorpion_grays' if a in {6, 8} else 'black_gear' if a in {1, 2, 3} else 'other'] += 1
            elif a != b:
                changed_head_cells += 1
        if is_lower:
            lower += 1
    assert lower == 426
    front_seed = atlas['templates']['front']
    front_key = front_seed.get('kind', 'primary'), front_seed['piece']
    front = landmarks(front_seed, raster(emitted_frames[front_key])[0], palette_after)
    deathlock = {}
    for kind, index in DEATHLOCK:
        identifier = str(index) if kind == 'primary' else 'secondary:' + str(index)
        assert identifier in atlas['heads'], ('Deathlock head is not registered', identifier)
        area = region(next(f for f in native if f['kind'] == kind and f['index'] == index), atlas)
        points = raster(emitted_frames[kind, index])[0]
        count = sum(v in {4, 5, 13} for q, v in points.items() if q in area)
        assert count >= 4, ('Visible Deathlock head lost grayscale makeup', identifier, count)
        deathlock[identifier] = count
    return {'before_sha256': hashlib.sha256(before).hexdigest(), 'after_sha256': hashlib.sha256(after).hexdigest(),
            'all_1720_descriptors_private_with_native_obj_topology': True,
            'all_426_wrestler_specific_lower_drawings_byte_exact': True,
            'protected_tile_cells_checked': protected_cells, 'protected_cell_categories': dict(protected),
            'changed_tile_cells_inside_reviewed_head_masks': changed_head_cells,
            'head_mask_union_may_include_shoulder_hair_overlap': True,
            'palette_indices_changed': palette_changes, 'body_skin_glove_and_scorpion_palette_unchanged': True,
            'native_frontal_landmarks': front, 'deathlock_private_heads_grayscale_pixels': deathlock,
            'replacement_mechanics': mechanics_checks(), 'audio_preservation': audio_preserved(before, after),
            'rom_byte_scope': byte_scope(before, after, config),
            'visual_likeness_verified': False, 'complete_live_animation_coverage_verified': False,
            'limitations': 'Checks emitted ROM pixels and declared head scope. Visual likeness and movement need separate native captures and user review.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'wram']:
        parser.add_argument(name, type=Path)
    parser.add_argument('--before-atlas', type=Path, required=True)
    parser.add_argument('--atlas', type=Path, default=ROOT / 'data/sting-rebuild-heads.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
