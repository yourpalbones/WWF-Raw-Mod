"""Draft small gear details on the observed upright walking poses.

Uses pose-relative landmarks, restricted to original skin/singlet pixels.
This is a draft for visual review, not a general anatomical sprite detector.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from decode_sprite_tile import decode_sprite_tile
from extract_oam import assemble, objects
from inspect_rom import tile


def add_details(rom, root, initial, plan):
    events = []
    for directory, earlier in [(initial, True), (root, False)]:
        for line in (directory / "tiles.jsonl").read_text().splitlines():
            e = json.loads(line)
            if 0x7E2000 <= e["destination"] < 0x7E2800:
                source = e["source"] & 0x3FFFFF
                decoded, _ = decode_sprite_tile(rom, source)
                events.append(
                    (0 if earlier else e["frame"], e["destination"], source, decoded)
                )
    excluded = {0x1225AB}  # Shared inactive object tile; preserve it.
    plan["assets"] = [a for a in plan["assets"] if int(a["offset"], 0) not in excluded]
    votes = defaultdict(lambda: defaultdict(Counter))
    missing = 0
    for png in sorted(root.glob("frame-*.png")):
        frame = int(png.stem.split("-")[1])
        if frame < 8:
            continue  # Existing standing edit handles the initial pose.
        pre = png.with_suffix("")

        def read(name):
            return Path(str(pre) + "-" + name + ".bin").read_bytes()

        vram = read("vram")
        recs = objects(vram, read("oam"), read("cgram"), read("registers")[0x2101])
        ids = [
            i
            for i, (r, im) in enumerate(recs)
            if r["palette"] == 0
            and 0 <= r["y"] < 190
            and -20 <= r["x"] < 256
            and im.getbbox()
        ]
        _, bounds = assemble(recs, ids)
        left, top, right, bottom = bounds
        atlas = {}
        for i in reversed(ids):
            r = recs[i][0]
            size, number = r["size"], r["tile"]
            for ty in range(size // 8):
                for tx in range(size // 8):
                    n = ((number & 0xF0) + ty * 16 + ((number + tx) & 15)) & 255
                    px = tile(vram, n * 32, 4)
                    for k, color in enumerate(px):
                        if not color:
                            continue
                        dx, dy = tx * 8 + k % 8, ty * 8 + k // 8
                        x = r["x"] + (size - 1 - dx if r["hflip"] else dx)
                        y = r["y"] + (size - 1 - dy if r["vflip"] else dy)
                        atlas[x, y] = (n, k, color)
        desired = {}
        # Rounded pad at the outside of the lowered/bent elbow.
        for (x, y), (_, _, color) in atlas.items():
            if (
                color in (7, 9, 10, 11, 12, 15)
                and ((x - left - 5.5) / 3.2) ** 2 + ((y - top - 34) / 3) ** 2 <= 1
            ):
                desired[x, y] = 2 if x >= left + 5 else 1
        # Thin bands at the lowered wrists; keep hands and silhouette intact.
        for (x, y), (_, _, color) in atlas.items():
            if color in (7, 9, 10, 11, 12, 15) and top + 39 <= y <= top + 40:
                desired[x, y] = 2 if y == top + 39 else 1
        # Place the mini chest emblem in a solid original singlet region.
        target = ((left + right) / 2 + 2, top + 29)
        centers = []
        for (x, y), (_, _, color) in atlas.items():
            if color not in (4, 5) or not top + 24 <= y < top + 33:
                continue
            points = [(x, y - 1), (x - 1, y), (x, y), (x + 1, y), (x, y + 1)]
            if all(atlas.get(p, (0, 0, 0))[2] in (4, 5) for p in points):
                centers.append(((x - target[0]) ** 2 + (y - target[1]) ** 2, x, y))
        if centers:
            _, x, y = min(centers)
            desired.update(
                {(x, y - 1): 4, (x - 1, y): 8, (x, y): 5, (x + 1, y): 8, (x, y + 1): 8}
            )
        for position, new_color in desired.items():
            n, index, color = atlas[position]
            decoded = vram[n * 32 : (n + 1) * 32]
            matches = [
                (source, True)
                for f, dest, source, data in reversed(events)
                if f <= frame and dest == 0x7E2000 + n * 32 and data == decoded
            ]
            if matches:
                key = matches[0]
            else:
                source = rom.find(decoded)
                if source < 0 or rom.find(decoded, source + 1) >= 0:
                    missing += 1
                    continue
                key = (source, False)
            if key[0] not in excluded:
                votes[key][index][new_color] += 1
    assets = {(int(a["offset"], 0), a["compressed"]): a for a in plan["assets"]}
    for key, pixels in votes.items():
        asset = assets.setdefault(
            key, {"offset": f"0x{key[0]:06X}", "compressed": key[1], "pixels": []}
        )
        asset["details"] = [
            {"index": index, "color": counts.most_common(1)[0][0]}
            for index, counts in sorted(pixels.items())
        ]
    plan["assets"] = [asset for key, asset in sorted(assets.items())]
    plan["detail_mapping"] = {
        "draft": True,
        "excluded_shared_sources": [f"0x{s:06X}" for s in sorted(excluded)],
        "assets": len(votes),
        "unresolved_detail_samples": missing,
        "method": "Observed upright-walk landmarks and original material masks; needs visual review",
    }
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--initial-trace", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    report = add_details(
        args.rom.read_bytes(),
        args.trace,
        args.initial_trace,
        json.loads(args.plan.read_text()),
    )
    args.plan.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["detail_mapping"]))


if __name__ == "__main__":
    main()
