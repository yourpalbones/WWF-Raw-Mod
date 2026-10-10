"""Check paired walking captures and export an actual-game comparison GIF."""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from extract_oam import assemble, objects
from inspect_rom import tile


def indexed_pose(root, name):
    def read(kind):
        return (root / (name + "-" + kind + ".bin")).read_bytes()

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
                for k, color in enumerate(tile(vram, n * 32, 4)):
                    if not color:
                        continue
                    dx, dy = tx * 8 + k % 8, ty * 8 + k // 8
                    x = r["x"] + (size - 1 - dx if r["hflip"] else dx) - bounds[0]
                    y = r["y"] + (size - 1 - dy if r["vflip"] else dy) - bounds[1]
                    atlas[x, y] = color
    return hashlib.sha256(body.tobytes()).hexdigest(), atlas


def verify_detail_anchors(before, after):
    path = (
        Path(__file__).resolve().parents[1] / "data" / "bret-left-walk-landmarks.json"
    )
    annotations = json.loads(path.read_text())["poses"]
    by_hash = {a["sprite_sha256"]: a for a in annotations}
    counts = {str(a["sample_frame"]): 0 for a in annotations}
    pixels_checked = 0
    for png in sorted(before.glob("frame-*.png")):
        digest, original = indexed_pose(before, png.stem)
        if digest not in by_hash:
            raise ValueError("Unannotated walking pose: " + png.stem)
        anno = by_hash[digest]
        _, edited = indexed_pose(after, png.stem)
        desired = {}
        for (x, y), color in original.items():
            if color not in (7, 9, 10, 11, 12, 15):
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
        for dx, dy, color in [(0, -1, 4), (-1, 0, 8), (0, 0, 4), (1, 0, 8), (0, 1, 8)]:
            position = cx + dx, cy + dy
            if original.get(position) not in (4, 5):
                raise ValueError("Chest landmark outside the original singlet")
            desired[position] = color
        for position, color in desired.items():
            if edited.get(position) != color:
                raise ValueError(
                    f"Detail does not follow authored pose: {png.stem} {position}"
                )
        counts[str(anno["sample_frame"])] += 1
        pixels_checked += len(desired)
    return {
        "annotated_poses": len(counts),
        "frames_per_pose": counts,
        "detail_pixel_checks": pixels_checked,
        "scope": "Matches hand-authored coordinates for these seven poses; anatomy still subject to visual review",
    }


def verify(before, after):
    original = sorted(before.glob("frame-*.png"))
    if len(original) != 90 or [p.name for p in original] != [
        p.name for p in sorted(after.glob("frame-*.png"))
    ]:
        raise ValueError("Expected 90 paired walking frames")
    report = []
    for png in original:
        name = png.stem

        def read(root, kind):
            return (root / (name + "-" + kind + ".bin")).read_bytes()

        v0, v1 = read(before, "vram"), read(after, "vram")
        o0, o1 = read(before, "oam"), read(after, "oam")
        c0, c1 = read(before, "cgram"), read(after, "cgram")
        if len(v0) != 65536 or len(v1) != 65536 or v0[0x800:] != v1[0x800:]:
            raise ValueError("Unexpected VRAM changes outside Bret: " + name)
        if len(o0) != 544 or o0 != o1:
            raise ValueError("Object positions or attributes changed: " + name)
        if (
            len(c0) != 512
            or len(c1) != 512
            or any(
                a != b for i, (a, b) in enumerate(zip(c0, c1)) if i not in (268, 269)
            )
        ):
            raise ValueError("Unexpected palette changes: " + name)
        records = objects(v0, o0, c0, read(before, "registers")[0x2101])
        ids = [
            i
            for i, (r, im) in enumerate(records)
            if r["palette"] == 0
            and 0 <= r["y"] < 190
            and -20 <= r["x"] < 256
            and im.getbbox()
        ]
        body, bounds = assemble(records, ids)
        mask = Image.new("L", (256, 256))
        mask.paste(body.getchannel("A"), bounds[:2])
        a = Image.open(png).convert("RGB")
        b = Image.open(after / png.name).convert("RGB")
        if a.size != (256, 224) or b.size != a.size:
            raise ValueError("Unexpected screenshot dimensions")
        differences = [
            (x, y)
            for y in range(224)
            for x in range(256)
            if a.getpixel((x, y)) != b.getpixel((x, y))
        ]
        if not differences or any(mask.getpixel((x, y)) == 0 for x, y in differences):
            raise ValueError("No gear changes, or changes outside Bret: " + name)
        report.append(
            {
                "frame": int(name.split("-")[1]),
                "changed_pixels": len(differences),
                "outside_bret": 0,
                "bret_bounds": list(bounds),
            }
        )
    return {
        "paired_frames": len(report),
        "authored_detail_anchors": verify_detail_anchors(before, after),
        "input": "Left held for 90 frames after cold-boot frame 2940",
        "outside_bret_screen_changes": 0,
        "outside_bret_vram_changes": 0,
        "other_palette_changes": 0,
        "object_positions_identical": True,
        "scope": "Observed upright left walk only; other animations unverified",
        "frames": report,
    }


def render(
    before, after, report, output, titles=("ORIGINAL GAME", "EDITED WALKING TEST")
):
    frames = []
    for record in report["frames"][::3]:
        n = record["frame"]
        name = f"frame-{n:06d}.png"
        bounds = record["bret_bounds"]
        canvas = Image.new("RGB", (1024, 900), "#202020")
        draw = ImageDraw.Draw(canvas)
        for x, root, title in [
            (0, before, titles[0]),
            (512, after, titles[1]),
        ]:
            image = Image.open(root / name).convert("RGB")
            draw.text((x + 12, 8), title, fill="white")
            canvas.paste(image.resize((512, 448), Image.Resampling.NEAREST), (x, 28))
            crop = image.crop(
                (bounds[0] - 2, bounds[1] - 2, bounds[2] + 2, bounds[3] + 2)
            )
            canvas.paste(
                crop.resize(
                    (crop.width * 4, crop.height * 4), Image.Resampling.NEAREST
                ),
                (x + 24, 504),
            )
        draw.text(
            (210, 520),
            f"Actual game capture\nFrame {n}/90\nLeft held\n\nWalking test only",
            fill="white",
        )
        draw.text(
            (720, 520),
            "Black gear\nChest mark\nElbow pad\nWrist tape\n\nOther animations\nremain unverified",
            fill="white",
        )
        frames.append(canvas)
    durations = [50] * len(frames)
    durations[0] = durations[-1] = 300
    frames[0].save(
        output / "walking-comparison.gif",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
        disposal=2,
    )
    sheet = Image.new("RGB", (1024, 720), "#202020")
    draw = ImageDraw.Draw(sheet)
    for j, record in enumerate(report["frames"][::15]):
        image = Image.open(after / f"frame-{record['frame']:06d}.png").convert("RGB")
        x, y = (j % 3) * 340, (j // 3) * 360
        bounds = record["bret_bounds"]
        crop = image.crop((bounds[0] - 2, bounds[1] - 2, bounds[2] + 2, bounds[3] + 2))
        sheet.paste(
            crop.resize((crop.width * 4, crop.height * 4), Image.Resampling.NEAREST),
            (x, y + 16),
        )
        draw.text((x, y), "Game frame " + str(record["frame"]), fill="white")
    sheet.save(output / "walking-poses.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.before, args.after)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "walk-verification.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    render(args.before, args.after, report, args.output)
    print("Verified", report["paired_frames"], "paired frames; no changes outside Bret")


if __name__ == "__main__":
    main()
