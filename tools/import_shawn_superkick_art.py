"""Convert a newly authored 4x2 sprite sheet into native indexed sprite assets.

This is format conversion for ROM insertion: foreground extraction, uniform
resampling, palette encoding and planted-foot registration. It does not create
movement by cutting or rotating any original game sprite pixels.
"""

import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image


def convert(sheet, cgram, output):
    source = Image.open(sheet).convert("RGBA")
    width, height = source.size
    colors = []
    for i in range(16):
        value = int.from_bytes(cgram[256 + i * 2 : 258 + i * 2], "little")
        colors.append(tuple((value >> shift & 31) * 255 // 31 for shift in [0, 5, 10]))
    cells = []
    for row in range(2):
        band = source.crop((0, row * height // 2, width, (row + 1) * height // 2))
        band_mask = band.getchannel("A").point(lambda a: 255 if a >= 200 else 0)
        xs = [
            x
            for x in range(width)
            if band_mask.crop((x, 0, x + 1, band.height)).getbbox()
        ]
        groups = []
        for x in xs:
            if not groups or x - groups[-1][-1] > 12:
                groups.append([])
            groups[-1].append(x)
        if len(groups) != 4:
            raise ValueError(
                ("Expected four separate authored sprites per row", row, len(groups))
            )
        for group in groups:
            # Generated sprites can cross nominal grid boundaries; use actual alpha silhouettes.
            cell = band.crop((group[0], 0, group[-1] + 1, band.height))
            mask = band_mask.crop((group[0], 0, group[-1] + 1, band.height))
            bbox = mask.getbbox()
            if not bbox:
                raise ValueError("Empty sprite cell")
            xs = sorted(
                {
                    x
                    for y in range(
                        bbox[3] - max(8, round((bbox[3] - bbox[1]) * 0.12)), bbox[3]
                    )
                    for x in range(bbox[0], bbox[2])
                    if mask.getpixel((x, y))
                }
            )
            first = []
            for x in xs:
                if first and x - first[-1] > 8:
                    break
                first.append(x)
            sole_y = max(
                y
                for y in range(
                    bbox[3] - max(8, round((bbox[3] - bbox[1]) * 0.12)), bbox[3]
                )
                for x in first
                if mask.getpixel((x, y))
            )
            anchor = ((first[0] + first[-1]) / 2, sole_y)
            cells.append((cell, mask, bbox, anchor))
    scale = 80 / (cells[0][2][3] - cells[0][2][1])
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    flat_palette = [v for color in colors for v in color] + [0] * 720
    for i, (cell, mask, bbox, anchor) in enumerate(cells):
        frame = Image.new("P", (96, 96), 0)
        frame.putpalette(flat_palette)
        for y in range(96):
            for x in range(96):
                sx = round(anchor[0] + (x - 44) / scale)
                sy = round(anchor[1] + (y - 89) / scale)
                if (
                    not 0 <= sx < cell.width
                    or not 0 <= sy < cell.height
                    or not mask.getpixel((sx, sy))
                ):
                    continue
                rgb = cell.getpixel((sx, sy))[:3]
                color = min(
                    range(1, 16),
                    key=lambda c: sum((rgb[k] - colors[c][k]) ** 2 for k in range(3)),
                )
                frame.putpixel((x, y), color)
        path = output / f"frame-{i:02d}.png"
        frame.save(path, transparency=0)
        rows.append(
            {
                "pose": i,
                "source_bounds": list(bbox),
                "support_boot_anchor": list(anchor),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest = {
        "source_sheet_sha256": hashlib.sha256(Path(sheet).read_bytes()).hexdigest(),
        "artwork_origin": "Reference-guided generated pixel-art sheet, converted into native indexed assets; not extracted game body pixels",
        "native_palette": colors,
        "alpha_threshold": 200,
        "uniform_scale": scale,
        "target_support_boot_anchor": [44, 89],
        "frames": rows,
        "motion_reference": "https://media1.tenor.com/m/ljOwV-Xx_QUAAAAd/shawn-michaels-sweet-chin-music.gif",
        "reference_observed_frames": list(range(24, 33)),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def load_pose(index, directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    path = directory / f"frame-{index:02d}.png"
    expected = manifest["frames"][index]["sha256"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("Authored artwork hash mismatch")
    image = Image.open(path)
    if image.mode != "P" or image.size != (96, 96) or image.getextrema()[1] > 15:
        raise ValueError("Expected 96x96 native indexed pose")
    if image.getpalette()[:48] != [
        c for color in manifest["native_palette"] for c in color
    ]:
        raise ValueError("Artwork palette mismatch")
    return image.copy()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sheet", type=Path)
    ap.add_argument("cgram", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    print(
        json.dumps(convert(args.sheet, args.cgram.read_bytes(), args.output), indent=2)
    )


if __name__ == "__main__":
    main()
