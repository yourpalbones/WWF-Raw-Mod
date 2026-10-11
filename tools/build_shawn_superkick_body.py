"""Build leaning full-body pose keyframes for the experimental Shawn superkick.

Source snapshots are local, hash-checked emulator captures. Generated ROM and
raw pixel buffers remain local; only authored code, metadata and IPS are shared.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

from build_shawn_superkick_pose import build as build_pose
from build_shawn_kick_prototype import Program
from inspect_rom import tile
from extract_oam import objects
from build_bret_gear import planar
from inventory_bret_frames import parse_frame


def checked_snapshot(prefix, name, expected_hash):
    data = Path(str(prefix) + "-" + name + ".bin").read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError("Unexpected reference snapshot: " + name)
    return data


def build(rom, reference):
    manifest = json.loads(
        (
            Path(__file__).resolve().parents[1] / "data/shawn-superkick-body.json"
        ).read_text()
    )
    r = bytearray(build_pose(rom, reference / "frame-000024")[0])
    tilecount = 0
    maps = [{}, {}]
    report = []
    for stage in manifest["stages"]:
        frame = stage["reference_frame"]
        angle = stage["torso_rotation_degrees"]
        anchors = stage["anchors"]
        prefix = reference / f"frame-{frame:06d}"

        def get(n):
            return checked_snapshot(prefix, n, stage["snapshot_hashes"][n])

        v = get("vram")
        rr = objects(v, get("oam"), get("cgram"), get("registers")[0x2101])
        es = stage["parts"]
        offset = 18
        for part, e in enumerate(es[:2]):
            original = parse_frame(rom, e["descriptor"])
            count = original["objects"]
            canvas = {}
            for index in range(offset, offset + count):
                rec, _ = rr[index]
                sz = rec["size"]
                for ty in range(sz // 8):
                    for tx in range(sz // 8):
                        n = (
                            (rec["tile"] & 0xF0) + ty * 16 + ((rec["tile"] + tx) & 15)
                        ) & 255
                        for k, c in enumerate(tile(v, n * 32, 4)):
                            if not c:
                                continue
                            x = tx * 8 + k % 8
                            y = ty * 8 + k // 8
                            if rec["hflip"]:
                                x = sz - 1 - x
                            if rec["vflip"]:
                                y = sz - 1 - y
                            canvas[(rec["x"] + x, rec["y"] + y)] = c
            # Use read-only native anchor observations from the reference capture.
            anchor = next(
                a
                for a in anchors
                if a["frame"] == frame - 2 and a["descriptor"] == e["descriptor"]
            )
            basex = anchor["x"] - manifest["camera_offset"][0]
            basey = anchor["y"] - 105 - manifest["camera_offset"][1]
            offset += count
            pivot = tuple(manifest["hip_pivot_screen"])
            a = math.radians(angle if part == 0 else (30 if frame == 24 else 0))
            co = math.cos(a)
            si = math.sin(a)

            def transformable(x, y):
                return part == 0 or y < 120 or (x < 131 and y < 128)

            moving = {p: c for p, c in canvas.items() if transformable(*p)}
            result = {p: c for p, c in canvas.items() if not transformable(*p)}
            for y in range(64, 168):
                for x in range(72, 193):
                    dx = x - pivot[0]
                    dy = y - pivot[1]
                    src = (
                        round(pivot[0] + co * dx + si * dy),
                        round(pivot[1] - si * dx + co * dy),
                    )
                    if src in moving:
                        result[(x, y)] = moving[src]
            candidates = []
            for gy in (64, 68, 72, 76):
                for gx in (64, 68, 72, 76):
                    groups = []
                    for y in range(gy, 176, 16):
                        for x in range(gx, 193, 16):
                            block = [
                                result.get((x + xx, y + yy), 0)
                                for yy in range(16)
                                for xx in range(16)
                            ]
                            nonempty = []
                            for ty, tx in ((0, 0), (0, 1), (1, 0), (1, 1)):
                                pixels = [
                                    block[(ty * 8 + yy) * 16 + tx * 8 + xx]
                                    for yy in range(8)
                                    for xx in range(8)
                                ]
                                if any(pixels):
                                    nonempty.append((x + tx * 8, y + ty * 8, pixels))
                            if nonempty:
                                groups.append((x, y, block, nonempty))
                    candidates.append(groups)
            groups = min(candidates, key=lambda g: (len(g), sum(len(z[3]) for z in g)))
            if part == 0:
                pending = []
            pending.append((part, e, basex, basey, groups, count))
        # Choose mixed object sizes under both the original OAM allocation and tile budget.
        budget = sum(p[5] for p in pending)
        states = {(0, 0): []}
        flat = [
            (pidx, gidx, g)
            for pidx, p in enumerate(pending)
            for gidx, g in enumerate(p[4])
        ]
        for pidx, gidx, g in flat:
            n = len(g[3])
            options = [(n, n, False)] if n < 4 else [(1, 4, True)]
            if 1 < n < 4:
                options.append((1, 4, True))
            nxt = {}
            for (o, t), choices in states.items():
                for oo, tt, large in options:
                    key = (o + oo, t + tt)
                    if key[0] <= budget and key[1] + 4 <= 64:
                        nxt[key] = choices + [large]
            states = nxt
        if not states:
            raise ValueError(("Cannot fit native OAM/tile budget", frame, budget))
        key = min(states, key=lambda k: (k[1], k[0]))
        choices = states[key]
        objects_by_part = [[], []]
        for (pidx, gidx, g), large in zip(flat, choices):
            if large:
                objects_by_part[pidx].append((g[0], g[1], 16, g[2]))
            else:
                objects_by_part[pidx].extend((x, y, 8, pix) for x, y, pix in g[3])
        for pidx, (part, e, basex, basey, groups, count) in enumerate(pending):
            chunks = sorted(objects_by_part[pidx], key=lambda z: -z[2])
            d = bytearray([len(chunks), sum(c[2] == 16 for c in chunks)])
            for x, y, size, pixels in chunks:
                relx = basex - x - 1
                rely = y - basey
                assert -64 <= relx < 64 and 0 <= rely < 128, (
                    frame,
                    part,
                    x,
                    y,
                    basex,
                    basey,
                )
                pixels = [
                    pixels[yy * size + size - 1 - xx]
                    for yy in range(size)
                    for xx in range(size)
                ]
                d.extend(bytes([0, relx & 127, rely]))
                for ty in range(size // 8):
                    for tx in range(size // 8):
                        packet = planar(
                            [
                                pixels[(ty * 8 + yy) * size + tx * 8 + xx]
                                for yy in range(8)
                                for xx in range(8)
                            ]
                        )
                        r[
                            0x320000 + tilecount * 32 : 0x320000 + (tilecount + 1) * 32
                        ] = packet
                        d.extend(tilecount.to_bytes(2, "little"))
                        tilecount += 1
            address = 0x310400 + (frame // 6 - 2) * 0x300 + part * 0x180
            r[address : address + len(d)] = d
            maps[part][e["part_id"]] = address & 65535
            report.append(
                {
                    "frame": frame,
                    "part": part,
                    "id": e["part_id"],
                    "objects": len(chunks),
                    "anchor": [basex, basey],
                    "angle": angle if part == 0 else (30 if frame == 24 else 0),
                    "combined_objects": key[0],
                    "native_objects": budget,
                    "combined_tiles_with_shadow": key[1] + 4,
                }
            )

    def hook(part):
        b = Program()
        b.emit("08 48 da a6 36 bd 74 0b c9 10 00")
        b.branch("d0", "fallback")
        b.emit("bd ec 0b c9 43 53")
        b.branch("f0", "dispatch")
        b.emit("c9 44 53")
        b.branch("f0", "dispatch")
        b.label("fallback")
        b.emit(
            "fa 68 28 "
            + ("7f 13 d5 ad 5c c5 ec 80" if part == 0 else "7f 47 d5 ad 5c 1d ed 80")
        )
        b.label("dispatch")
        b.emit("fa 68")
        for index, ident in enumerate(maps[part]):
            b.emit("c9 " + ident.to_bytes(2, "little").hex(" "))
            b.branch("f0", f"pose{index}")
        if part == 1:
            b.emit("c9 a8 00")
            b.branch("f0", "clear")
            b.emit("c9 72 00")
            b.branch("d0", "popped")
            b.label("clear")
            b.emit("48 da a6 36 9e ec 0b fa 68")
        b.label("popped")
        b.emit(
            "28 "
            + ("7f 13 d5 ad 5c c5 ec 80" if part == 0 else "7f 47 d5 ad 5c 1d ed 80")
        )
        for index, (ident, address) in enumerate(maps[part].items()):
            b.label(f"pose{index}")
            b.emit(
                "28 a9 f1 00 85 82 "
                + ("99 50 05" if part == 0 else "99 52 05")
                + " a9 "
                + address.to_bytes(2, "little").hex(" ")
                + " 85 80 "
                + (
                    "99 4e 05 c8 c8 5c e2 ec 80"
                    if part == 0
                    else "99 50 05 5c 38 ed 80"
                )
            )
        return b.finish()

    for part, address, entry in ((0, 0x300500, 0xECC1), (1, 0x300700, 0xED19)):
        code = hook(part)
        r[address : address + len(code)] = code
        r[entry : entry + 4] = bytes([0x5C, address & 255, (address >> 8) & 255, 0xF0])
    r[0xFFDC:0xFFE0] = bytes.fromhex("ffff0000")
    c = sum(r) & 65535
    r[0xFFDC:0xFFE0] = (c ^ 65535).to_bytes(2, "little") + c.to_bytes(2, "little")
    patch = bytearray(b"PATCH")
    for address in range(0x300000, 0x400000, 65535):
        length = min(65535, 0x400000 - address)
        patch += (
            address.to_bytes(3, "big") + b"\0\0" + length.to_bytes(2, "big") + b"\xff"
        )
    baseline = rom + b"\xff" * (len(r) - len(rom))
    i = 0
    while i < len(r):
        if baseline[i] == r[i]:
            i += 1
            continue
        start = i
        while i < len(r) and baseline[i] != r[i] and i - start < 65535:
            i += 1
        data = r[start:i]
        patch += start.to_bytes(3, "big") + len(data).to_bytes(2, "big") + data
    patch += b"EOF"
    metadata = {
        "original_sha256": hashlib.sha256(rom).hexdigest(),
        "patched_sha256": hashlib.sha256(r).hexdigest(),
        "ips_sha256": hashlib.sha256(patch).hexdigest(),
        "poses": report,
        "private_tiles": tilecount,
        "experimental": True,
        "complete_animation_replacement": False,
        "scope": manifest["scope"],
        "allocation": "Mixed 8x8/16x16 objects; each phase fits its original combined primary/secondary object allocation and a 64-tile actor budget including shadow.",
    }
    return bytes(r), bytes(patch), metadata


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom", type=Path)
    ap.add_argument(
        "reference",
        type=Path,
        help="Directory containing verified frame 18, 24 and 30 reference snapshots",
    )
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    rom, patch, metadata = build(args.rom.read_bytes(), args.reference)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "shawn-superkick-body.sfc").write_bytes(rom)
    (args.output / "shawn-superkick-body.ips").write_bytes(patch)
    (args.output / "patch-report.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
