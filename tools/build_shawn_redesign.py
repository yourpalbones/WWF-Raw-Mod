"""Replace Shawn's idle/walk graphics while retaining the tested superkick.

Only native idle/walking profiles are redirected, with an actor identity guard.
Other actions retain stock art; this is not a complete character replacement.
"""

import argparse
import hashlib
import json
from pathlib import Path

from build_shawn_kick_prototype import Program
from build_shawn_superkick_animation import build as build_finisher, install_poses

# Native profiles referenced by idle/walk/diagonal sequences at C4:03A2..0671.
# Individual runtime coverage is reported separately by the verifier.
# Artwork indices 0/1 are idle variants; 2..7 form the six-pose walk cycle.
PROFILE_POSES = {
    0xC84692: 0,
    **{0xC846AE + i * 14: 2 + i for i in range(6)},
    **{0xC84702 + i * 14: 3 + i for i in range(5)},
    **{0xC84748 + i * 14: 5 + i for i in range(3)},
    0xC84596: 8,
    **{0xC845B2 + i * 14: 10 + i for i in range(6)},
    **{0xC84606 + i * 14: 10 + i for i in range(3)},
    **{0xC84630 + i * 14: 14 + i for i in range(2)},
    **{0xC8464C + i * 14: 11 + i for i in range(5)},
}


def profile_hook():
    p = Program()
    p.emit("85 7c 86 7e 08 48 da a6 36 bd 74 0b c9 10 00")
    p.branch("d0", "fallback")
    p.emit("a5 7e 29 ff 00 c9 c8 00")
    p.branch("f0", "cases")
    p.label("fallback")
    p.emit("fa 68 28 a9 00 00 6b")
    p.label("cases")
    p.emit("a5 7c")
    for i, (profile, pose) in enumerate(PROFILE_POSES.items()):
        p.emit("c9 " + (profile & 65535).to_bytes(2, "little").hex(" "))
        p.branch("d0", f"next{i}")
        target = 0x6000 + pose * 14
        p.emit("a9 " + target.to_bytes(2, "little").hex(" "))
        p.emit("85 7c a9 f1 00 85 7e fa 68 28 a9 00 00 6b")
        p.label(f"next{i}")
    p.emit("fa 68 28 a9 00 00 6b")
    return p.finish()


def part_hook(secondary):
    p = Program()
    previous = "5c 00 07 f0" if secondary else "5c 00 05 f0"
    p.emit("08 48 da a6 36 bd 74 0b c9 10 00")
    p.branch("d0", "fallback")
    # Stock actions may use the same numeric part IDs. Only our private
    # graphics bank may dispatch through the replacement pointer tables.
    p.emit("a5 7e 29 ff 00 c9 f1 00")
    p.branch("f0", "shawn")
    p.label("fallback")
    p.emit("fa 68 28 " + previous)
    p.label("shawn")
    p.emit("fa 68")
    first = 1032 if secondary else 624
    p.emit("c9 " + first.to_bytes(2, "little").hex(" "))
    p.branch("90", "original")
    p.emit("c9 " + (first + 48).to_bytes(2, "little").hex(" "))
    p.branch("b0", "original")
    if secondary:
        # Returning to the new idle profile must consume the finisher marker.
        p.emit("c9 08 04")
        p.branch("f0", "clear")
        p.emit("c9 20 04")
        p.branch("d0", "lookup")
        p.label("clear")
        p.emit("48 da a6 36 9e ec 0b fa 68")
    p.label("lookup")
    p.emit("da 38 e9 " + first.to_bytes(2, "little").hex(" ") + " aa")
    p.emit("bf 00 " + ("1f" if secondary else "1e") + " f1 fa 28 85 80")
    p.emit("99 " + ("50" if secondary else "4e") + " 05 a9 f1 00 85 82")
    p.emit("99 " + ("52" if secondary else "50") + " 05")
    p.emit("5c 38 ed 80" if secondary else "c8 c8 5c e2 ec 80")
    p.label("original")
    p.emit("28 " + previous)
    return p.finish()


def make_patch(original, result):
    patch = bytearray(b"PATCH")
    for address in range(len(original), len(result), 65535):
        size = min(65535, len(result) - address)
        patch += (
            address.to_bytes(3, "big") + bytes(2) + size.to_bytes(2, "big") + b"\xff"
        )
    baseline = original + b"\xff" * (len(result) - len(original))
    i = 0
    while i < len(result):
        if baseline[i] == result[i]:
            i += 1
            continue
        start = i
        while i < len(result) and baseline[i] != result[i] and i - start < 65535:
            i += 1
        data = result[start:i]
        patch += start.to_bytes(3, "big") + len(data).to_bytes(2, "big") + data
    return bytes(patch + b"EOF")


def build(rom, reference, finisher_art, movement_art, back_art):
    base, _, finisher = build_finisher(rom, reference, finisher_art, step_back=4)
    r = bytearray(base)
    poses = install_poses(
        r,
        movement_art,
        profile_base=0x6000,
        descriptor_base=0x8000,
        tile_base=2048,
        primary_id=624,
        secondary_id=1032,
        upper_table=0x1E00,
        lower_table=0x1F00,
        sequence=False,
    )
    back_poses = install_poses(
        r,
        back_art,
        profile_base=0x6070,
        descriptor_base=0x9800,
        tile_base=3072,
        primary_id=648,
        secondary_id=1056,
        upper_table=0x1E18,
        lower_table=0x1F18,
        sequence=False,
    )
    for entry in back_poses:
        entry["pose"] += 8
    poses += back_poses
    # The first finisher draft's canvas registered soles eight pixels above
    # the stock idle ground line. Align all authored bodies to that native
    # line together, preserving native actor position, collision and shadow.
    for base, count in [(0x312000, 8), (0x316000, 16)]:
        for i in range(count):
            for field in [3, 7]:
                address = base + i * 14 + field
                r[address] = (r[address] + 8) & 255
    hooks = [
        (0xF0E8, 0x301200, bytes.fromhex("85 7c 86 7e"), profile_hook()),
        (0xECC1, 0x301800, bytes.fromhex("5c 00 05 f0"), part_hook(False)),
        (0xED19, 0x301A00, bytes.fromhex("5c 00 07 f0"), part_hook(True)),
    ]
    for entry, target, expected, code in hooks:
        if r[entry : entry + 4] != expected or len(code) > 0x500:
            raise ValueError("Unexpected hook bytes or oversized redirect")
        r[target : target + len(code)] = code
        r[entry : entry + 4] = bytes([0x5C, target & 255, target >> 8 & 255, 0xF0])
    r[0xFFDC:0xFFE0] = bytes.fromhex("ff ff 00 00")
    checksum = sum(r) & 65535
    r[0xFFDC:0xFFE0] = (checksum ^ 65535).to_bytes(2, "little") + checksum.to_bytes(
        2, "little"
    )
    patch = make_patch(rom, r)
    metadata = {
        "original_sha256": hashlib.sha256(rom).hexdigest(),
        "patched_sha256": hashlib.sha256(r).hexdigest(),
        "ips_sha256": hashlib.sha256(patch).hexdigest(),
        "movement_artwork_manifest_sha256": hashlib.sha256(
            (movement_art / "manifest.json").read_bytes()
        ).hexdigest(),
        "back_artwork_manifest_sha256": hashlib.sha256(
            (back_art / "manifest.json").read_bytes()
        ).hexdigest(),
        "authored_body_vertical_offset_pixels": 8,
        "movement_poses": poses,
        "native_idle_walk_sequence_range": ["C403A2", "C40671"],
        "native_profile_mapping": {f"{k:06X}": v for k, v in PROFILE_POSES.items()},
        "finisher": finisher,
        "experimental": True,
        "scope": "Shawn idle and walking profiles plus front-facing superkick; other actions still use stock artwork",
        "limitations": [
            "Idle variants 1 and 9 authored but unused by the stock idle profiles",
            "Walk pose transitions and likeness need visual review",
            "Full character animation replacement is unfinished",
        ],
    }
    return bytes(r), patch, metadata


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom", type=Path)
    ap.add_argument("reference", type=Path)
    ap.add_argument(
        "--finisher-art", type=Path, default=Path("assets/shawn-superkick-front-art")
    )
    ap.add_argument(
        "--movement-art", type=Path, default=Path("assets/shawn-movement-art")
    )
    ap.add_argument(
        "--back-art", type=Path, default=Path("assets/shawn-movement-back-art")
    )
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    rom, patch, metadata = build(
        args.rom.read_bytes(),
        args.reference,
        args.finisher_art,
        args.movement_art,
        args.back_art,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "shawn-redesign.sfc").write_bytes(rom)
    (args.output / "shawn-redesign.ips").write_bytes(patch)
    (args.output / "patch-report.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
