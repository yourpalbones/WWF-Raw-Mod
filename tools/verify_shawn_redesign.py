"""Verify replacement artwork against actual emulator captures and stock controls."""

import argparse
import hashlib
import json
from pathlib import Path

from extract_oam import objects, assemble
from import_shawn_superkick_art import load_pose
from verify_shawn_superkick_animation import verify, verify_frame


def word(data, address):
    return int.from_bytes(data[address : address + 2], "little")


def memory(root, frame, kind="wram"):
    return (root / f"frame-{frame:06d}-{kind}.bin").read_bytes()


def actor_bounds(root, frame):
    records = objects(
        memory(root, frame, "vram"),
        memory(root, frame, "oam"),
        memory(root, frame, "cgram"),
        memory(root, frame, "registers")[0x2101],
    )
    ids = [
        i
        for i, (r, image) in enumerate(records)
        if r["palette"] == 0 and r["tile"] < 64 and r["y"] < 224 and image.getbbox()
    ]
    return assemble(records, ids)[1]


def verify_movement(root, stock, report, front_art, back_art):
    rendered = []
    native_profiles = set()
    for event in map(json.loads, (stock / "parts.jsonl").read_text().splitlines()):
        if event["actor_slot"] == 0 and not event["secondary"]:
            native_profiles.add(f"{event['profile_pointer']:06X}")
    entries = {e["primary_id"]: e for e in report["movement_poses"]}
    for event in map(json.loads, (root / "parts.jsonl").read_text().splitlines()):
        if event["actor_slot"] or event["secondary"] or event["part_id"] not in entries:
            continue
        entry = entries[event["part_id"]]
        i = entry["pose"]
        frame = event["frame"] + 2
        source = load_pose(i if i < 8 else i - 8, front_art if i < 8 else back_art)
        translation = verify_frame(root / f"frame-{frame:06d}", entry, source)
        records = objects(
            memory(root, frame, "vram"),
            memory(root, frame, "oam"),
            memory(root, frame, "cgram"),
            memory(root, frame, "registers")[0x2101],
        )
        flip = next(
            r["hflip"]
            for r, _ in records
            if r["palette"] == 0 and r["tile"] < 64 and r["y"] < 224
        )
        rendered.append(
            {
                "pose": i,
                "frame": frame,
                "horizontal_flip": flip,
                "source_pixels_match": True,
                "screen_translation": translation,
            }
        )
    run = json.loads((root / "run.json").read_text())
    stock_run = json.loads((stock / "run.json").read_text())
    if run["frames"] != stock_run["frames"] or run["presses"] != stock_run["presses"]:
        raise ValueError("Movement control recipes differ")
    end = run["frames"]
    addresses = [0x5F0, 0x5F2, 0x600, 0x602, 0x6B4, 0x6B6, 0xA78, 0xA7A]
    a, b = memory(root, end), memory(stock, end)
    if any(word(a, x) != word(b, x) for x in addresses):
        raise ValueError("Movement control endpoint differs")
    updates = []
    opponent_tile_differences = []
    for frame in range(1, end + 1):
        if (
            memory(root, frame, "vram")[4096:6144]
            != memory(stock, frame, "vram")[4096:6144]
        ):
            opponent_tile_differences.append(frame)
        a, b = memory(root, frame), memory(stock, frame)
        if any(word(a, x) != word(b, x) for x in addresses):
            updates.append(frame)
    for frame in [1, 50, 100, end]:
        if frame in opponent_tile_differences:
            raise ValueError(
                "Opponent graphics differ at a representative settled sample"
            )
    return {
        "rendered_pose_checks": rendered,
        "native_profiles_observed": sorted(native_profiles),
        "movement_health_and_action_endpoint_matches_original": True,
        "opponent_tile_buffer_matches_original_at_frames": [1, 50, 100, end],
        "opponent_tile_buffer_differences_at_frames": opponent_tile_differences,
        "gameplay_snapshot_differences_at_frames": updates,
        "controller_inputs": run["presses"],
        "frames": end,
    }


def verify_all(root, build, original, front_art, back_art, finisher_art):
    report = json.loads((build / "patch-report.json").read_text())
    for directory, expected in [
        (front_art, report["movement_artwork_manifest_sha256"]),
        (back_art, report["back_artwork_manifest_sha256"]),
        (finisher_art, report["finisher"]["artwork_manifest_sha256"]),
    ]:
        if (
            hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest()
            != expected
        ):
            raise ValueError("Artwork manifest differs from the tested build")
    original_bytes = original.read_bytes()
    patched = (build / "shawn-redesign.sfc").read_bytes()
    ips = (build / "shawn-redesign.ips").read_bytes()
    for data, key in [
        (original_bytes, "original_sha256"),
        (patched, "patched_sha256"),
        (ips, "ips_sha256"),
    ]:
        if hashlib.sha256(data).hexdigest() != report[key]:
            raise ValueError("Build hash mismatch")
    result = bytearray(original_bytes)
    i = 5
    if ips[:5] != b"PATCH":
        raise ValueError("Invalid IPS header")
    while ips[i : i + 3] != b"EOF":
        address = int.from_bytes(ips[i : i + 3], "big")
        size = int.from_bytes(ips[i + 3 : i + 5], "big")
        i += 5
        if size:
            data = ips[i : i + size]
            i += size
        else:
            size = int.from_bytes(ips[i : i + 2], "big")
            data = ips[i + 2 : i + 3] * size
            i += 3
        if len(result) < address + size:
            result.extend(bytes(address + size - len(result)))
        result[address : address + size] = data
    if bytes(result) != patched:
        raise ValueError("IPS round trip differs")
    if (
        sum(patched) & 65535 != word(patched, 0xFFDE)
        or word(patched, 0xFFDC) ^ word(patched, 0xFFDE) != 65535
    ):
        raise ValueError("Invalid SNES checksum")
    movement = {}
    for name, stock in [
        ("walk", "walk-stock"),
        ("walk-left-facing", "walk-left-stock"),
        ("back-walk", "back-stock"),
        ("mirror-walk", "mirror-stock"),
    ]:
        movement[name] = verify_movement(
            root / name, root / stock, report, front_art, back_art
        )
    seen = {
        (e["pose"], e["horizontal_flip"])
        for c in movement.values()
        for e in c["rendered_pose_checks"]
    }
    required = {
        (i, flip)
        for i in [0, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]
        for flip in [False, True]
    }
    if not required <= seen:
        raise ValueError(f"Missing artwork orientations: {sorted(required - seen)}")
    ground_checks = []
    for name, stock, frame in [
        ("walk-left-facing", "walk-left-stock", 90),
        ("back-walk", "back-stock", 140),
    ]:
        actual = actor_bounds(root / name, frame)[3]
        expected = actor_bounds(root / stock, frame)[3]
        if actual != expected:
            raise ValueError("Standing soles do not align with the native ground line")
        ground_checks.append(
            {
                "case": name,
                "frame": frame,
                "sole_screen_y_exclusive": actual,
                "matches_stock_ground_line": True,
            }
        )
    finisher = {}
    for name, start, end in [("left", 222, 78), ("right", 238, 94)]:
        poses = verify(root / name, report["finisher"], finisher_art)
        initial, back, forward, final = [
            memory(root / name, f) for f in [9, 12, 18, 180]
        ]
        distance = 4 if name == "left" else -4
        if word(back, 0x5F0) - word(initial, 0x5F0) != distance or word(
            forward, 0x5F0
        ) != word(initial, 0x5F0):
            raise ValueError("Finisher preparation step differs")
        if (
            word(initial, 0xA7A) != start
            or word(final, 0xA7A) != end
            or word(final, 0x6B4)
            or word(final, 0xBEC)
        ):
            raise ValueError("Finisher contact or idle recovery failed")
        # The native facing selects either frontal or rear idle on recovery.
        idle_pose = None
        for candidate, directory in [(0, front_art), (8, back_art)]:
            try:
                verify_frame(
                    root / name / "frame-000060",
                    report["movement_poses"][candidate],
                    load_pose(0, directory),
                )
                idle_pose = candidate
                break
            except ValueError:
                continue
        if idle_pose is None:
            raise ValueError("Finisher recovery did not render either authored idle")
        finisher[name] = {
            "pose_checks": poses,
            "opponent_health": [start, end],
            "step_back_pixels": 4,
            "returns_to_new_idle_and_clears_marker": True,
            "recovery_idle_pose": idle_pose,
        }
    for name, frame in [("A", 180), ("UT", 600)]:
        a, b = memory(root / name, frame), memory(root / (name + "-stock"), frame)
        if any(
            word(a, x) != word(b, x) for x in [0x5F0, 0x600, 0x6B4, 0x6B6, 0xA78, 0xA7A]
        ):
            raise ValueError("Stock move control endpoint differs")
    for frame in [18, 24, 30]:
        if (
            memory(root / "A", frame, "vram")[:4096]
            != memory(root / "A-stock", frame, "vram")[:4096]
        ):
            raise ValueError("Ordinary A kick art differs")
    for frame in range(6, 601, 6):
        if (
            memory(root / "UT", frame, "vram")[:4096]
            != memory(root / "UT-stock", frame, "vram")[:4096]
        ):
            raise ValueError("Undertaker graphics differ")
    return {
        "patched_rom_sha256": report["patched_sha256"],
        "movement": movement,
        "finisher": finisher,
        "standing_ground_alignment_checks": ground_checks,
        "distinct_movement_pose_orientations_verified": len(seen),
        "normal_A_kick_and_Undertaker_finisher_endpoints_match_original": True,
        "normal_A_actor_tiles_match_original_at_frames": [18, 24, 30],
        "Undertaker_actor_tiles_match_original_all_100_samples": True,
        "ips_round_trip_exact": True,
        "snes_checksum_valid": True,
        "setup": "Original-ROM controller-generated save states; no emulator RAM writes",
        "limitations": [
            "Standing/walking and superkick only; other Shawn actions retain stock art",
            "Movement update timing differs at a few capture frames; endpoints match",
            "Loaded-state testing; fresh-boot finisher setup remains unresolved",
            "Full match, interruptions, player 2, gear combinations and all diagonal controls unverified",
            "Generated indexed artwork and transitions need visual review",
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("captures", type=Path)
    ap.add_argument("build", type=Path)
    ap.add_argument("original_rom", type=Path)
    ap.add_argument("--front-art", type=Path, default=Path("assets/shawn-movement-art"))
    ap.add_argument(
        "--back-art", type=Path, default=Path("assets/shawn-movement-back-art")
    )
    ap.add_argument(
        "--finisher-art", type=Path, default=Path("assets/shawn-superkick-front-art")
    )
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    report = verify_all(
        args.captures,
        args.build,
        args.original_rom,
        args.front_art,
        args.back_art,
        args.finisher_art,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print("Verified movement artwork, finisher, stock controls and patch round trip")


if __name__ == "__main__":
    main()
