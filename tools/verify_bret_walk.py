"""Check paired walking captures and export an actual-game comparison GIF."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from extract_oam import assemble, objects


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
        "input": "Left held for 90 frames after cold-boot frame 2940",
        "outside_bret_screen_changes": 0,
        "outside_bret_vram_changes": 0,
        "other_palette_changes": 0,
        "object_positions_identical": True,
        "scope": "Observed upright left walk only; other animations unverified",
        "frames": report,
    }


def render(before, after, report, output):
    frames = []
    for record in report["frames"][::3]:
        n = record["frame"]
        name = f"frame-{n:06d}.png"
        bounds = record["bret_bounds"]
        canvas = Image.new("RGB", (1024, 900), "#202020")
        draw = ImageDraw.Draw(canvas)
        for x, root, title in [
            (0, before, "ORIGINAL GAME"),
            (512, after, "EDITED WALKING TEST"),
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
