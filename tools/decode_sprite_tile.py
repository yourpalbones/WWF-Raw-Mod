"""Decode WWF Raw's zero-eliding in-ring tile format (AC:F775).

Each SNES 4bpp tile has a four-byte mask header. Each high/low nibble describes
four output bytes; set bits mean a byte is present, clear bits restore zero.
This is distinct from the game's mode-1/mode-2 interface compression.
"""

import argparse
import hashlib
import json
from pathlib import Path
from decode_graphics import render


def decode_sprite_tile(rom, offset):
    if offset < 0 or offset + 4 > len(rom):
        raise ValueError("Mask header outside input")
    masks = rom[offset : offset + 4]
    cursor = offset + 4
    output = bytearray()
    for byte in masks:
        for mask in (byte >> 4, byte & 15):
            for bit in (8, 4, 2, 1):
                if mask & bit:
                    if cursor >= len(rom) or cursor >> 16 != offset >> 16:
                        raise ValueError(
                            "Tile payload truncated or crosses bank boundary"
                        )
                    output.append(rom[cursor])
                    cursor += 1
                else:
                    output.append(0)
    return bytes(output), cursor - offset


def encode_sprite_tile(tile):
    """Encode exactly 32 bytes; canonical output may be shorter than the source."""
    if len(tile) != 32:
        raise ValueError("Expected one 32-byte SNES 4bpp tile")
    masks = bytearray(4)
    payload = bytearray()
    for group in range(8):
        mask = 0
        for i, bit in enumerate((8, 4, 2, 1)):
            value = tile[group * 4 + i]
            if value:
                mask |= bit
                payload.append(value)
        masks[group // 2] |= mask << (4 if group % 2 == 0 else 0)
    return bytes(masks + payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--offset", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.count < 1:
        raise ValueError("Tile count must be positive")
    rom = args.rom.read_bytes()
    if len(rom) % 1024 == 512:
        rom = rom[512:]
    cursor = args.offset
    output = bytearray()
    entries = []
    for _ in range(args.count):
        tile, size = decode_sprite_tile(rom, cursor)
        entries.append({"offset": f"0x{cursor:06X}", "compressed_size": size})
        output.extend(tile)
        cursor += size
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "tiles.bin").write_bytes(output)
    render(output, args.output / "tiles-4bpp.png")
    result = {
        "entries": entries,
        "decoded_size": len(output),
        "sha256": hashlib.sha256(output).hexdigest(),
    }
    (args.output / "extraction.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
