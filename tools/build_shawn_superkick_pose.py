"""Build an isolated raised-leg extension for the experimental Shawn finisher.

The reference snapshot is generated locally from the user's original ROM.
No extracted tiles or emulator memory files are distributed with this tool.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

from build_shawn_kick_prototype import build as build_base, Program
from build_bret_gear import planar
from inspect_rom import tile
from extract_oam import objects


def build(rom, snapshot):
    manifest = json.loads(
        (
            Path(__file__).resolve().parents[1] / "data/shawn-superkick-pose.json"
        ).read_text()
    )

    def get(name):
        data = Path(str(snapshot) + "-" + name + ".bin").read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest["source_hashes"][name]:
            raise ValueError(
                "Snapshot does not match the verified stock kick reference: " + name
            )
        return data

    r = bytearray(build_base(rom)[0])
    v = get("vram")
    rr = objects(v, get("oam"), get("cgram"), get("registers")[0x2101])
    canvas = {}
    for i in manifest["source_objects"]:
        rec, _ = rr[i]
        size = rec["size"]
        for ty in range(size // 8):
            for tx in range(size // 8):
                number = (
                    (rec["tile"] & 0xF0) + ty * 16 + ((rec["tile"] + tx) & 15)
                ) & 255
                data = tile(v, number * 32, 4)
                for k, c in enumerate(data):
                    if c:
                        x = tx * 8 + k % 8
                        y = ty * 8 + k // 8
                        if rec["hflip"]:
                            x = size - 1 - x
                        if rec["vflip"]:
                            y = size - 1 - y
                        canvas[(rec["x"] + x, rec["y"] + y)] = c
    # Rotate the kicking thigh/shin/boot about its connection at the hip.
    pivot = tuple(manifest["pivot_screen"])
    angle = math.radians(manifest["rotation_degrees"])
    cos = math.cos(angle)
    sin = math.sin(angle)

    def mask(x, y):
        return y < 120 or (x < 131 and y < 128)

    leg = {p: c for p, c in canvas.items() if mask(*p)}
    result = {p: c for p, c in canvas.items() if not mask(*p)}
    for y in range(72, 136):
        for x in range(80, 153):
            dx = x - pivot[0]
            dy = y - pivot[1]
            sx = round(pivot[0] + cos * dx + sin * dy)
            sy = round(pivot[1] - sin * dx + cos * dy)
            if (sx, sy) in leg:
                result[(x, y)] = leg[(sx, sy)]
    # The standing leg stays at its native coordinates. Pack non-empty 16x16 objects.
    chunks = []
    tiles = []
    for y in range(72, 168, 16):
        for x in range(80, 160, 16):
            pixels = [
                result.get((x + xx, y + yy), 0) for yy in range(16) for xx in range(16)
            ]
            if not any(pixels):
                continue
            # Authored artwork uses canonical right-facing pixels; the native left flip restores this view.
            pixels = [pixels[yy * 16 + 15 - xx] for yy in range(16) for xx in range(16)]
            ids = []
            for ty, tx in ((0, 0), (0, 1), (1, 0), (1, 1)):
                ids.append(len(tiles))
                tiles.append(
                    planar(
                        [
                            pixels[(ty * 8 + yy) * 16 + tx * 8 + xx]
                            for yy in range(8)
                            for xx in range(8)
                        ]
                    )
                )
            chunks.append((x, y, ids))
    d = bytearray([len(chunks), len(chunks)])
    for x, y, ids in chunks:
        d.extend([0, (109 - x - 1) & 127, (y - 56) & 127])
        for i in ids:
            d.extend(i.to_bytes(2, "little"))
    r[0x310100 : 0x310100 + len(d)] = d
    r[0x320000 : 0x320000 + len(tiles) * 32] = b"".join(tiles)
    # Secondary part pointer redirect, preserving the original carry flag on fallback.
    b = Program()
    b.emit("08 48 da a6 36 bd 74 0b c9 10 00")
    b.branch("d0", "fallback")
    b.emit("bd b4 06 c9 7e 00")
    b.branch("f0", "kick")
    b.emit("bd ec 0b c9 43 53")
    b.branch("f0", "clear")
    b.emit("c9 44 53")
    b.branch("d0", "fallback")
    b.label("clear")
    b.emit("9e ec 0b")
    b.branch("80", "fallback")
    b.label("kick")
    b.emit("bd ec 0b c9 43 53")
    b.branch("f0", "marked")
    b.emit("c9 44 53")
    b.branch("d0", "fallback")
    b.label("marked")
    b.emit("fa 68 c9 89 01")
    b.branch("d0", "check_idle")
    b.emit("28 a9 f1 00 85 82 99 52 05 a9 00 01 85 80 99 50 05 5c 38 ed 80")
    b.label("check_idle")
    b.emit("c9 a8 00")
    b.branch("f0", "idle_part")
    b.emit("c9 72 00")
    b.branch("d0", "popped")
    b.label("idle_part")
    # Parts are requested before the current action is written back to actor RAM.
    # Recognize the observed idle lower-body parts ($00A8 / $0072), not only the old action.
    b.emit("da a6 36 9e ec 0b fa a9 a8 00")
    b.branch("80", "popped")
    b.label("fallback")
    b.emit("fa 68")
    b.label("popped")
    b.emit("28 7f 47 d5 ad 5c 1d ed 80")
    r[0x300300 : 0x300300 + len(b.finish())] = b.finish()
    assert r[0xED19:0xED1D] == bytes.fromhex("7f47d5ad")
    r[0xED19:0xED1D] = bytes.fromhex("5c0003f0")
    # Preserve a distinct visual marker after native impact, then clear it at idle.
    needle = bytes.fromhex("9e ec 0b fa bd 78 0a")
    pos = r.find(needle, 0x300100, 0x300200)
    assert pos >= 0
    # Rebuild the contact callback to retain a separate post-impact visual marker.
    b = Program()
    b.emit("85 90 da a6 36 bd 74 0b c9 10 00")
    b.branch("d0", "original")
    b.emit("bd ec 0b c9 43 53")
    b.branch("d0", "original")
    b.emit("bd b4 06 c9 7e 00")
    b.branch("d0", "original")
    b.emit("a9 44 53 9d ec 0b fa bd 78 0a 38 e9 7e 00")
    b.branch("b0", "store")
    b.emit("a9 00 00")
    b.label("store")
    b.emit("9d 78 0a a9 84 03 85 90 bd e4 06 5c 27 cd 80")
    b.label("original")
    b.emit("fa bd e4 06 5c 27 cd 80")
    r[0x300100 : 0x300100 + len(b.finish())] = b.finish()
    raw = bytes.fromhex(
        "68 48 eb 4a 4a 4a 29 1f 00 18 69 f2 00 85 dd 68 29 ff 07 0a 0a 0a 0a 0a 85 db a9 00 00 6b"
    )
    guard = bytes.fromhex("48 a5 82 29 ff 00 c9 f1 00 d0") + bytes([len(raw)])
    fallback = bytes.fromhex("68 cf 48 0f 00 5c e8 f6 ac")
    lookup = guard + raw + fallback
    r[0x300400 : 0x300400 + len(lookup)] = lookup
    r[0x2CF6E4:0x2CF6E8] = bytes.fromhex("5c0004f0")
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
    report = {
        "original_sha256": hashlib.sha256(rom).hexdigest(),
        "patched_sha256": hashlib.sha256(r).hexdigest(),
        "ips_sha256": hashlib.sha256(patch).hexdigest(),
        "experimental": True,
        "authored_pose_changes": "Rotate the stock kicking leg upward 30 degrees about the hip; supporting leg retains its original pixels and coordinates.",
        "private_secondary_part_id": 393,
        "private_descriptor_bank": "F1",
        "private_raw_tile_bank": "F2",
        "private_objects": len(chunks),
        "private_tiles": len(tiles),
        "private_tile_bytes": len(tiles) * 32,
        "scope": "One extension phase; stock wind-up, knee lift and recovery retained.",
        "complete_move_validation": False,
        "marker": "$5343 pending contact, $5344 after contact; cleared on idle part request or ordinary kick entry.",
    }
    return bytes(r), bytes(patch), report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom", type=Path)
    ap.add_argument(
        "snapshot", type=Path, help="Verified native reference prefix, without suffix"
    )
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    rom, patch, report = build(args.rom.read_bytes(), args.snapshot)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "shawn-superkick-pose.sfc").write_bytes(rom)
    (args.output / "shawn-superkick-pose.ips").write_bytes(patch)
    (args.output / "patch-report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
