"""Carry user-marked facial landmarks into exact copies of the native face.

Only matching original pixels qualify, including reflected poses. Other face
drawings need their own anchors; their beard is deliberately left unpainted.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from native_gear_art import head_region
from scott_frame_catalog import catalog, raster


def register(rom, wram):
    frames = catalog(rom, wram, 9)
    original, _ = raster(frames[1])
    # Rows 6..12 of the user's grid: brow, eyes, nose, upper lip.
    template = {q: v for q, v in original.items()
                if -1 <= q[0] <= 5 and -38 <= q[1] <= -32}
    landmarks = {"eyes": [[1, -35], [2, -35], [4, -35]],
                 "nose": [3, -33], "mouth": [[3, -31], [3, -30]],
                 "jaw": [3, -29]}
    heads = {}
    for frame in frames:
        if frame["kind"] != "primary":
            continue
        head, _ = head_region(frame, raster(frame)[0], True)
        if not head:
            continue
        matches = []
        for sx, sy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
            votes = Counter((x - sx * tx, y - sy * ty)
                            for (tx, ty), v in template.items()
                            for (x, y), value in head.items() if value == v)
            for (dx, dy), _ in votes.most_common(2):
                if all(head.get((sx*x+dx, sy*y+dy)) == v
                       for (x, y), v in template.items()):
                    matches.append([sx, sy, dx, dy])
        if len(matches) == 1:
            heads[str(frame["index"])] = {"template": 1,
                                         "transform": matches[0],
                                         "exact_pixels": len(template)}
    return {"version": 1, "selector": 9,
            "method": "All 49 original brow/eye/nose/upper-lip pixels match exactly; no crown-relative beard placement.",
            "templates": {"1": {"primary_piece": 1,
                                  "landmarks": landmarks,
                                  "user_grid": {"nose": [11, 11],
                                                "mouth": [[11, 13], [11, 14]],
                                                "eyes": [[9, 9], [10, 9], [12, 9]]},
                                  "jaw_note": "Jaw row 15 inferred below the user-marked mouth; not separately marked by the user."}},
            "heads": heads}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("wram", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = register(args.rom.read_bytes(), args.wram.read_bytes())
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Registered exact facial landmarks for", len(result["heads"]), "primary pieces")
