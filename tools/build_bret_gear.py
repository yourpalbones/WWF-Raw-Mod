"""Build a reference-inspired black-gear prototype for Bret's tested pose.

This edits ROM assets, with authored standing/walking and observed running poses.
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
        (Path(__file__).resolve().parents[1] / "data" / "bret-gear.json").read_text()
    )
    simplified = []
    simplified_details = []
    omitted_details = []
    relocations = []
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
            if not asset["compressed"]:
                raise ValueError("Raw tile length changed")
            relocations.append((offset, bytes(packet)))
        else:
            result[offset : offset + len(packet)] = packet
            edits.append((offset, bytes(packet)))
    relocated = []
    if relocations:
        # Preserve the sparse decoder and the original lookup. Redirect only the
        # resolved pointers whose authored packet cannot fit its original slot.
        entry = 0x2CF771
        if rom[entry : entry + 4] != bytes.fromhex("a9 01 00 6b"):
            raise ValueError("Compressed lookup return differs from original")
        result.extend(b"\xff" * (0x400000 - len(result)))
        program = bytearray()
        for number, (source, packet) in enumerate(relocations):
            target = 0x301000 + number * 40
            source_cpu = source | 0xC00000
            target_cpu = target | 0xC00000
            # All native callers use 16-bit A and D=0, as recorded by the trace.
            matched = (
                b"\xa9"
                + (target_cpu >> 16).to_bytes(2, "little")
                + b"\x85\xdd"
                + b"\xa9"
                + (target_cpu & 65535).to_bytes(2, "little")
                + b"\x85\xdb"
                + bytes.fromhex("a9 01 00 6b")
            )
            low = (
                bytes.fromhex("a5 db c9")
                + (source_cpu & 65535).to_bytes(2, "little")
                + b"\xd0"
                + bytes([len(matched)])
                + matched
            )
            program += (
                bytes.fromhex("a5 dd 29 ff 00 c9")
                + (source_cpu >> 16).to_bytes(2, "little")
                + b"\xd0"
                + bytes([len(low)])
                + low
            )
            result[target : target + len(packet)] = packet
            edits.append((target, packet))
            relocated.append(
                {
                    "original_offset": f"0x{source:06X}",
                    "new_offset": f"0x{target:06X}",
                    "packet_size": len(packet),
                }
            )
        program += bytes.fromhex("a9 01 00 6b")
        if len(program) > 4096:
            raise ValueError("Lookup redirect program exceeds reserved page")
        result[0x300000 : 0x300000 + len(program)] = program
        redirect = bytes.fromhex("5c 00 00 f0")
        result[entry : entry + 4] = redirect
        edits.extend([(0x300000, bytes(program)), (entry, redirect)])
    for slot, offset, compressed in ASSETS:
        # The same authored source map drives standing and walking details.
        # Never overwrite it with separate standing-position artwork.
        if compressed:
            tiles[slot] = decode_sprite_tile(result, offset)[0]
        else:
            tiles[slot] = bytes(result[offset : offset + 32])
    # Original gray boot trim becomes light pink. Other palette entries stay put.
    pink = (31 | (12 << 5) | (24 << 10)).to_bytes(2, "little")
    result[PALETTE + 12 : PALETTE + 14] = pink
    edits.append((PALETTE + 12, pink))
    checksum = (
        sum(result)
        if relocations
        else sum(result[:0x200000]) + 2 * sum(result[0x200000:])
    ) & 0xFFFF
    header = (checksum ^ 0xFFFF).to_bytes(2, "little") + checksum.to_bytes(2, "little")
    result[0xFFDC:0xFFE0] = header
    edits.append((0xFFDC, header))
    patch = bytearray(b"PATCH")
    if relocations:
        # IPS RLE creates erased expanded space without embedding a ROM image.
        for address in range(0x300000, 0x400000, 65535):
            length = min(65535, 0x400000 - address)
            patch += (
                address.to_bytes(3, "big")
                + b"\x00\x00"
                + length.to_bytes(2, "big")
                + b"\xff"
            )
    for address, data in edits:
        patch += address.to_bytes(3, "big") + len(data).to_bytes(2, "big") + data
    patch += b"EOF"
    report = {
        "original_sha256": ORIGINAL_HASH,
        "patched_sha256": hashlib.sha256(result).hexdigest(),
        "changed_rom_bytes": sum(a != b for a, b in zip(rom, result)),
        "expanded_size": len(result),
        "relocated_packets": relocated,
        "lookup_redirect": "Compressed pointer return only; native sparse decoder retained"
        if relocations
        else None,
        "checksum": f"0x{checksum:04X}",
        "tile_slots": list(tiles),
        "edits": [{"offset": f"0x{a:06X}", "size": len(d)} for a, d in edits],
        "walk_assets": len(walk_map["assets"]),
        "movement_mapping": walk_map.get("movement_mapping"),
        "walk_tiles_using_flat_black": simplified,
        "walk_details_using_flat_black": simplified_details,
        "walk_detail_assets_omitted_for_space": omitted_details,
        "detail_mapping": walk_map["detail_mapping"],
        "visual_consistency_verified": False,
        "scope": walk_map.get(
            "scope", "Authored movement poses; other animations unverified"
        ),
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
