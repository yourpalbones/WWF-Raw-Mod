"""Map observed input actions to native primary/secondary frame-part requests."""

import argparse
import hashlib
import json
from pathlib import Path

from build_bret_gear import ORIGINAL_HASH
from inventory_bret_frames import parse_frame
from validate_traces import validate
from verify_roster_identities import DELTAS

CASES = [
    ("idle", "Both wrestlers idle", 0),
    ("p1-walk", "Bret walks right", 0),
    ("p2-walk", "Undertaker walks left", 2),
    ("p1-punch", "Bret standing punch into empty space", 0),
    ("p1-kick", "Bret standing kick into empty space", 0),
]


def summarize(rom, root, cases=CASES, window=(30, 90)):
    if hashlib.sha256(rom).hexdigest() != ORIGINAL_HASH:
        raise ValueError("Requires the verified original ROM")
    results = []
    for folder, label, actor in cases:
        trace = root / ("actions-" + folder)
        requests = [
            json.loads(line)
            for line in (trace / "parts.jsonl").read_text().splitlines()
        ]
        fields = {}
        selected = []
        for event in requests:
            if event["d"] != 0:
                raise ValueError("Unexpected direct page")
            table = 0x2DD547 if event["secondary"] else 0x2DD513
            index = event["selected_table_offset"]
            if index % 2 or index > 24 or event["part_id"] % 3:
                raise ValueError("Unexpected table offset or part alignment")
            base = int.from_bytes(rom[table + index : table + index + 2], "little")
            bank = rom[table + 26 + index]
            offset = ((bank << 16) | ((base + event["part_id"]) & 0xFFFF)) & 0x3FFFFF
            pointer = (rom[offset] << 16) | int.from_bytes(
                rom[offset + 1 : offset + 3], "little"
            )
            if pointer != event["descriptor"]:
                raise ValueError("Native part pointer differs from ROM table")
            frame = parse_frame(rom, pointer)
            for field in frame["fields"]:
                fields[(event["actor_slot"], 0xC00000 | field["offset"])] = field[
                    "tile_id"
                ]
            if (
                event["actor_slot"] == actor
                and window[0] <= event["frame"] <= window[1]
            ):
                selected.append(event)
        checked = 0
        for line in (trace / "tile_calls.jsonl").read_text().splitlines():
            event = json.loads(line)
            address = event["descriptor"] + DELTAS[event["caller"]]
            if fields.get((event["actor_slot"], address)) != event["tile_id"]:
                raise ValueError("Native tile field absent from requested parts")
            checked += 1
        codec = validate(rom, trace)
        if codec["errors"]:
            raise ValueError("Native codec comparison failed")
        run = json.loads((trace / "run.json").read_text())
        results.append(
            {
                "case": folder,
                "observed_action": label,
                "actor_slot": actor,
                "input_schedule": run["presses"],
                "input_schedule_fields": [
                    "controller_port",
                    "start_frame",
                    "button_id",
                    "duration",
                ],
                "sampled_gameplay_frames": len(list(trace.glob("frame-*.png"))),
                "snapshot_interval": run["interval"],
                "selection_window": list(window),
                "native_part_requests_checked": len(requests),
                "native_tile_fields_checked": checked,
                "primary_part_ids_in_input_window": sorted(
                    {e["part_id"] for e in selected if not e["secondary"]}
                ),
                "secondary_part_ids_in_input_window": sorted(
                    {e["part_id"] for e in selected if e["secondary"]}
                ),
                "observed_part_request_sequence": selected,
                "codec_verification": codec,
                "complete_action_variant_coverage": False,
            }
        )
    return {
        "original_sha256": ORIGINAL_HASH,
        "scope": "Controlled original-game input cases; no edited outfit validation",
        "complete_animation_coverage": False,
        "cases": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("trace_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--case", action="append", help="folder_suffix:observed_action:actor_slot"
    )
    parser.add_argument("--window", nargs=2, type=int, default=[30, 90])
    args = parser.parse_args()
    cases = CASES
    if args.case:
        cases = []
        for case in args.case:
            folder, label, actor = case.split(":")
            cases.append((folder, label, int(actor)))
    if args.window[0] < 1 or args.window[1] < args.window[0]:
        raise ValueError("Invalid selection window")
    result = summarize(args.rom.read_bytes(), args.trace_root, cases, args.window)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Mapped {len(result['cases'])} controlled cases")


if __name__ == "__main__":
    main()
