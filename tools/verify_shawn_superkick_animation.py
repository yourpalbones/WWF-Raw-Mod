"""Verify all drawn poses against settled emulator OAM/VRAM captures.

This catches lost pixels, incorrect tiles, and frame/anchor misalignment rather
than checking only a builder's own output. Inputs are local emulator snapshots.
"""

import argparse
import json
from pathlib import Path
from PIL import Image
from draw_shawn_superkick import pose
from import_shawn_superkick_art import load_pose
from extract_oam import objects


def verify(root, report, art_dir=None):
    rows = []
    for i, entry in enumerate(report["poses"]):
        frame = 12 + i * 6
        prefix = root / f"frame-{frame:06d}"

        def get(name):
            return Path(str(prefix) + "-" + name + ".bin").read_bytes()

        cg = get("cgram")
        records = objects(get("vram"), get("oam"), cg, get("registers")[0x2101])
        actual = Image.new("RGBA", (256, 224))
        actor_records = [
            (rec, image)
            for rec, image in records
            if rec["palette"] == 0 and rec["tile"] < 64 and rec["y"] < 224
        ]
        if len(actor_records) != entry["objects"]:
            raise ValueError(f"Pose {i}: unexpected actor object count")
        for rec, image in reversed(actor_records):
            actual.alpha_composite(image, (rec["x"], rec["y"]))
        expected = Image.new("RGBA", (256, 224))
        source = load_pose(i, art_dir) if art_dir else pose(i)
        for y in range(96):
            for x in range(96):
                c = source.getpixel((x, y))
                if c:
                    value = int.from_bytes(cg[256 + c * 2 : 258 + c * 2], "little")
                    rgb = tuple(
                        (value >> shift & 31) * 255 // 31 for shift in [0, 5, 10]
                    )
                    expected.putpixel(
                        (
                            (181 - x) if actor_records[0][0]["hflip"] else (64 + x),
                            64 + y,
                        ),
                        rgb + (255,),
                    )
        actual_bounds = actual.getbbox()
        expected_bounds = expected.getbbox()
        if (
            actual.crop(actual_bounds).tobytes()
            != expected.crop(expected_bounds).tobytes()
            or actual.crop(actual_bounds).size != expected.crop(expected_bounds).size
        ):
            raise ValueError(
                f"Pose {i}, frame {frame}: assembled artwork does not match drawn source"
            )
        rows.append(
            {
                "pose": i,
                "frame": frame,
                "pixels_match_drawn_source": True,
                "screen_translation": [
                    actual_bounds[0] - expected_bounds[0],
                    actual_bounds[1] - expected_bounds[1],
                ],
            }
        )
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("capture", type=Path)
    ap.add_argument("report", type=Path)
    ap.add_argument("--art-dir", type=Path)
    args = ap.parse_args()
    print(
        json.dumps(
            verify(args.capture, json.loads(args.report.read_text()), args.art_dir),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
