"""Map hand-authored gear landmarks to the exact observed walking tile assets.

Conflicting source-pixel placements are rejected instead of merged by voting.
Coordinates describe only the seven inspected left-walking poses.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from decode_sprite_tile import decode_sprite_tile
from extract_oam import objects, assemble
from inspect_rom import tile
from build_bret_gear import ORIGINAL_HASH


def add_details(rom, root, initial, plan, landmarks):
    if hashlib.sha256(rom).hexdigest() != ORIGINAL_HASH:
        raise ValueError("Requires the verified original USA ROM")
    events = []
    for directory, earlier in [(initial, True), (root, False)]:
        for line in (directory / "tiles.jsonl").read_text().splitlines():
            e = json.loads(line)
            if 0x7E2000 <= e["destination"] < 0x7E2800:
                source = e["source"] & 0x3FFFFF
                data, _ = decode_sprite_tile(rom, source)
                events.append(
                    (0 if earlier else e["frame"], e["destination"], source, data)
                )

    def pose(n):
        pre = root / f"frame-{n:06d}"

        def read(k):
            return Path(str(pre) + "-" + k + ".bin").read_bytes()

        v = read("vram")
        rs = objects(v, read("oam"), read("cgram"), read("registers")[0x2101])
        ids = [
            i
            for i, (r, im) in enumerate(rs)
            if r["palette"] == 0
            and 0 <= r["y"] < 190
            and -20 <= r["x"] < 256
            and im.getbbox()
        ]
        im, b = assemble(rs, ids)
        atlas = {}
        for i in reversed(ids):
            r = rs[i][0]
            size, number = r["size"], r["tile"]
            for ty in range(size // 8):
                for tx in range(size // 8):
                    num = ((number & 0xF0) + ty * 16 + ((number + tx) & 15)) & 255
                    raw = v[num * 32 : (num + 1) * 32]
                    matches = [
                        (source, True)
                        for f, dest, source, data in reversed(events)
                        if f <= n and dest == 0x7E2000 + num * 32 and data == raw
                    ]
                    if matches:
                        source, comp = matches[0]
                    else:
                        source = rom.find(raw)
                        comp = False
                        if source < 0 or rom.find(raw, source + 1) >= 0:
                            continue
                    for k, col in enumerate(tile(raw, 0, 4)):
                        if not col:
                            continue
                        dx, dy = tx * 8 + k % 8, ty * 8 + k // 8
                        x = r["x"] + (size - 1 - dx if r["hflip"] else dx) - b[0]
                        y = r["y"] + (size - 1 - dy if r["vflip"] else dy) - b[1]
                        atlas[x, y] = (source, comp, k, col)
        return im, atlas

    wanted = defaultdict(dict)
    all_occurrences = defaultdict(list)
    skin = (7, 9, 10, 11, 12, 15)
    for anno in landmarks["poses"]:
        n = anno["sample_frame"]
        im, atlas = pose(n)
        desired = {}
        digest = hashlib.sha256(im.tobytes()).hexdigest()
        if anno.get("sprite_sha256") and anno["sprite_sha256"] != digest:
            raise ValueError("Landmarks do not match the captured pose")
        anno["sprite_sha256"] = digest
        for (x, y), entry in atlas.items():
            if entry[3] not in skin:
                continue
            if any(
                ((x - ex) / 3.0) ** 2 + ((y - ey) / 2.5) ** 2 <= 1
                for ex, ey in anno["elbows"]
            ):
                desired[x, y] = 1
            if any(
                wx - w / 2 <= x < wx + w / 2 and wy - h / 2 <= y < wy + h / 2
                for wx, wy, w, h in anno["wrists"]
            ):
                desired[x, y] = 1
        cx, cy = anno["chest"]
        for dx, dy, col in [(0, -1, 4), (-1, 0, 8), (0, 0, 4), (1, 0, 8), (0, 1, 8)]:
            pos = cx + dx, cy + dy
            if pos in atlas and atlas[pos][3] in (4, 5):
                desired[pos] = col
        for pos, (src, comp, k, col) in atlas.items():
            key = (src, comp, k)
            all_occurrences[key].append((n, pos, desired.get(pos)))
            if pos in desired:
                wanted[key][n] = desired[pos]
    conflicts = []
    approved = {}
    for key, values in wanted.items():
        occ = all_occurrences[key]
        colors = set(values.values())
        missing = [o for o in occ if o[2] is None]
        if len(colors) > 1 or missing:
            conflicts.append(
                {"source": hex(key[0]), "index": key[2], "observations": occ}
            )
        else:
            approved[key] = next(iter(colors))
    # No vote/union: reject disagreements; physical tile pixels require one consistent annotation.
    assets = {(int(a["offset"], 0), a["compressed"]): a for a in plan["assets"]}
    for a in assets.values():
        a.pop("details", None)
    for (src, comp, k), color in approved.items():
        if src == 0x1225AB:
            continue
        a = assets.setdefault(
            (src, comp), {"offset": f"0x{src:06X}", "compressed": comp, "pixels": []}
        )
        a.setdefault("details", []).append({"index": k, "color": color})
    plan["assets"] = [a for key, a in sorted(assets.items())]
    plan["detail_mapping"] = {
        "draft": True,
        "method": "Explicit per-pose anatomy annotations; conflicting source pixels rejected, no majority voting",
        "pose_samples": [a["sample_frame"] for a in landmarks["poses"]],
        "rejected_conflicting_pixels": len(conflicts),
        "approved_detail_pixels": len(approved),
        "pose_sprite_hashes": {
            str(a["sample_frame"]): a["sprite_sha256"] for a in landmarks["poses"]
        },
    }

    return plan, conflicts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--initial-trace", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument(
        "--landmarks",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "data"
        / "bret-left-walk-landmarks.json",
    )
    parser.add_argument("--conflicts", type=Path, required=True)
    args = parser.parse_args()
    landmarks = json.loads(args.landmarks.read_text())
    result, conflicts = add_details(
        args.rom.read_bytes(),
        args.trace,
        args.initial_trace,
        json.loads(args.plan.read_text()),
        landmarks,
    )
    args.plan.write_text(json.dumps(result, indent=2) + "\n")
    args.landmarks.write_text(json.dumps(landmarks, indent=2) + "\n")
    args.conflicts.write_text(json.dumps(conflicts, indent=2) + "\n")
    print(json.dumps(result["detail_mapping"]))


if __name__ == "__main__":
    main()
