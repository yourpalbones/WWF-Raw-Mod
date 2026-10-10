"""Build a reference-inspired black-gear prototype for Bret's tested pose.

This edits known ROM assets, not a screenshot. The mapped standing pose and an observed upright left walk are covered.
Other animations and other users of shared tiles remain unverified.
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
    walk_map = json.loads(
        (
            Path(__file__).resolve().parents[1] / "data" / "bret-left-walk.json"
        ).read_text()
    )
    simplified = []
    simplified_details = []
    omitted_details = []
    for asset in walk_map["assets"]:
        offset = int(asset["offset"], 0)
        if asset["compressed"]:
            original, length = decode_sprite_tile(rom, offset)
        else:
            original, length = rom[offset : offset + 32], 32
        native_pixels = tile(original, 0, 4)
        pixels = native_pixels.copy()
        for index in asset["pixels"]:
            if not 0 <= index < 64 or pixels[index] not in (4, 5):
                raise ValueError("Invalid walking garment pixel map")
            pixels[index] = 1 if pixels[index] == 4 else 3
        for detail in asset.get("details", []):
            index, color = detail["index"], detail["color"]
            if not 0 <= index < 64 or color not in (1, 2, 4, 5, 8):
                raise ValueError("Invalid walking detail map")
            material = native_pixels[index]
            expected = (7, 9, 10, 11, 12, 15) if color in (1, 2) else (4, 5)
            if material not in expected:
                raise ValueError("Walking detail would overwrite the wrong material")
            pixels[index] = color
        decoded = planar(pixels)
        packet = encode_sprite_tile(decoded) if asset["compressed"] else decoded
        if len(packet) > length:
            # Keep the allocation: use black instead of charcoal on this tile.
            detail_indices = {d["index"] for d in asset.get("details", [])}
            for index in asset["pixels"]:
                if index not in detail_indices:
                    pixels[index] = 1
            decoded = planar(pixels)
            packet = encode_sprite_tile(decoded) if asset["compressed"] else decoded
            simplified.append(asset["offset"])
        if len(packet) > length:
            for detail in asset.get("details", []):
                if detail["color"] in (1, 2):
                    pixels[detail["index"]] = 1
            decoded = planar(pixels)
            packet = encode_sprite_tile(decoded) if asset["compressed"] else decoded
            simplified_details.append(asset["offset"])
        if len(packet) > length:
            # Keep garment conversion; report detail tiles needing relocation.
            pixels = tile(original, 0, 4)
            for index in asset["pixels"]:
                pixels[index] = 1
            decoded = planar(pixels)
            packet = encode_sprite_tile(decoded) if asset["compressed"] else decoded
            omitted_details.append(asset["offset"])
        if len(packet) > length:
            raise ValueError(
                "Walking asset exceeds original allocation: " + asset["offset"]
            )
        result[offset : offset + len(packet)] = packet
        edits.append((offset, bytes(packet)))
    for slot, offset, compressed in ASSETS:
        if compressed:
            old, length = decode_sprite_tile(rom, offset)
        else:
            old, length = rom[offset : offset + 32], 32
        original_pixels = tile(old, 0, 4)
        # Black shade + charcoal highlight; preserve skin, silhouette and tights.
        pixels = [1 if p == 4 else 3 if p == 5 else p for p in original_pixels]
        if slot in (3, 19):
            # Shift the emblem toward the middle of the visible front panel.
            mark = (
                {(6, 7): 4}
                if slot == 3
                else {
                    (5, 0): 8,
                    (6, 0): 5,
                    (7, 0): 8,
                    (5, 1): 8,
                    (6, 1): 8,
                    (7, 1): 8,
                    (6, 2): 4,
                }
            )
            for (x, y), color in mark.items():
                if original_pixels[y * 8 + x] not in (4, 5):
                    raise ValueError("Chest mark would overwrite skin")
                pixels[y * 8 + x] = color
        # Wrap the pad around the elbow tip, including the lowest bent pixels.
        pad = []
        if slot == 18:
            pad = [(x, 7) for x in range(2, 7)]
        elif slot == 15:
            pad = [(x, y) for y in range(5) for x in range(6)]
        for x, y in pad:
            if original_pixels[y * 8 + x] in (7, 9, 10, 11, 12, 15):
                pixels[y * 8 + x] = 2 if x in (2, 3) else 1
        # Narrow bands immediately before each hand, rather than broad arm blocks.
        tape = []
        if slot == 30:
            tape = [(x, y) for y in range(3) for x in (3, 4)]
        elif slot == 20:
            tape = [(x, y) for y in (1, 2) for x in (5, 6)]
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
        "walk_assets": len(walk_map["assets"]),
        "walk_tiles_using_flat_black": simplified,
        "walk_details_using_flat_black": simplified_details,
        "walk_detail_assets_omitted_for_space": omitted_details,
        "scope": "Standing details and mapped upright left walk; other animations unverified",
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
