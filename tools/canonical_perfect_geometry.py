"""Canonical-facing Perfect-Plex geometry (needs the Royal ROM; writes geometry only).

Raw's art faces right when an actor is unflipped. Royal's captured Perfect faces right and
the receiver faces left. So the attacker drawings stay as captured, and the receiver
drawings are mirrored.

The measured renderer rule places a flipped object at origin - dx - size + 8, so a
flipped pixel at descriptor column c lands at origin + 7 - c. With the pair spacing fixed at
PAIR_SPACING by the init hook, a receiver body profile offset of PAIR_SPACING + 7 registers
both facings exactly against the attacker (docs/perfect-plex-native-trace.md).

Outputs:
- editor/royal-import-layouts.js: attacker `finisher[].chunks` repacked for the unmirrored drawing,
  regenerated hook `programs`, `victim[].translate` for the generic receiving path, and an
  `orientation` marker.
- data/perfect-receivers.json: per pose `canonical_chunks`, `body_dx`, `shadow_dx`.

    python3 tools/canonical_perfect_geometry.py ROYAL_ROM
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from inspect_rom import tile
from royal_rumble_sprites import decode_tile
from build_shawn_superkick_animation import pack

ROOT = Path(__file__).resolve().parents[1]
ROYAL_SHA256 = '51c53e36ed0b959b0695fc6ef036fa7302d1c995eca35c28261d6f3cb77df0ca'
LAYOUTS = ROOT / 'editor/royal-import-layouts.js'
RECEIVERS = ROOT / 'data/perfect-receivers.json'
FLIP_PIVOT = 8
# Receiver descriptor column for Royal-relative column u is MIRROR_SHIFT - u. The shift keeps every packed
# chunk inside Raw's 7-bit descriptor x range; the body profile offset compensates for it.
MIRROR_SHIFT = 2


def pixels(rom, ref, cache):
    if ref is None:   # blank tile (as editor/royal-import-core.js tile(data, null))
        return [0] * 64
    key = tuple(ref)
    if key not in cache:
        cache[key] = tile(decode_tile(rom, ref[0], bool(ref[1]))[0], 0, 4)
    return cache[key]


def paint(rom, parts, size, origin, mirror, cache):
    """Opaque pixels of a Royal drawing; parts listed first sit on top (native OAM order)."""
    image = Image.new('P', (size, size))
    for part in reversed(parts):
        s = part['size']
        for y in range(s):
            for x in range(s):
                sx = s - 1 - x if part['hflip'] else x
                sy = s - 1 - y if part['vflip'] else y
                value = pixels(rom, part['refs'][(sy // 8) * (s // 8) + sx // 8], cache)[sy % 8 * 8 + sx % 8]
                if not value:
                    continue
                u = part['x'] + x
                cx = origin[0] + (MIRROR_SHIFT - u if mirror else u)
                cy = origin[1] + part['y'] + y
                if not (0 <= cx < size and 0 <= cy < size):
                    raise ValueError('Drawing exceeds its canvas')
                image.putpixel((cx, cy), value)
    return image


def chunks_for(image, size, origin):
    options = [o for o in pack(image, size) if o[0][0] + 2 <= 17 and o[0][1] + 4 <= 64]
    if not options:
        raise ValueError('No legal object packing')
    (count, cost), chosen = min(options, key=lambda o: (o[0][1], o[0][0]))
    result = sorted(([x - origin[0], y - origin[1], s] for x, y, s, _ in chosen), key=lambda c: (-c[2], c[1], c[0]))
    for x, y, s in result:
        if not (-64 <= x < 64 and -105 <= y < 23):
            raise ValueError('Chunk outside Raw descriptor range')
    return result


def programs(frames):
    """Slot-12 hook programs; the primary worker serves IDs up to 1000 + frames (Perfect-Plex and exit frames)."""
    import import_perfect_plex as plex
    from build_perfect_slot import hook_worker, hook_lookup
    limit = ((1000 + frames) * 3).to_bytes(2, 'little')

    def worker(secondary, native):
        code = hook_worker(secondary, native)
        return code.replace(bytes.fromhex('c9 76 08'), bytes.fromhex('c9 7f 08')) if secondary else \
            code.replace(bytes.fromhex('c9 b2 0b'), b'\xc9' + limit)

    def lookup(native):
        code = hook_lookup(native)
        for before, after in [(0x7dc000, 0x749800), (0x7dc002, 0x749802)]:
            code = code.replace(before.to_bytes(3, 'little'), after.to_bytes(3, 'little'))
        return code
    return {variant: [[at, list(code), hook] for at, code, hook in
                      [(0x70f000, worker(False, native), 0xecc1), (0x70f100, worker(True, native), 0xed19),
                       (0x70f200, lookup(native), 0x2cf6e4), (0x70f300, plex.init_hook(), 0x2cecb0),
                       (0x70f400, plex.sequence_hook(), 0xf073)]]
            for variant, native in [('stock', False), ('native', True)]}


def load_layouts():
    text = LAYOUTS.read_text()
    return json.loads(text[text.index('=') + 1:].strip().rstrip(';'))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('royal', type=Path)
    args = parser.parse_args()
    rom = args.royal.read_bytes()
    if hashlib.sha256(rom).hexdigest() != ROYAL_SHA256:
        raise SystemExit('Expected the unmodified Royal Rumble USA ROM')
    import import_perfect_plex as plex
    spacing = plex.PAIR_SPACING
    cache = {}

    # Attacker: unmirrored on the 112-pixel canvas used by editor/royal-import-core.js (origin 56,100).
    manifest = load_layouts()
    for f in manifest['finisher']:
        image = paint(rom, f['parts'], 112, (56, 100), False, cache)
        f['chunks'] = chunks_for(image, 112, (56, 100))
    manifest['orientation'] = {'attacker': 'unmirrored (faces right unflipped)', 'pair_spacing': spacing,
                               'flip_pivot': FLIP_PIVOT}

    # Generic receiving path (stock Raw parts for receivers without Royal art): flipped receiver on the
    # attacker's right; centre the stock parts on the Royal receiver's body.
    for row in manifest['victim']:
        native_centre = (row['native_bbox'][0] + row['native_bbox'][2]) / 2
        royal_centre = (row['royal_relative_bbox'][0] + row['royal_relative_bbox'][2]) / 2
        row['translate'] = [round(spacing + FLIP_PIVOT - 1 - native_centre - royal_centre), row['translate'][1]]

    manifest['programs'] = programs(len(manifest['finisher']) + len(manifest.get('exit', {}).get('attacker', {}).get('frames', [])))
    LAYOUTS.write_text('window.RAW_ROYAL_IMPORT_MANIFEST=' + json.dumps(manifest, separators=(',', ':')) + ';\n')

    # Receivers: mirrored on a 144-pixel canvas (origin 72,105).
    receivers = json.loads(RECEIVERS.read_text())
    for worker_row in receivers['workers']:
        for pose in worker_row['poses']:
            image = paint(rom, pose['parts'], 144, (72, 105), True, cache)
            pose['canonical_chunks'] = chunks_for(image, 144, (72, 105))
            centre = (pose['bbox'][0] + pose['bbox'][2]) / 2
            pose['body_dx'] = spacing + FLIP_PIVOT - 1 - MIRROR_SHIFT
            # Stock shadow extent is [-14, 18) from its origin; flipped or not, centring it under the body
            # gives the same profile offset (derivation in docs/perfect-plex-native-trace.md).
            pose['shadow_dx'] = round(spacing + 5.5 - centre)   # independent of MIRROR_SHIFT
    receivers['canonical'] = {'receiver': 'mirrored (faces right unflipped)', 'pair_spacing': spacing,
                              'mirror_shift': MIRROR_SHIFT,
                              'flip_pivot': FLIP_PIVOT, 'canvas': 144, 'origin': [72, 105]}
    RECEIVERS.write_text(json.dumps(receivers, separators=(',', ':')) + '\n')
    counts = [len(p['canonical_chunks']) for w in receivers['workers'] for p in w['poses']]
    print('attacker poses', len(manifest['finisher']), 'receiver poses', len(counts), 'max receiver chunks', max(counts))


if __name__ == '__main__':
    main()
