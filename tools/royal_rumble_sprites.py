"""Read Royal Rumble USA's native sprite chains and shared mask packets.

LoROM addressing and pose chains differ from Raw. This does not import moves or
make an expanded Raw roster; it provides verified source graphics for that work.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
from decode_sprite_tile import decode_sprite_tile
from inspect_rom import tile

ROYAL_SHA256 = '51c53e36ed0b959b0695fc6ef036fa7302d1c995eca35c28261d6f3cb77df0ca'
RAW_THRESHOLD = 0x3d1f
FRAME_COUNT = 828


def decode_tile(rom, source, compressed):
    raw, length = decode_sprite_tile(rom, source) if compressed else (rom[source:source + 32], 32)
    if len(raw) != 32 or source // 0x8000 != (source + length - 1) // 0x8000:
        raise ValueError('Royal tile is truncated or crosses a LoROM bank')
    return raw, length


def verify_trace(rom, wram, trace):
    events = [json.loads(line) for line in (trace / 'royal-tiles.jsonl').read_text().splitlines()]
    if not events:
        raise ValueError('Native trace contains no tile requests')
    for event in events:
        source, compressed = lookup(event['tile_id'], wram)
        if source != lorom_offset(event['source']) or compressed != bool(event['compressed']):
            raise ValueError(f"Lookup mismatch at event {event['event']}")
        raw, _ = decode_tile(rom, source, compressed)
        asset = trace / 'assets' / f"royal-tile-{event['event']:06d}-{event['source']:06x}.bin"
        if raw != asset.read_bytes():
            raise ValueError(f"Native tile mismatch at event {event['event']}")
    return {'tile_requests_checked': len(events),
            'unique_ids': len({event['tile_id'] for event in events}),
            'compressed_requests': sum(bool(event['compressed']) for event in events),
            'native_bytes_match': True,
            'cross_game_animation_conversion_complete': False}


def lorom_offset(address):
    bank, low = address >> 16 & 255, address & 65535
    if bank in {0x7e, 0x7f} or low < 0x8000:
        raise ValueError(f'Not a mapped LoROM address: {address:06x}')
    return (bank & 127) * 0x8000 + (low & 0x7fff)


def lookup(tile_id, wram):
    if tile_id < RAW_THRESHOLD:
        offset = 0x17 * 0x8000 + 0x6840 + tile_id * 32
        return offset, False
    index = tile_id - RAW_THRESHOLD
    at = 0x10000 + (index // 128) * 4
    bank, low, high, page = wram[at:at + 4]
    address = low | high << 8
    delta_at = 0x11000 + page * 256 + (index & 127) * 2
    address += int.from_bytes(wram[delta_at:delta_at + 2], 'little')
    if address >= 0x10000:
        address = (address & 65535) | 0x8000
        bank += 1
    return lorom_offset(bank << 16 | address), True


def parse_pose(rom, pointer, wram):
    start = pointer
    seen = set()
    parts = []
    while True:
        if pointer in seen or len(parts) > 64:
            raise ValueError(f'Invalid/cyclic pose at {start:06x}')
        seen.add(pointer)
        at = lorom_offset(pointer)
        y, x = rom[at:at + 2]
        if y & 128:
            pointer = ((rom[at + 2] | 128) << 16) | y << 8 | x
            continue
        if not y:
            break
        size = 16 if x & 128 else 8
        refs = []
        for i in range(4 if size == 16 else 1):
            ident = int.from_bytes(rom[at + 2 + i * 2:at + 4 + i * 2], 'little')
            source, compressed = lookup(ident, wram)
            raw, length = decode_tile(rom, source, compressed)
            refs.append({'tile_id': ident, 'source': source, 'compressed': compressed,
                         'length': length, 'pixels': tile(raw, 0, 4)})
        parts.append({'x': (x & 127) - 64, 'y': y - 64, 'size': size,
                      'hflip': False, 'vflip': False, 'refs': refs})
        pointer += 2 + len(refs) * 2
    return {'pointer': start, 'parts': parts}


def catalog(rom, wram, selector=1):
    if hashlib.sha256(rom).hexdigest() != ROYAL_SHA256:
        raise ValueError('Requires the verified Royal Rumble USA source ROM')
    assert 0 <= selector < 12
    base = int.from_bytes(rom[0xa5a + selector * 2:0xa5c + selector * 2], 'little')
    result = []
    for i in range(FRAME_COUNT):
        at = lorom_offset(0x900000 | base + i * 2)
        offset = int.from_bytes(rom[at:at + 2], 'little')
        entry = lorom_offset(0x918000 + offset)
        bank = rom[entry] | 128
        address = int.from_bytes(rom[entry + 1:entry + 3], 'little')
        frame = parse_pose(rom, bank << 16 | address, wram)
        frame.update(index=i, selector=selector, directory_offset=offset)
        result.append(frame)
    return result


def raster(frame):
    points = {}
    for part in reversed(frame['parts']):
        for y in range(part['size']):
            for x in range(part['size']):
                ref = part['refs'][y // 8 * (part['size'] // 8) + x // 8]
                value = ref['pixels'][y % 8 * 8 + x % 8]
                if value:
                    points[part['x'] + x, part['y'] + y] = value
    return points


def render(frame, colors):
    pts = raster(frame)
    if not pts:
        return Image.new('RGBA', (1, 1))
    l, t = min(x for x, y in pts), min(y for x, y in pts)
    r, b = max(x for x, y in pts) + 1, max(y for x, y in pts) + 1
    im = Image.new('RGBA', (r - l, b - t))
    for (x, y), value in pts.items():
        im.putpixel((x - l, y - t), tuple((colors[value] >> s & 31) * 255 // 31 for s in [0, 5, 10]) + (255,))
    return im


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['rom', 'wram', 'cgram']:
        p.add_argument(name, type=Path)
    p.add_argument('--selector', type=int, default=1)
    p.add_argument('--obj-palette', type=int, choices=range(8), default=2,
                   help='Captured OAM palette for the selected wrestler (Mr. Perfect/player 1: 2)')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--verify-trace', type=Path)
    a = p.parse_args()
    frames = catalog(a.rom.read_bytes(), a.wram.read_bytes(), a.selector)
    palette = a.cgram.read_bytes()
    palette_base = 256 + a.obj_palette * 32
    colors = [int.from_bytes(palette[palette_base + i * 2:palette_base + i * 2 + 2], 'little') for i in range(16)]
    a.output.mkdir(parents=True, exist_ok=True)
    if a.verify_trace:
        report = verify_trace(a.rom.read_bytes(), a.wram.read_bytes(), a.verify_trace)
        (a.output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    (a.output / 'catalog.json').write_text(json.dumps(frames, separators=(',', ':')))
    for page in range((len(frames) + 63) // 64):
        sheet = Image.new('RGB', (8 * 120, 8 * 125), '#24252d')
        draw = ImageDraw.Draw(sheet)
        for n, frame in enumerate(frames[page * 64:(page + 1) * 64]):
            im = render(frame, colors)
            scale = min(2, 110 // max(1, im.width), 100 // max(1, im.height))
            if scale:
                im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
            x, y = n % 8 * 120, n // 8 * 125
            sheet.paste(im, (x + 5, y + 20), im)
            draw.text((x + 5, y + 3), str(frame['index']), fill='white')
        sheet.save(a.output / f'poses-{page:02d}.png')
    print('Decoded', len(frames), 'Royal Rumble source pose entries')
