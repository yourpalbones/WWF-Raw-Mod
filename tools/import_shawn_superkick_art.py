"""Convert a newly authored 4x2 sprite sheet into native indexed sprite assets.

This is format conversion for ROM insertion: foreground extraction, uniform
resampling, palette encoding and planted-foot registration. It does not create
movement by cutting or rotating any original game sprite pixels.
"""

import argparse
import hashlib
import json
from pathlib import Path
from collections import deque
from PIL import Image


def connected_regions(band, mask):
    width, height = mask.size
    foreground = bytearray(mask.tobytes())
    components = []
    for seed in range(len(foreground)):
        if not foreground[seed]:
            continue
        foreground[seed] = 0
        queue = deque([seed])
        pixels = []
        while queue:
            k = queue.popleft()
            pixels.append(k)
            x = k % width
            y = k // width
            for yy in range(max(0, y - 1), min(height, y + 2)):
                for xx in range(max(0, x - 1), min(width, x + 2)):
                    n = yy * width + xx
                    if foreground[n]:
                        foreground[n] = 0
                        queue.append(n)
        if len(pixels) > 1000:
            components.append(pixels)
    if len(components) != 4:
        raise ValueError(("Expected four complete foreground bodies", len(components)))
    regions = []
    for pixels in components:
        xs = [k % width for k in pixels]
        ys = [k // width for k in pixels]
        bbox = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
        own = Image.new("L", (bbox[2] - bbox[0], height), 0)
        for k in pixels:
            own.putpixel((k % width - bbox[0], k // width), 255)
        regions.append((bbox[0], band.crop((bbox[0], 0, bbox[2], height)), own))
    return [(cell, own) for _, cell, own in sorted(regions, key=lambda r: r[0])]


def convert(
    sheet,
    cgram,
    output,
    motion_reference=None,
    reference_frames=None,
    anchor_mode="foot",
    native_height=80,
    normalize_rows=False,
):
    if anchor_mode not in ("foot", "waist"):
        raise ValueError("Unknown artwork registration mode")
    if not 48 <= native_height <= 88:
        raise ValueError("Native artwork height must be between 48 and 88 pixels")
    target_x = 59 if anchor_mode == "waist" else 44
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
            # Chin-high boots can overlap the next figure's x range without touching it.
            regions = connected_regions(band, band_mask)
        else:
            regions = [
                (
                    band.crop((g[0], 0, g[-1] + 1, band.height)),
                    band_mask.crop((g[0], 0, g[-1] + 1, band.height)),
                )
                for g in groups
            ]
        for cell, mask in regions:
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
            if anchor_mode == "waist":
                # Red tights mark the waist on this authored sheet. Register the
                # torso rather than whichever boot happens to be planted.
                red = [
                    (x, y)
                    for y in range(bbox[1], bbox[3])
                    for x in range(bbox[0], bbox[2])
                    if mask.getpixel((x, y))
                    and cell.getpixel((x, y))[0] > 50
                    and cell.getpixel((x, y))[0] > 1.7 * cell.getpixel((x, y))[1]
                    and cell.getpixel((x, y))[0] > 1.7 * cell.getpixel((x, y))[2]
                ]
                if not red:
                    raise ValueError("Waist registration needs visible red tights")
                top = min(y for x, y in red)
                waist = [
                    x
                    for x, y in red
                    if y < top + max(3, round((bbox[3] - bbox[1]) * 0.03))
                ]
                anchor = (sum(waist) / len(waist), bbox[3] - 1)
            cells.append((cell, mask, bbox, anchor))
    scale = native_height / (cells[0][2][3] - cells[0][2][1])
    row_scales = [scale, scale]
    if normalize_rows:
        row_scales[1] = native_height / (cells[4][2][3] - cells[4][2][1])
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    flat_palette = [v for color in colors for v in color] + [0] * 720
    for i, (cell, mask, bbox, anchor) in enumerate(cells):
        frame_scale = row_scales[i // 4]
        if any(
            not -0.5 <= coordinate < 96.5
            for coordinate in (
                target_x + (bbox[0] - anchor[0]) * frame_scale,
                target_x + (bbox[2] - anchor[0]) * frame_scale,
                89 + (bbox[1] - anchor[1]) * frame_scale,
                89 + (bbox[3] - anchor[1]) * frame_scale,
            )
        ):
            raise ValueError(
                "Authored silhouette would be clipped by the native canvas"
            )
        frame = Image.new("P", (96, 96), 0)
        frame.putpalette(flat_palette)
        for y in range(96):
            for x in range(96):
                sx = round(anchor[0] + (x - target_x) / frame_scale)
                sy = round(anchor[1] + (y - 89) / frame_scale)
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
                "source_registration_anchor": list(anchor),
                "source_scale": frame_scale,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest = {
        "source_sheet_sha256": hashlib.sha256(Path(sheet).read_bytes()).hexdigest(),
        "artwork_origin": "Reference-guided generated pixel-art sheet, converted into native indexed assets; not extracted game body pixels",
        "native_palette": colors,
        "alpha_threshold": 200,
        "uniform_scale": scale if not normalize_rows else None,
        "row_scales": row_scales,
        "native_reference_height": native_height,
        "registration_mode": anchor_mode,
        "target_registration_anchor": [target_x, 89],
        "target_support_boot_anchor": [44, 89] if anchor_mode == "foot" else None,
        "frames": rows,
        "motion_reference": motion_reference
        or (
            None
            if anchor_mode == "waist"
            else "https://media1.tenor.com/m/ljOwV-Xx_QUAAAAd/shawn-michaels-sweet-chin-music.gif"
        ),
        "reference_observed_frames": reference_frames
        if reference_frames is not None
        else ([] if anchor_mode == "waist" else list(range(24, 33))),
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
    ap.add_argument("--motion-reference")
    ap.add_argument("--native-height", type=int, default=80)
    ap.add_argument(
        "--normalize-rows",
        action="store_true",
        help="Correct a generated sheet with different scales between rows",
    )
    ap.add_argument("--anchor-mode", choices=("foot", "waist"), default="foot")
    ap.add_argument(
        "--reference-frames", help="Comma-separated inspected frame numbers"
    )
    args = ap.parse_args()
    print(
        json.dumps(
            convert(
                args.sheet,
                args.cgram.read_bytes(),
                args.output,
                args.motion_reference,
                [int(n) for n in args.reference_frames.split(",")]
                if args.reference_frames
                else None,
                args.anchor_mode,
                args.native_height,
                args.normalize_rows,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
