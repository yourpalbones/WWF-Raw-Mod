"""Clone Bret's complete primary frame directory into expanded ROM space.

Baseline mode preserves every pixel, enabling an independent relocation test.
No stock shared tile is overwritten. This is not a finished all-moves outfit.
"""

import argparse
import hashlib
import json
from pathlib import Path

from decode_sprite_tile import decode_sprite_tile
from inventory_bret_frames import DIRECTORY, inventory
from inspect_rom import tile
from build_bret_gear import planar

PROGRAM = 0x300000
FRAMES = 0x310000
TILES = 0x320000
LOOKUP = 0x2CF6E4


def lookup_program():
    # A/X/Y are 16-bit at native lookup entry. Save A while testing descriptor bank.
    # New F1 frame descriptors use private raw IDs; all other calls execute the
    # original comparison and jump back to AC:F6E8 with its flags intact.
    raw = bytes.fromhex(
        "68 48 eb 4a 4a 4a 29 1f 00 18 69 f2 00 85 dd 68 29 ff 07 0a 0a 0a 0a 0a 85 db a9 00 00 6b"
    )
    guard = bytes.fromhex("48 a5 82 29 ff 00 c9 f1 00 d0") + bytes([len(raw)])
    fallback = bytes.fromhex("68 cf 48 0f 00 5c e8 f6 ac")
    return guard + raw + fallback


def build(rom, wram, black=False):
    catalog = inventory(rom, wram)
    if rom[LOOKUP : LOOKUP + 4] != bytes.fromhex("cf 48 0f 00"):
        raise ValueError("Lookup entry differs from the verified original")
    result = bytearray(rom)
    result.extend(b"\xff" * (0x400000 - len(result)))
    program = lookup_program()
    result[PROGRAM : PROGRAM + len(program)] = program
    result[LOOKUP : LOOKUP + 4] = bytes.fromhex("5c 00 00 f0")
    ids = {}
    for private_id, asset in enumerate(catalog["assets"]):
        ids[asset["tile_id"]] = private_id
        source = asset["source"] & 0x3FFFFF
        decoded = (
            decode_sprite_tile(rom, source)[0]
            if asset["compressed"]
            else rom[source : source + 32]
        )
        if black:
            pixels = [1 if p == 4 else 3 if p == 5 else p for p in tile(decoded, 0, 4)]
            decoded = planar(pixels)
        address = TILES + private_id * 32
        result[address : address + 32] = decoded
    if TILES + len(ids) * 32 > 0x400000:
        raise ValueError("Private tiles exceed expanded ROM")
    pointers = {}
    cursor = FRAMES
    for frame in catalog["frames"]:
        if frame["pointer"] not in pointers:
            if cursor + frame["length"] > FRAMES + 65536:
                raise ValueError("Private frame descriptors exceed F1 bank")
            pointers[frame["pointer"]] = cursor | 0xC00000
            data = bytearray(rom[frame["offset"] : frame["offset"] + frame["length"]])
            for field in frame["fields"]:
                relative = field["offset"] - frame["offset"]
                data[relative : relative + 2] = ids[field["tile_id"]].to_bytes(
                    2, "little"
                )
            result[cursor : cursor + len(data)] = data
            cursor += len(data)
        pointer = pointers[frame["pointer"]]
        entry = DIRECTORY + frame["frame_index"] * 3
        result[entry : entry + 3] = bytes([pointer >> 16]) + (
            pointer & 0xFFFF
        ).to_bytes(2, "little")
    # Original header declares 4 MiB (0x0C); the source ROM is 3 MiB with mirroring.
    if result[0xFFD7] != 12:
        raise ValueError("Unexpected ROM size declaration")
    checksum = sum(result) & 0xFFFF
    result[0xFFDC:0xFFE0] = (checksum ^ 0xFFFF).to_bytes(
        2, "little"
    ) + checksum.to_bytes(2, "little")
    if sum(result) & 0xFFFF != checksum:
        raise ValueError("Expanded ROM checksum mismatch")
    report = {
        "original_rom_sha256": hashlib.sha256(rom).hexdigest(),
        "expanded_rom_sha256": hashlib.sha256(result).hexdigest(),
        "expanded_size": len(result),
        "directory_entries": catalog["directory_entries"],
        "private_frame_descriptors": len(pointers),
        "private_raw_tiles": len(ids),
        "frame_descriptor_bytes": cursor - FRAMES,
        "private_tile_bytes": len(ids) * 32,
        "native_lookup_hook_bytes": len(program),
        "black_primary_gear": black,
        "gameplay_coverage_complete": False,
        "scope": "Primary frame isolation only. Lower/common parts and complete outfit details still require work.",
    }
    return bytes(result), report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("wram", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--black-primary-gear", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        raise ValueError("Output must be empty")
    result, report = build(
        args.rom.read_bytes(), args.wram.read_bytes(), args.black_primary_gear
    )
    (args.output / "WWF-Raw-private-primary.sfc").write_bytes(result)
    (args.output / "relocation-report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
