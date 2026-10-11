"""Build a drawn eight-pose superkick sequence isolated to Shawn's R finisher."""

import argparse
import hashlib
import json
from pathlib import Path

from build_shawn_superkick_pose import build as build_pose
from build_shawn_kick_prototype import Program
from build_bret_gear import planar
from draw_shawn_superkick import POSES, pose
from import_shawn_superkick_art import load_pose


def pack(image):
    """Choose small/large objects within the actor's OAM and tile limits."""
    candidates = []
    for gy in range(0, 16, 4):
        for gx in range(0, 16, 4):
            groups = []
            for y in range(gy - 16, 96, 16):
                for x in range(gx - 16, 96, 16):
                    block = [
                        image.getpixel((x + xx, y + yy))
                        if 0 <= x + xx < 96 and 0 <= y + yy < 96
                        else 0
                        for yy in range(16)
                        for xx in range(16)
                    ]
                    small = []
                    for ty, tx in ((0, 0), (0, 1), (1, 0), (1, 1)):
                        pix = [
                            block[(ty * 8 + yy) * 16 + tx * 8 + xx]
                            for yy in range(8)
                            for xx in range(8)
                        ]
                        if any(pix):
                            small.append((x + tx * 8, y + ty * 8, 8, pix))
                    if small:
                        groups.append((x, y, block, small))
            states = {(0, 0): []}
            for x, y, block, small in groups:
                nxt = {}
                for (objects, tiles), chosen in states.items():
                    for parts, cost in [(small, len(small)), ([(x, y, 16, block)], 4)]:
                        key = (objects + len(parts), tiles + cost)
                        if key[0] <= 17 and key[1] <= 60:
                            nxt[key] = chosen + parts
                states = nxt
            if states:
                candidates.extend(states.items())
    if not candidates:
        raise ValueError("Drawn pose exceeds actor allocation")
    return candidates


def install_poses(
    r,
    art_dir,
    count=8,
    *,
    profile_base=0x2000,
    descriptor_base=0x4000,
    tile_base=0,
    primary_id=600,
    secondary_id=1008,
    upper_table=0x1C00,
    lower_table=0x1D00,
    sequence=True,
    step_back=0,
):
    """Install complete indexed poses into private graphics profiles and tiles."""
    tiles = 0
    report = []
    # 7-byte native sequence entries point at 14-byte graphics profiles.
    for i in range(count):
        profile = profile_base + i * 14
        if sequence:
            r[0x311000 + i * 7 : 0x311007 + i * 7] = (
                bytes([0xF1])
                + profile.to_bytes(2, "little")
                + bytes(
                    [
                        (-step_back if i == 0 else step_back if i == 1 else 0) & 255,
                        0,
                        0,
                        0,
                    ]
                )
            )
        descriptor = descriptor_base + i * 0x300
        ident = primary_id + i * 3
        r[0x310000 + upper_table + i * 3 : 0x310003 + upper_table + i * 3] = (
            descriptor.to_bytes(2, "little") + bytes(1)
        )
        r[0x310000 + lower_table + i * 3 : 0x310003 + lower_table + i * 3] = (
            descriptor + 0x180
        ).to_bytes(2, "little") + bytes(1)
        # Fixed anchors, upper/lower body descriptors and native shadow.
        record = (
            ident.to_bytes(2, "little")
            + bytes.fromhex("03 d1")
            + (0x8000 | secondary_id + i * 3).to_bytes(2, "little")
            + bytes.fromhex("00 ff 24 80 00 ff ff ff")
        )
        r[0x310000 + profile : 0x310000 + profile + 14] = record
        total_objects = total_cost = 0
        pairs = []
        # Keep the established split when it fits. Broad neutral stances may
        # need a different upper/lower boundary to avoid wasted tile rows.
        for split_y in (48, 40, 44, 52, 56, 60):
            packed = []
            for part in range(2):
                image = load_pose(i, art_dir) if art_dir else pose(i)
                for yy in range(96):
                    if (yy < split_y) != (part == 0):
                        for xx in range(96):
                            image.putpixel((xx, yy), 0)
                packed.append(pack(image))
            pairs = [
                (a, b)
                for a in packed[0]
                for b in packed[1]
                if a[0][0] + b[0][0] <= 17 and a[0][1] + b[0][1] <= 60
            ]
            if pairs:
                break
        if not pairs:
            raise ValueError(("Cannot pack combined artwork", i))
        chosen = min(
            pairs, key=lambda ab: (ab[0][0][1] + ab[1][0][1], ab[0][0][0] + ab[1][0][0])
        )
        for part, ((objects, cost), chunks) in enumerate(chosen):
            chunks = sorted(chunks, key=lambda c: -c[2])
            total_objects += objects
            total_cost += cost
            d = bytearray([objects, sum(c[2] == 16 for c in chunks)])
            for x, y, size, pixels in chunks:
                screenx = 137 - (x + size - 1 - 44)
                screeny = 113 + y - 49
                basex, basey = (113, 10) if part == 0 else (116, 56)
                relx = basex - screenx - 1 + (8 if size == 8 else 0)
                rely = screeny - basey
                if not -64 <= relx < 64 or not 0 <= rely < 128:
                    raise ValueError(
                        (
                            "Object outside native offset range",
                            i,
                            part,
                            x,
                            y,
                            relx,
                            rely,
                        )
                    )
                d.extend([0, relx & 127, rely])
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
                            0x320000 + (tile_base + tiles) * 32 : 0x320020
                            + (tile_base + tiles) * 32
                        ] = packet
                        d.extend((tile_base + tiles).to_bytes(2, "little"))
                        tiles += 1
            address = 0x310000 + descriptor + part * 0x180
            r[address : address + len(d)] = d
        if total_objects > 17 or total_cost + 4 > 64:
            raise ValueError(
                ("Combined actor budget exceeded", i, total_objects, total_cost)
            )
        report.append(
            {
                "pose": i,
                "primary_id": ident,
                "objects": total_objects,
                "tiles_including_shadow": total_cost + 4,
            }
        )
    return report


def build(rom, reference, art_dir=None, step_back=0):
    if not 0 <= step_back <= 8:
        raise ValueError("Step-back distance must be between zero and eight pixels")
    r = bytearray(build_pose(rom, reference)[0])
    report = install_poses(r, art_dir, step_back=step_back)
    r[0x311000 + len(POSES) * 7] = 255
    r[0x313E00:0x313E02] = bytes(2)
    # Redirect only the marked special to its own native sequence table.
    b = Program()
    b.emit("08 48 da c9 7e 00")
    b.branch("d0", "fallback")
    b.emit("a6 36 bd 74 0b c9 10 00")
    b.branch("d0", "fallback")
    b.emit("bd ec 0b c9 43 53")
    b.branch("f0", "sequence")
    b.emit("c9 44 53")
    b.branch("d0", "fallback")
    b.label("sequence")
    b.emit("fa 68 28 a9 f1 00 85 7e a5 48 18 69 00 10 85 7c 5c 80 f0 80")
    b.label("fallback")
    b.emit("fa 68 28 85 7c 48 a5 7e c9 f1 00")
    b.branch("d0", "bank_done")
    b.emit("a9 c4 00 85 7e")
    b.label("bank_done")
    b.emit("68 a7 7c 5c 77 f0 80")
    if r[0xF073:0xF077] != bytes.fromhex("85 7c a7 7c"):
        raise ValueError("Unexpected sequence hook")
    r[0x300900 : 0x300900 + len(b.finish())] = b.finish()
    r[0xF073:0xF077] = bytes.fromhex("5c 00 09 f0")
    for part, entry, address in [(0, 0xECC1, 0x300500), (1, 0xED19, 0x300700)]:
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
        if part == 0:
            b.emit("c9 58 02")
            b.branch("90", "original")
            b.emit("c9 70 02")
            b.branch("b0", "original")
            b.emit(
                "da 38 e9 58 02 aa bf 00 1c f1 fa 28 85 80 99 4e 05 a9 f1 00 85 82 99 50 05 c8 c8 5c e2 ec 80"
            )
        else:
            b.emit("c9 f0 03")
            b.branch("90", "idle")
            b.emit("c9 08 04")
            b.branch("b0", "idle")
            b.emit(
                "da 38 e9 f0 03 aa bf 00 1d f1 fa 28 85 80 99 50 05 a9 f1 00 85 82 99 52 05 5c 38 ed 80"
            )
            b.label("idle")
            b.emit("c9 a8 00")
            b.branch("f0", "clear")
            b.emit("c9 72 00")
            b.branch("d0", "original")
            b.label("clear")
            b.emit("48 da a6 36 9e ec 0b fa 68")
        b.label("original")
        b.emit(
            "28 "
            + ("7f 13 d5 ad 5c c5 ec 80" if part == 0 else "7f 47 d5 ad 5c 1d ed 80")
        )
        code = b.finish()
        r[address : address + len(code)] = code
        r[entry : entry + 4] = bytes([0x5C, address & 255, address >> 8 & 255, 0xF0])
    r[0xFFDC:0xFFE0] = bytes.fromhex("ff ff 00 00")
    checksum = sum(r) & 65535
    r[0xFFDC:0xFFE0] = (checksum ^ 65535).to_bytes(2, "little") + checksum.to_bytes(
        2, "little"
    )
    patch = bytearray(b"PATCH")
    for address in range(0x300000, 0x400000, 65535):
        length = min(65535, 0x400000 - address)
        patch += (
            address.to_bytes(3, "big") + bytes(2) + length.to_bytes(2, "big") + b"\xff"
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
        "newly_drawn_artwork": True,
        "artwork_assets": str(art_dir) if art_dir else None,
        "artwork_manifest_sha256": hashlib.sha256(
            (art_dir / "manifest.json").read_bytes()
        ).hexdigest()
        if art_dir
        else None,
        "native_sequence_entries": len(POSES),
        "stock_kick_sequence_entries": 4,
        "step_back_world_pixels": step_back,
        "sequence_forward_offsets": [-step_back, step_back] + [0] * 6,
        "experimental": True,
        "limitations": [
            "Reference-guided artwork draft; style and transitions still need review"
            if art_dir
            else "Initial artwork is a geometric pixel-art draft",
            "Native kick collision/damage logic retained; new visual sequence requires gameplay validation",
            "Full match, interruptions, AI and player 2 as Shawn unverified",
        ],
    }
    return bytes(r), bytes(patch), metadata


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom", type=Path)
    ap.add_argument("reference", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--art-dir", type=Path, help="Hash-checked authored indexed poses")
    ap.add_argument(
        "--step-back",
        type=int,
        default=0,
        help="Native backward/forward preparation step (0 to 8 world pixels)",
    )
    args = ap.parse_args()
    rom, ips, report = build(
        args.rom.read_bytes(), args.reference, args.art_dir, args.step_back
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "shawn-superkick-animation.sfc").write_bytes(rom)
    (args.output / "shawn-superkick-animation.ips").write_bytes(ips)
    (args.output / "patch-report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
