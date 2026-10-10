"""Map garment pixels from an original, upright walking trace.

The upright-pose cutoff (34 pixels below the head) is specific to this tested
walk. It is not a general classifier for attacks, falling, or other wrestlers.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from decode_sprite_tile import decode_sprite_tile
from extract_oam import assemble, objects
from inspect_rom import tile


def map_walk(rom, root, initial=None):
    events = [json.loads(s) for s in (root / "tiles.jsonl").read_text().splitlines()]
    if initial:
        prior = [
            json.loads(s) for s in (initial / "tiles.jsonl").read_text().splitlines()
        ]
        for e in prior:
            e["frame"] = 0
        events = prior + events
    by_destination = defaultdict(list)
    for e in events:
        if 0x7E2000 <= e["destination"] < 0x7E2800:
            source = e["source"] & 0x3FFFFF
            decoded, length = decode_sprite_tile(rom, source)
            by_destination[e["destination"]].append((e["frame"], source, decoded))
    assets = defaultdict(set)
    lower = defaultdict(set)
    poses = set()
    for png in sorted(root.glob("frame-*.png")):
        frame = int(png.stem.split("-")[1])
        prefix = png.with_suffix("")

        def read(name):
            return Path(str(prefix) + "-" + name + ".bin").read_bytes()

        vram = read("vram")
        records = objects(vram, read("oam"), read("cgram"), read("registers")[0x2101])
        ids = [
            i
            for i, (r, im) in enumerate(records)
            if r["palette"] == 0
            and 0 <= r["y"] < 190
            and -20 <= r["x"] < 256
            and im.getbbox()
        ]
        image, bounds = assemble(records, ids)
        poses.add(
            tuple(
                vram[r["tile"] * 32 : (r["tile"] + 1) * 32]
                for r, im in (records[i] for i in ids)
            )
        )
        cutoff = bounds[1] + 34
        for i in ids:
            record = records[i][0]
            number = record["tile"]
            size = record["size"]
            for ty in range(size // 8):
                for tx in range(size // 8):
                    n = ((number & 0xF0) + ty * 16 + ((number + tx) & 15)) & 255
                    decoded = vram[n * 32 : (n + 1) * 32]
                    pixels = tile(decoded, 0, 4)
                    if not any(p in (4, 5) for p in pixels):
                        continue
                    hits = [
                        (source, True)
                        for f, source, data in reversed(
                            by_destination[0x7E2000 + n * 32]
                        )
                        if f <= frame and data == decoded
                    ]
                    if hits:
                        source, compressed = hits[0]
                    else:
                        start = rom.find(decoded)
                        if start < 0 or rom.find(decoded, start + 1) >= 0:
                            raise ValueError(
                                f"Unresolved source for frame {frame}, tile {n}"
                            )
                        source, compressed = start, False
                    key = (source, compressed)
                    for y in range(8):
                        for x in range(8):
                            if pixels[y * 8 + x] not in (4, 5):
                                continue
                            dy = ty * 8 + y
                            if record["vflip"]:
                                dy = size - 1 - dy
                            target = assets if record["y"] + dy < cutoff else lower
                            target[key].add(y * 8 + x)
    conflicts = {
        key: values & lower[key]
        for key, values in assets.items()
        if values & lower[key]
    }
    if conflicts:
        raise ValueError(
            "Shared garment/tights pixels need separate mapping: " + str(conflicts)
        )
    return {
        "scope": "Upright left walking, first 90 frames after verified cold-boot pose",
        "sampled_frames": len(list(root.glob("frame-*.png"))),
        "distinct_object_tile_layouts": len(poses),
        "assets": [
            {
                "offset": f"0x{source:06X}",
                "compressed": compressed,
                "pixels": sorted(pixels),
            }
            for (source, compressed), pixels in sorted(assets.items())
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--initial-trace", type=Path)
    args = parser.parse_args()
    report = map_walk(args.rom.read_bytes(), args.trace, args.initial_trace)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        "Mapped",
        len(report["assets"]),
        "assets across",
        report["sampled_frames"],
        "frames",
    )


if __name__ == "__main__":
    main()
