"""Inventory secondary frame directories and verify observed native references."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from build_bret_gear import ORIGINAL_HASH
from decode_sprite_tile import decode_sprite_tile
from inventory_bret_frames import lookup, parse_frame
from verify_roster_identities import CASES, DELTAS

ENTRY_BYTES = 0x04FE


def inventory(rom, trace_root):
    if hashlib.sha256(rom).hexdigest() != ORIGINAL_HASH:
        raise ValueError("Requires the verified original ROM")
    directories = {}
    selectors = []
    for selector in range(13):
        base = 0x2DD547 + selector * 2
        bank = 0x2DD561 + selector * 2
        pointer = (rom[bank] << 16) | int.from_bytes(rom[base : base + 2], "little")
        offset = pointer & 0x3FFFFF
        selectors.append(
            {"selector": selector, "directory_file_offset": f"{offset:06X}"}
        )
        if offset in directories:
            directories[offset]["selectors"].append(selector)
            continue
        frames = []
        for entry in range(offset, offset + ENTRY_BYTES, 3):
            address = (rom[entry] << 16) | int.from_bytes(
                rom[entry + 1 : entry + 3], "little"
            )
            frame = parse_frame(rom, address)
            frame["frame_index"] = (entry - offset) // 3
            frames.append(frame)
        directories[offset] = {"selectors": [selector], "frames": frames}
    by_selector = {s: d for d in directories.values() for s in d["selectors"]}
    initial = trace_root / "roster-bret-match/frame-001200-wram.bin"
    wram = initial.read_bytes()
    assets = {}
    frame_users = Counter()
    asset_users = Counter()
    for directory in directories.values():
        frame_users.update({f["pointer"] for f in directory["frames"]})
        ids = {field["tile_id"] for f in directory["frames"] for field in f["fields"]}
        sources = set()
        for tile_id in ids:
            source, compressed = lookup(tile_id, wram, 0x1FFF, 0xDD, 0xA880, 0x027C)
            offset = source & 0x3FFFFF
            if compressed:
                decoded, length = decode_sprite_tile(rom, offset)
            else:
                decoded, length = rom[offset : offset + 32], 32
            if len(decoded) != 32:
                raise ValueError("Secondary tile outside ROM")
            assets[tile_id] = {
                "tile_id": tile_id,
                "source": source,
                "compressed": compressed,
                "packet_bytes": length,
                "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
            }
            sources.add(source)
        directory["tile_ids"] = sorted(ids)
        directory["sources"] = sorted(sources)
        asset_users.update(sources)
    checks = []
    for name, folder, selector, _ in CASES:
        fields = {
            0xC00000 | field["offset"]: field["tile_id"]
            for frame in by_selector[selector]["frames"]
            for field in frame["fields"]
        }
        trace = trace_root / folder
        match_wram = (trace / "frame-001200-wram.bin").read_bytes()
        checked = 0
        for line in (trace / "tile_calls.jsonl").read_text().splitlines():
            event = json.loads(line)
            if event["actor_slot"] != 0 or event["raw_threshold"] != 0x1FFF:
                continue
            address = event["descriptor"] + DELTAS[event["caller"]]
            if fields.get(address) != event["tile_id"]:
                raise ValueError(f"Secondary frame field absent for {name}")
            source, compressed = lookup(
                event["tile_id"],
                match_wram,
                event["raw_threshold"],
                event["raw_bank"],
                event["raw_base"],
                event["directory_base"],
            )
            if (source, compressed) != (event["source"], bool(event["compressed"])):
                raise ValueError(f"Native secondary source lookup differs for {name}")
            asset = assets[event["tile_id"]]
            if (asset["source"], asset["compressed"]) != (source, compressed):
                raise ValueError("Secondary dictionary differs across matches")
            checked += 1
        if not checked:
            raise ValueError(f"No native secondary references for {name}")
        checks.append(
            {
                "character": name,
                "selector": selector,
                "native_references_checked": checked,
            }
        )
    summaries = []
    for offset, directory in directories.items():
        pointers = {f["pointer"] for f in directory["frames"]}
        summaries.append(
            {
                "directory_file_offset": f"{offset:06X}",
                "selectors": directory["selectors"],
                "entries": len(directory["frames"]),
                "distinct_frames": len(pointers),
                "distinct_tile_ids": len(directory["tile_ids"]),
                "distinct_sources": len(directory["sources"]),
                "frame_pointers_shared_with_other_directories": sum(
                    frame_users[p] > 1 for p in pointers
                ),
                "sources_shared_with_other_directories": sum(
                    asset_users[s] > 1 for s in directory["sources"]
                ),
            }
        )
    return {
        "original_sha256": ORIGINAL_HASH,
        "scope": "Secondary directory range below part ID 04FE; semantic body-part/action labels unfinished",
        "complete_animation_coverage": False,
        "fallback_selector": 8,
        "selectors": selectors,
        "directories": summaries,
        "native_checks": checks,
        "private_frames": list(directories.values()),
        "private_assets": list(assets.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("trace_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.rom.read_bytes(), args.trace_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    del result["private_frames"], result["private_assets"]
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"Verified {sum(c['native_references_checked'] for c in result['native_checks'])} secondary references"
    )


if __name__ == "__main__":
    main()
