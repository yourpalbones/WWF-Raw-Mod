"""Extend authored gear pixels using explicit regions on observed running poses.

This maps only supplied, hash-checked poses, not arbitrary move anatomy.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from build_bret_gear import ORIGINAL_HASH
from decode_sprite_tile import decode_sprite_tile
from extract_oam import assemble, objects
from inspect_rom import tile


def pose_atlas(rom, root, initial, frame):
    events = defaultdict(list)
    for directory, earlier in [(initial, True), (root, False)]:
        for line in (directory / "tile_calls.jsonl").read_text().splitlines():
            e = json.loads(line)
            if e["actor_slot"] != 0 or not 0x7E2000 <= e["destination"] < 0x7E2800:
                continue
            source = e["source"] & 0x3FFFFF
            compressed = bool(e["compressed"])
            data = (
                decode_sprite_tile(rom, source)[0]
                if compressed
                else rom[source : source + 32]
            )
            events[e["destination"]].append(
                (0 if earlier else e["frame"], source, compressed, data)
            )
    prefix = root / f"frame-{frame:06d}"

    def read(kind):
        return Path(str(prefix) + "-" + kind + ".bin").read_bytes()

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
    body, bounds = assemble(records, ids)
    atlas = {}
    for i in reversed(ids):
        r = records[i][0]
        size, number = r["size"], r["tile"]
        for ty in range(size // 8):
            for tx in range(size // 8):
                n = ((number & 0xF0) + ty * 16 + ((number + tx) & 15)) & 255
                raw = vram[n * 32 : (n + 1) * 32]
                hits = [
                    (s, c)
                    for f, s, c, data in reversed(events[0x7E2000 + n * 32])
                    if f <= frame and data == raw
                ]
                if hits:
                    source, compressed = hits[0]
                else:
                    source = rom.find(raw)
                    if source < 0 or rom.find(raw, source + 1) >= 0:
                        raise ValueError(f"Unresolved source: frame {frame}, tile {n}")
                    compressed = False
                for k, color in enumerate(tile(raw, 0, 4)):
                    if not color:
                        continue
                    dx, dy = tx * 8 + k % 8, ty * 8 + k // 8
                    x = r["x"] + (size - 1 - dx if r["hflip"] else dx) - bounds[0]
                    y = r["y"] + (size - 1 - dy if r["vflip"] else dy) - bounds[1]
                    atlas[x, y] = (source, compressed, k, color)
    return hashlib.sha256(body.tobytes()).hexdigest(), atlas


def extend(rom, initial, root, plan, annotations):
    if hashlib.sha256(rom).hexdigest() != ORIGINAL_HASH:
        raise ValueError("Requires the verified original ROM")
    assets = {(int(a["offset"], 0), a["compressed"]): a for a in plan["assets"]}
    observations = defaultdict(list)
    for annotation in annotations:
        digest, atlas = pose_atlas(rom, root, initial, annotation["sample_frame"])
        if digest != annotation["sprite_sha256"]:
            raise ValueError("Captured pose differs from authored annotation")
        for (x, y), (source, compressed, index, color) in atlas.items():
            if color not in (4, 5):
                continue
            inside = any(
                left <= x < right and top <= y < bottom
                for left, top, right, bottom in annotation["garment_regions"]
            )
            observations[source, compressed, index].append(inside)
    for (source, compressed, index), values in observations.items():
        key = source, compressed
        previous = index in assets.get(key, {}).get("pixels", [])
        if any(values) and not all(values) or previous and not all(values):
            raise ValueError(
                f"Shared torso/tights pixel conflict: {source:06X}:{index}"
            )
        if any(values):
            if source == 0x1225AB:
                raise ValueError("Would edit excluded shared object source")
            a = assets.setdefault(
                key,
                {"offset": f"0x{source:06X}", "compressed": compressed, "pixels": []},
            )
            a["pixels"] = sorted(set(a["pixels"]) | {index})
    plan["assets"] = [a for key, a in sorted(assets.items())]
    plan["scope"] = (
        "Authored standing/walking poses plus six observed running back/side poses; other moves unverified"
    )
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--initial-trace", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    annotations = [
        a
        for a in json.loads(args.annotations.read_text())["poses"]
        if a["case"] == args.case
    ]
    if not annotations:
        raise ValueError("No annotations for this case")
    plan = extend(
        args.rom.read_bytes(),
        args.initial_trace,
        args.trace,
        json.loads(args.plan.read_text()),
        annotations,
    )
    args.plan.write_text(json.dumps(plan, indent=2) + "\n")
    print(
        "Mapped",
        len(annotations),
        "running poses;",
        len(plan["assets"]),
        "total sources",
    )


if __name__ == "__main__":
    main()
