"""Derive the stock packed tile directory (addresses and offsets only) from a gameplay WRAM dump.

At boot Raw builds a directory in WRAM that maps a logical tile ID to its packet. Tile IDs at or above a
threshold use 128-tile groups (records at $7F:0000, four bytes each) and shared offset pages ($7F:1000,
128 sixteen-bit offsets each); lower IDs are direct 32-byte tiles. See tools/inventory_bret_frames.lookup.
The directory is identical in every match of the same ROM, and stock packets never move, so one derivation
serves every edited ROM whose stock packets are unchanged.

The output holds ROM addresses and byte offsets only (no pixels). It is checked against the stock ROM: every
resolved packet must have a valid mask header and lie inside the ROM.

    python3 tools/derive_tile_directory.py RAW_ROM WRAM_DUMP --output data/raw-tile-directory.json
"""
import argparse
import hashlib
import json
from pathlib import Path

RAW_SHA256 = '0af7b0d3022acd24a1fb15865a076519f7f56e7a4b33f12b6d851b3a91e5388c'
KINDS = {  # threshold, direct bank, direct base, record base (bytes into $7F:0000)
    'primary': (0x4D55, 0xC8, 0x79E0, 0),
    'secondary': (0x1FFF, 0xDD, 0xA880, 0x27C),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('rom', type=Path)
    parser.add_argument('wram', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rom, wram = args.rom.read_bytes(), args.wram.read_bytes()
    if hashlib.sha256(rom).hexdigest() != RAW_SHA256:
        raise SystemExit('Expected the unmodified WWF Raw USA ROM')
    out = {'generated_by': 'tools/derive_tile_directory.py', 'rom_sha256': RAW_SHA256, 'kinds': {}, 'pages': {}}
    ends = {'primary': KINDS['secondary'][3], 'secondary': None}
    used_pages = set()
    for kind, (threshold, bank, base, record_base) in KINDS.items():
        groups = []
        at = 0x10000 + record_base
        end = 0x10000 + ends[kind] if ends[kind] is not None else 0x11000
        while at + 4 <= end:
            d = wram[at:at + 4]
            if d == b'\x00\x00\x00\x00':
                break
            address = ((((d[0] >> 1) | 0xC0) << 16) | (int.from_bytes(d[1:3], 'little') & 0x7FFF) |
                       ((d[0] & 1) << 15)) & 0x3FFFFF
            # Groups are laid out in ascending ROM order; the first backward or far jump ends the table
            # (later WRAM bytes belong to other data).
            if groups and not 0 < address - groups[-1][0] <= 0x2000:
                break
            groups.append([address, d[3]])
            used_pages.add(d[3])
            at += 4
        out['kinds'][kind] = {'threshold': threshold, 'direct_bank': bank, 'direct_base': base, 'groups': groups}
    for page in sorted(used_pages):
        out['pages'][str(page)] = [int.from_bytes(wram[0x11000 + page * 256 + k * 2:0x11000 + page * 256 + k * 2 + 2],
                                                  'little') for k in range(128)]
    # Check: every resolved packet has a sane mask header and stays inside the ROM.
    checked = 0
    for kind, info in out['kinds'].items():
        for start, page in info['groups']:
            for offset in out['pages'][str(page)]:
                packet = start + offset
                if packet + 4 > len(rom):
                    raise SystemExit(f'{kind} packet outside ROM: {packet:06x}')
                length = 4 + sum(bin(b).count('1') for b in rom[packet:packet + 4])
                if packet + length > len(rom):
                    raise SystemExit(f'{kind} packet overruns ROM: {packet:06x}')
                checked += 1
    args.output.write_text(json.dumps(out, separators=(',', ':')) + '\n')
    print({k: len(v['groups']) for k, v in out['kinds'].items()}, 'pages', len(out['pages']), 'packets checked', checked)


if __name__ == '__main__':
    main()
