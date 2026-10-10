"""Inventory primary directory selectors without guessing character identities."""

import argparse
import hashlib
import json
from pathlib import Path

from build_bret_gear import ORIGINAL_HASH
from inventory_bret_frames import FRAME_COUNT, parse_frame


def inventory(rom):
    if hashlib.sha256(rom).hexdigest() != ORIGINAL_HASH:
        raise ValueError("Requires the verified original WWF Raw USA ROM")
    directories = {}
    selectors = []
    for selector in range(13):
        base = 0x2DD513 + selector * 2
        bank = 0x2DD52D + selector * 2
        pointer = (rom[bank] << 16) | int.from_bytes(rom[base : base + 2], "little")
        offset = pointer & 0x3FFFFF
        selectors.append(
            {
                "selector": selector,
                "directory_cpu_address": f"{pointer:06X}",
                "directory_file_offset": f"{offset:06X}",
                "confirmed_character": "Bret Hart" if selector == 1 else None,
                "role": "common fallback" if selector == 8 else "unconfirmed",
            }
        )
        if offset in directories:
            directories[offset]["selectors"].append(selector)
            continue
        frames = []
        for index in range(FRAME_COUNT):
            entry = offset + index * 3
            address = (rom[entry] << 16) | int.from_bytes(
                rom[entry + 1 : entry + 3], "little"
            )
            frame = parse_frame(rom, address)
            frame["frame_index"] = index
            frames.append(frame)
        directories[offset] = {"selectors": [selector], "frames": frames}
    summaries = []
    for offset, directory in directories.items():
        pointers = {frame["pointer"] for frame in directory["frames"]}
        shared = set()
        for other_offset, other in directories.items():
            if other_offset != offset:
                shared.update(pointers & {f["pointer"] for f in other["frames"]})
        summaries.append(
            {
                "directory_file_offset": f"{offset:06X}",
                "selectors": directory["selectors"],
                "entries_in_examined_range": len(directory["frames"]),
                "distinct_frame_pointers": len(pointers),
                "frame_pointers_shared_with_other_directories": len(shared),
                "distinct_tile_ids": len(
                    {
                        f["tile_id"]
                        for frame in directory["frames"]
                        for f in frame["fields"]
                    }
                ),
            }
        )
    return {
        "original_sha256": ORIGINAL_HASH,
        "scope": "13 primary selectors; examined 527 entries per distinct directory using Bret's established range",
        "character_identities_complete": False,
        "gameplay_coverage_complete": False,
        "lower_body_inventory_complete": False,
        "selectors": selectors,
        "directories": summaries,
        "private_frames": list(directories.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.rom.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    del result["private_frames"]
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"Inventoried {len(result['selectors'])} selectors and {len(result['directories'])} distinct directories"
    )


if __name__ == "__main__":
    main()
