"""Apply the alternate Scott Hall art (tools/scott_alt_art.py) to the Razor/Scott slot of a WWF Raw ROM.

The current Scott gear (tools/build_scott_hall_gear.py, the editor's "Use Scott reference gear") is left exactly as it
is; this is a second take you can compare it with. The result uses the same storage, hooks and marker
(SCOTT-HALL-GEAR3) as the current Scott gear, so the editor and every tool read it as the Scott gear; only the art and
the slot palette differ. Apply it before Add Mr. Perfect, like the other gear.

The donor is Razor Ramon's native art in the input ROM (slot 5), read with the static part resolver
(tools/raw_parts.py) through the game's own directory, so no memory dump is needed and the current Scott gear, if the
ROM has it, is replaced rather than painted over. Its pixels stay in your ROM; the repository holds only the
authoring rules. Nothing else in the ROM changes.

    python3 tools/build_scott_alt.py RAW.sfc --output OUT.sfc

RAW.sfc is the original game or an edited ROM, with or without the current Scott gear.
"""
import argparse
import hashlib
from pathlib import Path

import build_scott_hall_gear as gear
import scott_alt_art
from build_bret_gear import planar
from build_nwo_gear import checksum
from build_sting_crow import donor_catalog
from raw_parts import palette_offset

SLOT = 5
STRIDE = 32     # the game copies 32 bytes per private tile; the current gear spaces them 36 apart, too few for this art
HOOKS = [(0x2cf6e4, 'cf480f00'), (0xecc1, '7f13d5ad'), (0xed19, '7f47d5ad')]   # stock bytes before any Scott gear


def has_gear(rom):
    return len(rom) >= 0x600000 and bytes(rom[gear.SIGNATURE:gear.SIGNATURE + len(gear.MAGIC)]) == gear.MAGIC


def donor(rom):
    """Razor's native frames, read through the stock directory even when the ROM carries the Scott gear."""
    plain = bytearray(rom)
    if has_gear(rom):
        plain[gear.SIGNATURE:gear.SIGNATURE + len(gear.MAGIC)] = bytes(len(gear.MAGIC))
    return donor_catalog(bytes(plain), SLOT)


def build(rom, art=None, frames=None, palette=None, stride=STRIDE):
    """art(frame) -> {tile field: 64 pixels} (default scott_alt_art.author); palette: {index: BGR555}. With
    build_scott_hall_gear's decorate, its palette and stride 36 this writes exactly what that builder writes."""
    rom = bytes(rom)
    if len(rom) not in (0x400000, 0x600000, 0x800000):
        raise ValueError('Unexpected ROM size.')
    if not has_gear(rom):
        for address, expect in HOOKS:
            if rom[address:address + 4] != bytes.fromhex(expect):
                raise ValueError('This ROM already has an unsupported sprite hook.')
    frames = frames if frames is not None else donor(rom)
    art = art or scott_alt_art.author
    palette = scott_alt_art.PALETTE if palette is None else palette

    out = bytearray(rom) + bytearray(b'\xff' * (max(len(rom), 0x600000) - len(rom)))
    for start, end in [(gear.FRAMES, gear.FRAME_END), (gear.PACKETS, gear.PACKET_END), (gear.POINTERS, gear.POINTER_END)]:
        out[start:end] = b'\xff' * (end - start)
    out[gear.PRIMARY:gear.PRIMARY + 998 * 3] = bytes(998 * 3)
    out[gear.SECONDARY:gear.SECONDARY + 722 * 3] = bytes(722 * 3)
    cursor, packet_cursor, tiles, descriptors, modified = gear.FRAMES, gear.PACKETS, {}, {}, 0
    for f in frames:
        changed = art(f)
        if not changed:
            continue
        data, variants = bytearray(rom[f['offset']:f['offset'] + f['length']]), 0
        for part in f['parts']:
            for ref in part['refs']:
                pixels = changed.get(ref['field'])
                if pixels is None or pixels == ref['pixels']:
                    continue
                if any((p == 0) != (q == 0) for p, q in zip(pixels, ref['pixels'])):
                    raise ValueError('Art changes native transparency.')
                raw = planar(pixels)
                if raw not in tiles:
                    if (packet_cursor & 65535) + stride > 65536:
                        packet_cursor = (packet_cursor + 65535) & ~65535
                    idx = len(tiles)
                    if idx >= 16384 or gear.POINTERS + idx * 3 + 3 > gear.POINTER_END or packet_cursor + stride > gear.PACKET_END:
                        raise ValueError('Scott tiles exceed their private space.')
                    tiles[raw] = idx
                    out[packet_cursor:packet_cursor + 32] = raw
                    out[gear.POINTERS + idx * 3:gear.POINTERS + idx * 3 + 3] = packet_cursor.to_bytes(3, 'little')
                    packet_cursor += stride
                data[ref['relative']:ref['relative'] + 2] = (0xc000 | tiles[raw]).to_bytes(2, 'little')
                variants += 1
        if not variants:
            continue
        key = bytes(data)
        if key not in descriptors:
            if (cursor & 65535) + len(data) > 65536:
                cursor = (cursor + 65535) & ~65535
            if (cursor & 65535) == 0:
                cursor += 256
            if cursor + len(data) > gear.FRAME_END:
                raise ValueError('Scott descriptors exceed their private bank.')
            descriptors[key] = cursor
            out[cursor:cursor + len(data)] = data
            cursor += len(data)
        table = (gear.PRIMARY if f['kind'] == 'primary' else gear.SECONDARY) + f['index'] * 3
        out[table:table + 3] = descriptors[key].to_bytes(3, 'little')
        modified += 1
    for offset in {gear.PALETTE, palette_offset(out, SLOT)}:      # the stock table and, after Add Mr. Perfect, its copy
        for i, c in palette.items():
            out[offset + i * 2:offset + i * 2 + 2] = c.to_bytes(2, 'little')
    if not has_gear(rom):
        # A ROM with the Scott gear keeps its own sprite programs: the editor relocates them behind a dispatcher that
        # also serves the other gear and Mr. Perfect, and they read this storage the same way.
        programs = [(gear.PROGRAM, gear.lookup_program(), 0x2cf6e4), (gear.PROGRAM + 0x100, gear.part_program(False), 0xecc1),
                    (gear.PROGRAM + 0x200, gear.part_program(True), 0xed19)]
        for address, code, hook in programs:
            out[address:address + len(code)] = code
            out[hook:hook + 4] = bytes([0x5c, address & 255, address >> 8 & 255, address >> 16])
        out[gear.SIGNATURE:gear.SIGNATURE + len(gear.MAGIC)] = gear.MAGIC
    checksum(out)
    return bytes(out), {'modified_directory_entries': modified, 'private_descriptors': len(descriptors),
                        'private_tiles': len(tiles), 'private_packet_bytes': packet_cursor - gear.PACKETS}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('rom', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out, report = build(a.rom.read_bytes())
    a.output.write_bytes(out)
    print({**report, 'sha256': hashlib.sha256(out).hexdigest()})


if __name__ == '__main__':
    main()
