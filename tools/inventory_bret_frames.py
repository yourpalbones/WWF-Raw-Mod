"""Enumerate the stock Bret primary frame directory and tile references.

This is an asset inventory, not proof that gameplay has exercised every move.
The field parser follows 80:EDF7 and 80:F1B8; source lookup follows AC:F6E4.
"""

import argparse
import hashlib
import json
from pathlib import Path

from build_bret_gear import ORIGINAL_HASH
from decode_sprite_tile import decode_sprite_tile

DIRECTORY = 0x2D6FE4  # Native table selection 1; verified Bret descriptors.
FRAME_COUNT = 0x062D // 3


def parse_frame(rom, pointer):
    offset = pointer & 0x3FFFFF
    if offset + 2 > len(rom):
        raise ValueError("Frame header outside ROM")
    total, large = rom[offset : offset + 2]
    if large > total or total > 64:
        raise ValueError(f"Invalid frame counts at {pointer:06X}")
    cursor = offset + 2
    fields = []
    for obj in range(total):
        control = rom[cursor]
        cursor += 1
        # Zero means two literal bytes; otherwise each zero nibble has a literal.
        cursor += 2 if not control else int(not control >> 4) + int(not control & 15)
        count = 4 if obj < large else 1
        for sub in range(count):
            if cursor + 2 > len(rom) or cursor >> 16 != offset >> 16:
                raise ValueError("Frame tile fields cross a bank")
            fields.append(
                {
                    "offset": cursor,
                    "tile_id": int.from_bytes(rom[cursor : cursor + 2], "little"),
                    "object": obj,
                    "subtile": sub,
                }
            )
            cursor += 2
    return {
        "pointer": pointer,
        "offset": offset,
        "length": cursor - offset,
        "objects": total,
        "large_objects": large,
        "fields": fields,
    }


def lookup(tile_id, wram, threshold=0x4D55, bank=0xC8, base=0x79E0, directory_base=0):
    if tile_id < threshold:
        return (bank << 16) + base + tile_id * 32, False
    index = tile_id - threshold
    record = 0x10000 + directory_base + (index // 128) * 4
    data = wram[record : record + 4]
    if len(data) != 4:
        raise ValueError("Packed tile directory truncated")
    address = ((data[0] >> 1) | 0xC0) << 16
    address |= (int.from_bytes(data[1:3], "little") & 0x7FFF) | ((data[0] & 1) << 15)
    offset_record = 0x11000 + data[3] * 256 + (index & 127) * 2
    return address + int.from_bytes(
        wram[offset_record : offset_record + 2], "little"
    ), True


def inventory(rom, wram, calls=None):
    if hashlib.sha256(rom).hexdigest() != ORIGINAL_HASH:
        raise ValueError("Inventory requires the verified original ROM")
    frames = []
    assets = {}
    field_ids = {}
    for number in range(FRAME_COUNT):
        offset = DIRECTORY + number * 3
        bank = rom[offset]
        address = int.from_bytes(rom[offset + 1 : offset + 3], "little")
        frame = parse_frame(rom, (bank << 16) | address)
        for field in frame["fields"]:
            source, compressed = lookup(field["tile_id"], wram)
            file_offset = source & 0x3FFFFF
            if compressed:
                data, length = decode_sprite_tile(rom, file_offset)
            else:
                data, length = rom[file_offset : file_offset + 32], 32
                if len(data) != 32:
                    raise ValueError("Raw tile outside ROM")
            assets[field["tile_id"]] = {
                "tile_id": field["tile_id"],
                "source": source,
                "compressed": compressed,
                "size": length,
                "decoded_sha256": hashlib.sha256(data).hexdigest(),
            }
            field_ids[0xC00000 | field["offset"]] = field["tile_id"]
        frame["frame_index"] = number
        frames.append(frame)
    checked = 0
    if calls:
        for line in calls.read_text().splitlines():
            event = json.loads(line)
            source, compressed = lookup(
                event["tile_id"],
                wram,
                event["raw_threshold"],
                event["raw_bank"],
                event["raw_base"],
                event["directory_base"],
            )
            if source != event["source"] or compressed != bool(event["compressed"]):
                raise ValueError("Lookup differs from native trace")
            checked += 1
            if event["actor_slot"] != 0 or event["raw_threshold"] != 0x4D55:
                continue
            delta = {0x80EEA8: 0, 0x80EEB8: 2, 0x80EEC8: 4, 0x80EED8: 6, 0x80EF1F: 0}[
                event["caller"]
            ]
            pointer = event["descriptor"] + delta
            if field_ids.get(pointer) != event["tile_id"]:
                raise ValueError(
                    f"Bret frame field missing from inventory: {pointer:06X}"
                )
    return {
        "directory_offset": f"0x{DIRECTORY:06X}",
        "directory_entries": len(frames),
        "distinct_frame_pointers": len({f["pointer"] for f in frames}),
        "distinct_tile_ids": len(assets),
        "tile_references": sum(len(f["fields"]) for f in frames),
        "native_lookup_calls_checked": checked,
        "gameplay_coverage_complete": False,
        "scope": "Primary Bret frame directory only; common/lower parts and semantic move mapping still require inventory",
        "frames": frames,
        "assets": list(assets.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("wram", type=Path)
    parser.add_argument("--calls", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.rom.read_bytes(), args.wram.read_bytes(), args.calls)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("frames", "assets")}, indent=2
        )
    )


if __name__ == "__main__":
    main()
