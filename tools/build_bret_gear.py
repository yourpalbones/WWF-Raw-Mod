"""Build a reference-inspired black-gear prototype for Bret's tested pose.

This edits known ROM assets, not a screenshot. Only the mapped standing pose
is covered. Other animations and other users of shared tiles remain unverified.
"""

import argparse
import hashlib
import json
from pathlib import Path

from decode_sprite_tile import decode_sprite_tile, encode_sprite_tile
from inspect_rom import tile

ORIGINAL_HASH = "0af7b0d3022acd24a1fb15865a076519f7f56e7a4b33f12b6d851b3a91e5388c"
# VRAM slot, ROM offset, compression. Raw sources are unique exact ROM matches.
ASSETS = [
    (3, 0x0B3D60, False),
    (4, 0x1692D0, True),
    (14, 0x12AE50, True),
    (15, 0x17B998, True),
    (16, 0x0B3D20, False),
    (17, 0x1692B4, True),
    (18, 0x0AB100, False),
    (19, 0x0B3D80, False),
    (20, 0x0B3DA0, False),
    (30, 0x14766C, True),
]
PALETTE = 0x2CC4FA


def planar(pixels):
    output = bytearray(32)
    for y in range(8):
        for x in range(8):
            for plane in range(4):
                output[(plane // 2) * 16 + y * 2 + plane % 2] |= (
                    (pixels[y * 8 + x] >> plane) & 1
                ) << (7 - x)
    return bytes(output)


def build(rom):
    if hashlib.sha256(rom).hexdigest() != ORIGINAL_HASH:
        raise ValueError("Requires the exact verified, unmodified USA ROM")
    result = bytearray(rom)
    edits = []
    tiles = {}
    for slot, offset, compressed in ASSETS:
        if compressed:
            old, length = decode_sprite_tile(rom, offset)
        else:
            old, length = rom[offset : offset + 32], 32
        original_pixels = tile(old, 0, 4)
        # Black shade + charcoal highlight; preserve skin, silhouette and tights.
        pixels = [1 if p == 4 else 3 if p == 5 else p for p in original_pixels]
        if slot in (3, 19):
            # Raise the emblem two pixels toward the center of the chest.
            mark = (
                {(4, 7): 4}
                if slot == 3
                else {
                    (3, 0): 8,
                    (4, 0): 5,
                    (5, 0): 8,
                    (3, 1): 8,
                    (4, 1): 8,
                    (5, 1): 8,
                    (4, 2): 4,
                }
            )
            for (x, y), color in mark.items():
                if original_pixels[y * 8 + x] not in (4, 5):
                    raise ValueError("Chest mark would overwrite skin")
                pixels[y * 8 + x] = color
        # Cover the bend of the elbow, spanning the upper arm and forearm tiles.
        pad = []
        if slot == 18:
            pad = [(x, y) for y in (6, 7) for x in range(2, 7)]
        elif slot == 15:
            pad = [(x, y) for y in range(3) for x in range(5)]
        for x, y in pad:
            if original_pixels[y * 8 + x] in (7, 9, 10, 11, 12, 15):
                pixels[y * 8 + x] = 2 if x in (2, 3) else 1
        # Wrist bands on the foreground and raised far arm, before the hands.
        tape = []
        if slot == 30:
            tape = [(x, y) for y in range(4) for x in (2, 3, 4)]
        elif slot == 20:
            tape = [(x, y) for y in (3, 4, 5) for x in (4, 5, 6)]
        for x, y in tape:
            if original_pixels[y * 8 + x] in (7, 9, 10, 11, 12, 15):
                pixels[y * 8 + x] = 2 if x in (3, 5) else 1
        decoded = planar(pixels)
        packet = encode_sprite_tile(decoded) if compressed else decoded
        if len(packet) > length:
            raise ValueError("New tile exceeds existing asset space")
        result[offset : offset + len(packet)] = packet
        # Remaining bytes are unused padding; keep them intact.
        edits.append((offset, bytes(packet)))
        tiles[slot] = decoded
    # Original gray boot trim becomes light pink. Other palette entries stay put.
    pink = (31 | (12 << 5) | (24 << 10)).to_bytes(2, "little")
    result[PALETTE + 12 : PALETTE + 14] = pink
    edits.append((PALETTE + 12, pink))
    checksum = (sum(result[:0x200000]) + 2 * sum(result[0x200000:])) & 0xFFFF
    header = (checksum ^ 0xFFFF).to_bytes(2, "little") + checksum.to_bytes(2, "little")
    result[0xFFDC:0xFFE0] = header
    edits.append((0xFFDC, header))
    patch = bytearray(b"PATCH")
    for address, data in edits:
        patch += address.to_bytes(3, "big") + len(data).to_bytes(2, "big") + data
    patch += b"EOF"
    report = {
        "original_sha256": ORIGINAL_HASH,
        "patched_sha256": hashlib.sha256(result).hexdigest(),
        "changed_rom_bytes": sum(a != b for a, b in zip(rom, result)),
        "checksum": f"0x{checksum:04X}",
        "tile_slots": list(tiles),
        "edits": [{"offset": f"0x{a:06X}", "size": len(d)} for a, d in edits],
        "scope": "Mapped standing pose only; complete animation coverage unverified",
    }
    return bytes(result), bytes(patch), tiles, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        raise ValueError("Output directory must be empty")
    result, patch, tiles, report = build(args.rom.read_bytes())
    (args.output / "WWF-Raw-black-gear-prototype.sfc").write_bytes(result)
    (args.output / "bret-black-gear.ips").write_bytes(patch)
    (args.output / "patch-report.json").write_text(json.dumps(report, indent=2) + "\n")
    for slot, data in tiles.items():
        (args.output / f"tile-{slot:02d}.bin").write_bytes(data)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
