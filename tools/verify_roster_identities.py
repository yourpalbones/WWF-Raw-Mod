"""Verify roster selectors against native match tile lookup traces."""

import argparse
import json
from pathlib import Path

from inventory_roster import inventory

CASES = [
    ("Bret Hart", "roster-bret-match", 1, 0),
    ("Undertaker", "roster-match-undertaker", 2, 300),
    ("Yokozuna", "roster-match-yokozuna", 3, 600),
    ("Bam Bam Bigelow", "roster-match-bam-bam-bigelow", 4, 900),
    ("Razor Ramon", "roster-match-razor-ramon", 5, 1200),
    ("Lex Luger", "roster-match-lex-luger", 6, 1500),
    ("Doink", "roster-match-doink", 7, 1800),
    ("Shawn Michaels", "roster-match-shawn-michaels", 8, 2100),
    ("1-2-3 Kid", "roster-match-123-kid", 9, 2400),
    ("Diesel", "roster-match-diesel", 10, 2700),
    ("Owen Hart", "roster-match-owen-hart", 11, 3000),
    ("Luna Vachon", "roster-match-luna-vachon", 0, 3300),
]
DELTAS = {0x80EEA8: 0, 0x80EEB8: 2, 0x80EEC8: 4, 0x80EED8: 6, 0x80EF1F: 0}


def verify(rom, root):
    catalog = inventory(rom)
    directories = {
        selector: directory
        for directory in catalog["private_frames"]
        for selector in directory["selectors"]
    }
    results = []
    for name, folder, selector, menu_frame in CASES:
        directory = directories[selector]
        fields = {
            0xC00000 | field["offset"]: field["tile_id"]
            for frame in directory["frames"]
            for field in frame["fields"]
        }
        trace = root / folder
        wram = (trace / "frame-001200-wram.bin").read_bytes()
        actor_value = int.from_bytes(wram[0xB74:0xB76], "little")
        if actor_value != selector * 2:
            raise ValueError(f"Actor selector differs for {name}")
        checked = 0
        for line in (trace / "tile_calls.jsonl").read_text().splitlines():
            event = json.loads(line)
            if event["actor_slot"] != 0 or event["raw_threshold"] != 0x4D55:
                continue
            address = event["descriptor"] + DELTAS[event["caller"]]
            if fields.get(address) != event["tile_id"]:
                raise ValueError(f"Native frame reference differs for {name}")
            checked += 1
        if not checked:
            raise ValueError(f"No primary native frame references for {name}")
        results.append(
            {
                "character": name,
                "selector": selector,
                "actor_directory_value": actor_value,
                "native_primary_tile_references_checked": checked,
                "trace_folder": folder,
                "selection_cycle_frame": menu_frame,
                "complete_animation_coverage": False,
            }
        )
    return {"characters": results, "all_stock_roster_identities_verified": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("trace_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.rom.read_bytes(), args.trace_root)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Verified {len(result['characters'])} character directory identities")


if __name__ == "__main__":
    main()
