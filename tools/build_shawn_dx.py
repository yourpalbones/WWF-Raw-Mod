"""Put Shawn Michaels in his red DX-era ring gear (tools/shawn_dx_art.py) on the Shawn slot (8) of a WWF Raw ROM.

What it writes:
- Shawn's palette (slot 8): vivid red tights, black boots, white for the logos. It goes to the stock palette table
  and, after Add Mr. Perfect, to the table's copy the game reads.
- The heart logos: Shawn's own pieces that carry them get private copies (descriptors and tiles) in
  0x308000-0x32FFFF (HiROM banks $F0-$F2). No shipped editor feature uses that space; the ROM must have it free, or
  hold an earlier copy of this gear. Every other wrestler, and the game's shared generic bodies, keep their art.
- One branch for slot 8 at the start of the shared sprite dispatcher ($4B:E000/E100/E200), the same programs the
  Scott/Nash/Syxx/Sting reference gear and Add Mr. Perfect use. The branch only acts when this gear's marker
  (SHAWN-DX-GEAR1) is present. A ROM without any reference gear gets the dispatcher installed as the editor installs
  it.

Shawn's moves, timing and collision are untouched: only pixels and colours change.

    python3 tools/build_shawn_dx.py RAW.sfc --output OUT.sfc

RAW.sfc: the original game (4 MiB, as the editor saves it) or an edited ROM, with or without the reference gear and
Mr. Perfect. On a ROM that has Mr. Perfect but no reference gear, apply this before Add Mr. Perfect.
"""
import argparse
import hashlib
from pathlib import Path

import build_nwo_gear
import shawn_dx_art
from build_bret_gear import planar
from build_nwo_gear import checksum
from build_sting_crow import donor_catalog
from raw_parts import palette_offset

SLOT = 8
REGION = (0x308000, 0x330000)
SIGNATURE, MAGIC = 0x308000, b'SHAWN-DX-GEAR1'
PROGRAM = 0x308100                      # +0: primary worker, +0x100: secondary worker, +0x200: tile lookup
PRIMARY, SECONDARY = 0x309000, 0x30A000
POINTERS, POINTER_END = 0x30B000, 0x310000
FRAMES, FRAME_END = 0x310100, 0x318000  # one descriptor bank, $F1: the dispatcher's tile lookup keys on it
PACKETS, PACKET_END = 0x318000, 0x330000
HOOKS = [(0x2cf6e4, 'cf480f00'), (0xecc1, '7f13d5ad'), (0xed19, '7f47d5ad')]   # stock bytes
DISPATCH = (0x4be000, 0x4be100, 0x4be200)


def cpu(offset):
    """File 0x000000-0x3FFFFF is HiROM banks $C0-$FF."""
    return 0xC00000 | offset


def has_gear(rom):
    return len(rom) > REGION[1] and bytes(rom[SIGNATURE:SIGNATURE + len(MAGIC)]) == MAGIC


def programs():
    """[(offset, code)]: Shawn's two part workers and his tile lookup."""
    config = {'name': 'Shawn DX', 'primary_table': cpu(PRIMARY), 'secondary_table': cpu(SECONDARY),
              'pointers': cpu(POINTERS)}
    return [(PROGRAM, build_nwo_gear.worker(config)), (PROGRAM + 0x100, build_nwo_gear.worker(config, True)),
            (PROGRAM + 0x200, build_nwo_gear.lookup(config))]


def long_operand(address):
    return address.to_bytes(3, 'little')


def dispatchers():
    """The shared dispatchers (build_nwo_gear.programs) with Shawn's branch first. Each insert is self-contained,
    so the rest of every dispatcher keeps its exact bytes."""
    lookup, primary, secondary = (bytes(p['code']) for p in build_nwo_gear.programs()[:3])
    bank = cpu(FRAMES) >> 16
    shawn_lookup = bytes([0xc9, bank, 0x00, 0xd0, 0x04, 0x5c]) + long_operand(cpu(PROGRAM + 0x200))

    def part(worker):
        sig = bytes([0xaf]) + long_operand(cpu(SIGNATURE)) + bytes([0xc9]) + MAGIC[:2]
        jump = bytes([0x5c]) + long_operand(cpu(worker))
        return bytes([0xc9, SLOT * 2, 0x00, 0xd0, len(sig) + 2 + len(jump)]) + sig + bytes([0xd0, len(jump)]) + jump
    assert lookup[:6] == bytes.fromhex('48a58229ff00') and primary[:8] == secondary[:8] == bytes.fromhex('0848daa636bd740b')
    return [lookup[:6] + shawn_lookup + lookup[6:], primary[:8] + part(PROGRAM) + primary[8:],
            secondary[:8] + part(PROGRAM + 0x100) + secondary[8:]]


def build(rom, art=None, frames=None, palette=None):
    """art(frame) -> {tile field: 64 pixels} (default shawn_dx_art.author); palette: {index: BGR555}."""
    rom = bytes(rom)
    if len(rom) not in (0x400000, 0x600000, 0x800000):
        raise ValueError('Use the 4, 6 or 8 MiB ROM the editor saves.')
    total = sum(rom[:0x400000]) + (2 if len(rom) == 0x600000 else 1) * sum(rom[0x400000:])
    if total & 65535 != int.from_bytes(rom[0xffde:0xffe0], 'little'):
        raise ValueError('Invalid source checksum.')
    if not has_gear(rom) and any(b != 0xff for b in rom[REGION[0]:REGION[1]]):
        raise ValueError('0x308000-0x32FFFF is already used in this ROM (another patch); nothing was changed.')
    hooks = [bytes(rom[a:a + 4]) for a, _ in HOOKS]
    stock_hooks = hooks == [bytes.fromhex(e) for _, e in HOOKS]
    routed = hooks == [bytes([0x5c]) + long_operand(a) for a in DISPATCH]
    perfect = hooks == [bytes([0x5c]) + long_operand(a) for a in (0x70f200, 0x70f000, 0x70f100)]
    current = [bytes(p['code']) for p in build_nwo_gear.programs()[:3]]
    ours = dispatchers()
    present = len(rom) >= 0x600000 and all(any(rom[a:a + len(x)] == x for x in (c, o))
                                           for a, c, o in zip(DISPATCH, current, ours))
    if not stock_hooks:
        # Mr. Perfect's workers hand every other slot to the dispatcher only when it was there at import
        through = perfect and all(bytes([0x5c]) + long_operand(d) in rom[w:w + 0x100]
                                  for w, d in zip((0x70f000, 0x70f100, 0x70f200), (0x4be100, 0x4be200, 0x4be000)))
        if perfect and not (present and through):
            raise ValueError('Mr. Perfect is installed without the reference gear: apply Shawn DX before Add '
                             'Mr. Perfect.')
        if not (present and (routed or perfect)):
            raise ValueError('This ROM changes the sprite engine in a way this tool does not know; nothing was changed.')
    frames = frames if frames is not None else donor(rom)
    art = art or shawn_dx_art.author
    palette = shawn_dx_art.PALETTE if palette is None else palette

    out = bytearray(rom) + bytearray(b'\xff' * (max(len(rom), 0x600000) - len(rom)))
    out[REGION[0]:REGION[1]] = b'\xff' * (REGION[1] - REGION[0])
    out[PRIMARY:PRIMARY + 998 * 3] = bytes(998 * 3)
    out[SECONDARY:SECONDARY + 722 * 3] = bytes(722 * 3)
    cursor, packet, tiles, descriptors, modified = FRAMES, PACKETS, {}, {}, 0
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
                    if (packet & 65535) + 32 > 65536:
                        packet = (packet + 65535) & ~65535
                    idx = len(tiles)
                    if POINTERS + idx * 3 + 3 > POINTER_END or packet + 32 > PACKET_END:
                        raise ValueError('Shawn tiles exceed their private space.')
                    tiles[raw] = idx
                    out[packet:packet + 32] = raw
                    out[POINTERS + idx * 3:POINTERS + idx * 3 + 3] = long_operand(cpu(packet))
                    packet += 32
                data[ref['relative']:ref['relative'] + 2] = (0xc000 | tiles[raw]).to_bytes(2, 'little')
                variants += 1
        if not variants:
            continue
        key = bytes(data)
        if key not in descriptors:
            if (cursor & 65535) + len(data) > 65536 or cursor + len(data) > FRAME_END:
                raise ValueError('Shawn descriptors exceed their private bank.')
            descriptors[key] = cursor
            out[cursor:cursor + len(data)] = data
            cursor += len(data)
        table = (PRIMARY if f['kind'] == 'primary' else SECONDARY) + f['index'] * 3
        out[table:table + 3] = long_operand(cpu(descriptors[key]))
        modified += 1
    for offset, code in programs():
        out[offset:offset + len(code)] = code
    for address, code in zip(DISPATCH, ours):
        out[address:address + 0x100] = b'\xff' * 0x100
        out[address:address + len(code)] = code
    if stock_hooks:
        for (hook, _), address in zip(HOOKS, DISPATCH):
            out[hook:hook + 4] = bytes([0x5c]) + long_operand(address)
    out[SIGNATURE:SIGNATURE + len(MAGIC)] = MAGIC
    for offset in {0x2cc4da + SLOT * 32, palette_offset(out, SLOT)}:   # stock table and Mr. Perfect's copy
        for i, c in palette.items():
            out[offset + i * 2:offset + i * 2 + 2] = c.to_bytes(2, 'little')
    checksum(out)
    return bytes(out), {'modified_directory_entries': modified, 'private_descriptors': len(descriptors),
                        'descriptor_bytes': cursor - FRAMES, 'private_tiles': len(tiles),
                        'packet_bytes': packet - PACKETS, 'installed_dispatcher': stock_hooks}


def donor(rom):
    """Shawn's native frames, read through the stock directory even when the ROM carries this gear."""
    plain = bytearray(rom)
    plain[SIGNATURE:SIGNATURE + len(MAGIC)] = b'\xff' * len(MAGIC)
    return donor_catalog(bytes(plain), SLOT)


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
