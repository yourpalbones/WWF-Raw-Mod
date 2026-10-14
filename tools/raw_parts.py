"""Resolve any slot's frame parts to pixels the way the game routes them (stock, gear and imported slots).

Routing modelled here (each step was traced in the ROM; see docs/complete-wrestler-art.md):
- Frame index -> descriptor. The part loader ($80:ECC1 primary, $80:ED19 secondary) reads the slot's directory
  (selector table $2D:D513/$2D:D52D primary, $2D:D547/$2D:D561 secondary). Indices at or above 527 (primary)
  or 426 (secondary) come from the common directory (selector 8). The gear dispatchers ($4B:E100/$4B:E200)
  use a gear slot's own 998/722-entry tables when the entry is non-zero. The imported slot 12 uses $71:0000 and
  $71:1000.
- Descriptor -> tile IDs and object positions (header, control bytes, x/y delta tables at $00:BF2E..$00:BF8E).
- Tile ID -> packet. The lookup ($AC:F6E4, chained through $4B:E000 and the slot-12 hook) chooses by the
  descriptor's bank. Gear banks map private IDs (C000+) through that gear's pointer table. Perfect's banks
  $72-$75 map through $7D:0000 (primary) or $74:9800 (secondary). Everything else uses the stock directory
  (data/raw-tile-directory.json).

Pixels are only returned in memory; nothing is written.

    python3 tools/raw_parts.py ROM --slot N --part 0x177 [--png OUT.png]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = json.loads((ROOT / 'data/raw-tile-directory.json').read_text())
TABLES = {'primary': (0x2DD513, 0x2DD52D, 527, 998), 'secondary': (0x2DD547, 0x2DD561, 426, 722)}
COMMON_SELECTOR = 8
ORIGIN = {'primary': (0x70, 0x4A), 'secondary': (0x78, 0x3A)}
DELTAS = {'primary': (0xBF2E, 0xBF4E), 'secondary': (0xBF6E, 0xBF8E)}
# Gear slots: signature, own tables and private pointer tables (editor/*-layouts.js manifests, current revisions).
GEAR = {
    5: {'signature': (0x4BF000, b'SCOTT-HALL-GEAR3'), 'tables': (0x4BC000, 0x4BD000), 'banks': (0x42, 0x43),
        'pointers': (0x4B0000, 0x4B0000)},
    10: {'signature': (0x416000, b'NASH-NATIVE-GEAR2'), 'tables': (0x410000, 0x411000), 'banks': (0x4C, 0x4D),
         'pointers': (0x5F0000, 0x5F0000)},
    9: {'signature': (0x417000, b'SYXX-NATIVE-GEAR3'), 'tables': (0x413000, 0x414000), 'banks': (0x56, 0x57),
        'pointers': (0x5FA000, 0x5FA000)},
    7: {'signature': (0x6FF000, b'STING-NATIVE-GEAR4'), 'tables': (0x6FC000, 0x6FD000), 'banks': (0x60, 0x61),
        'pointers': (0x6E0000, 0x6F0000)},
}
PERFECT = {'signature': (0x70FE00, b'PERFECT-SLOT'), 'tables': (0x710000, 0x711000)}


def long(rom, at):
    return rom[at] | rom[at + 1] << 8 | rom[at + 2] << 16


def file_offset(address, size):
    bank = address >> 16
    if size > 0x400000 and 0x40 <= bank <= 0x7D:
        return address
    if size > 0x400000 and bank < 0x40 and address & 0x8000:
        return address + 0x400000
    return address & 0x3FFFFF


def active_gear(rom, slot):
    gear = GEAR.get(slot)
    if not gear or len(rom) < 0x600000:
        return None
    at, text = gear['signature']
    return gear if bytes(rom[at:at + len(text)]) == text else None


def has_perfect(rom):
    at, text = PERFECT['signature']
    return len(rom) >= 0x800000 and bytes(rom[at:at + len(text)]) == text


def descriptor_address(rom, slot, kind, index):
    table, banks, own_count, total = TABLES[kind]
    if not 0 <= index < total:
        raise ValueError(f'{kind} index {index} out of range')
    if slot == 12:
        if not has_perfect(rom):
            raise ValueError('ROM has no imported slot 12')
        return long(rom, PERFECT['tables'][kind == 'secondary'] + index * 3)
    gear = active_gear(rom, slot)
    if gear:
        entry = long(rom, gear['tables'][kind == 'secondary'] + index * 3)
        if entry & 0xFFFF:
            return entry
    selector = slot if index < own_count else COMMON_SELECTOR
    directory = file_offset((rom[banks + selector * 2] << 16) | int.from_bytes(rom[table + selector * 2:table + selector * 2 + 2], 'little'), len(rom))
    entry = directory + index * 3   # stock directory entries are [bank, low, high]
    return rom[entry] << 16 | rom[entry + 1] | rom[entry + 2] << 8


def packet_length(rom, offset):
    return 4 + sum(bin(b).count('1') for b in rom[offset:offset + 4])


def decode_packet(rom, offset):
    """In-ring mask packet -> 32 planar bytes (see docs/in-ring-sprites.md)."""
    out, cursor = bytearray(32), offset + 4
    for i in range(32):
        mask = rom[offset + i // 8]
        if mask >> (7 - i % 8) & 1:
            out[i] = rom[cursor]
            cursor += 1
    return bytes(out)


def planar_pixels(raw):
    return [sum(((raw[(p // 2) * 16 + y * 2 + p % 2] >> (7 - x)) & 1) << p for p in range(4))
            for y in range(8) for x in range(8)]


def tile_source(rom, kind, tile_id, descriptor_bank):
    """(file offset, compressed) for a tile ID in a descriptor stored in descriptor_bank."""
    for gear in GEAR.values():
        if descriptor_bank in gear['banks'] and tile_id >= 0xC000:
            pointers = gear['pointers'][descriptor_bank == gear['banks'][1]]
            return file_offset(long(rom, pointers + (tile_id & 0x3FFF) * 3), len(rom)), False
    if 0x72 <= descriptor_bank <= 0x75 and tile_id >= 0xC000:
        pointers = 0x749800 if descriptor_bank >= 0x74 else 0x7D0000
        return long(rom, pointers + (tile_id & 0x3FFF) * 3), True
    info = DIRECTORY['kinds'][kind]
    if tile_id < info['threshold']:
        return ((info['direct_bank'] << 16) + info['direct_base'] + tile_id * 32) & 0x3FFFFF, False
    index = tile_id - info['threshold']
    start, page = info['groups'][index // 128]
    return start + DIRECTORY['pages'][str(page)][index % 128], True


def tile_pixels(rom, kind, tile_id, descriptor_bank):
    offset, compressed = tile_source(rom, kind, tile_id, descriptor_bank)
    raw = decode_packet(rom, offset) if compressed else bytes(rom[offset:offset + 32])
    return planar_pixels(raw), offset, compressed


def parse_descriptor(rom, kind, address):
    """Objects of one frame part: [{x, y, size, hflip, vflip, tiles: [(tile_id, field_offset)]}]."""
    offset = file_offset(address, len(rom))
    total, large = rom[offset], rom[offset + 1]
    if large > total or total > 64:
        raise ValueError(f'Invalid descriptor at {address:06x}')
    cursor, (x, y) = offset + 2, ORIGIN[kind]
    x_table, y_table = DELTAS[kind]
    parts = []
    for obj in range(total):
        control = rom[cursor]
        cursor += 1
        if not control:
            x, y = rom[cursor], rom[cursor + 1]
            cursor += 2
        else:
            dx, dy = control >> 4, control & 15
            if dx:
                x = (x + int.from_bytes(rom[x_table + dx * 2:x_table + dx * 2 + 2], 'little')) & 255
            else:
                x = rom[cursor]
                cursor += 1
            if dy:
                y = (y + int.from_bytes(rom[y_table + dy * 2:y_table + dy * 2 + 2], 'little')) & 255
            else:
                y = rom[cursor]
                cursor += 1
        size = 16 if obj < large else 8
        tiles = []
        for _ in range(4 if size == 16 else 1):
            tiles.append((int.from_bytes(rom[cursor:cursor + 2], 'little'), cursor))
            cursor += 2
        px = x & 127
        parts.append({'x': px - 128 if px & 64 else px, 'y': (y & 127) - 105, 'size': size,
                      'hflip': bool(x & 128), 'vflip': bool(y & 128), 'tiles': tiles})
    return parts, offset, cursor - offset


def resolve_part(rom, slot, part_id):
    """A profile part ID (bit 15 = secondary) -> objects with tile pixels and their sources."""
    kind = 'secondary' if part_id & 0x8000 else 'primary'
    index = part_id & 0x7FFF
    address = descriptor_address(rom, slot, kind, index)
    parts, offset, length = parse_descriptor(rom, kind, address)
    bank = offset >> 16 if len(rom) > 0x400000 and offset >= 0x400000 else None
    for part in parts:
        part['pixels'], part['sources'] = [], []
        for tile_id, _ in part['tiles']:
            pixels, source, compressed = tile_pixels(rom, kind, tile_id, bank if bank is not None else -1)
            part['pixels'].append(pixels)
            part['sources'].append((source, compressed))
    return {'kind': kind, 'index': index, 'descriptor': offset, 'length': length, 'parts': parts}


def raster(parts, dx=0, dy=0, flip=False, into=None):
    """Paint objects (first listed on top) into {(x, y): colour}; flip mirrors about the actor origin."""
    out = {} if into is None else into
    for part in reversed(parts):
        s = part['size']
        for y in range(s):
            for x in range(s):
                sx = s - 1 - x if part['hflip'] else x
                sy = s - 1 - y if part['vflip'] else y
                value = part['pixels'][(sy // 8) * (s // 8) + sx // 8][sy % 8 * 8 + sx % 8]
                if not value:
                    continue
                px = part['x'] + x
                out[(dx + (-px - 1 if flip else px), dy + part['y'] + y)] = value
    return out


def profile_parts(rom, profile_address):
    """Entries [id, dx, dy] of a stock profile (ends at FFFF)."""
    at, entries = file_offset(profile_address, len(rom)), []
    while (part := rom[at] | rom[at + 1] << 8) != 0xFFFF:
        dx, dy = rom[at + 2], rom[at + 3]
        entries.append((part, dx - 256 if dx > 127 else dx, dy - 256 if dy > 127 else dy))
        at += 4
    return entries


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--slot', type=int, required=True)
    parser.add_argument('--part', type=lambda s: int(s, 0), required=True)
    parser.add_argument('--png', type=Path)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    part = resolve_part(rom, args.slot, args.part)
    print({k: v for k, v in part.items() if k != 'parts'}, len(part['parts']), 'objects')
    if args.png:
        from PIL import Image
        points = raster(part['parts'])
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        image = Image.new('L', (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
        for (x, y), v in points.items():
            image.putpixel((x - min(xs), y - min(ys)), v * 16)
        image.resize((image.width * 4, image.height * 4), Image.NEAREST).save(args.png)


def palette(rom, slot):
    """The slot's 16 in-ring colours (BGR555) from the live palette table ($2C:F212 holds its address)."""
    base = file_offset((rom[0x2CF218] << 16) | rom[0x2CF212] | rom[0x2CF213] << 8, len(rom)) + 64 + slot * 32
    return [rom[base + i * 2] | rom[base + i * 2 + 1] << 8 for i in range(16)]


def rgb(colour):
    return tuple((colour >> s & 31) * 255 // 31 for s in (0, 5, 10))
