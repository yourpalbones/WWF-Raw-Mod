"""Reconstruct SNES objects from captured VRAM, OAM and CGRAM.

This assembles tiles using actual game-provided positions, sizes, flips and
palettes. It does not crop a game screenshot. Background priority, windows,
color math and scanline sprite limits are outside this focused extractor.
"""

import argparse
import json
from pathlib import Path
from PIL import Image
from inspect_rom import tile

SIZES = [(8, 16), (8, 32), (8, 64), (16, 32), (16, 64), (32, 64)]


def objects(vram, oam, cgram, obsel):
    if len(vram) != 65536 or len(oam) != 544 or len(cgram) != 512:
        raise ValueError("Expected 64 KiB VRAM, 544-byte OAM and 512-byte CGRAM")
    size_mode = obsel >> 5
    if size_mode >= 6:
        raise ValueError("Rectangular object-size modes are not implemented")
    palettes = [int.from_bytes(cgram[i : i + 2], "little") for i in range(0, 512, 2)]
    base = (obsel & 3) << 14
    name_select = ((obsel >> 3) & 3) << 13
    result = []
    for i in range(128):
        x, y, number, attr = oam[i * 4 : i * 4 + 4]
        high = (oam[512 + i // 4] >> (2 * (i % 4))) & 3
        if high & 1:
            x -= 256
        size = SIZES[size_mode][bool(high & 2)]
        image = Image.new("RGBA", (size, size))
        for ty in range(size // 8):
            for tx in range(size // 8):
                # OBJ tile columns wrap within 16-column rows.
                n = ((number & 0xF0) + ty * 16 + ((number + tx) & 15)) & 255
                address = (
                    base + ((name_select + 8192) if attr & 1 else 0) + n * 32
                ) & 65535
                for k, value in enumerate(tile(vram, address, 4)):
                    if not value:
                        continue
                    color = palettes[128 + ((attr >> 1) & 7) * 16 + value]
                    rgb = tuple(
                        ((color >> shift) & 31) * 255 // 31 for shift in (0, 5, 10)
                    )
                    image.putpixel((tx * 8 + k % 8, ty * 8 + k // 8), rgb + (255,))
        if attr & 0x40:
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if attr & 0x80:
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        result.append(
            (
                {
                    "index": i,
                    "x": x,
                    "y": y,
                    "tile": number + (attr & 1) * 256,
                    "size": size,
                    "palette": (attr >> 1) & 7,
                    "hflip": bool(attr & 0x40),
                    "vflip": bool(attr & 0x80),
                },
                image,
            )
        )
    return result


def assemble(records, indices):
    canvas = Image.new("RGBA", (256, 256))
    # Lower OAM indices have priority among objects of the same level.
    for index in reversed(list(indices)):
        record, image = records[index]
        for y in (record["y"], record["y"] - 256):
            canvas.alpha_composite(image, (record["x"], y))
    bounds = canvas.getbbox()
    if bounds is None:
        raise ValueError("Selected objects contain no visible pixels")
    return canvas.crop(bounds), bounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "snapshot", type=Path, help="Prefix of captured frame files, e.g. frame-000240"
    )
    parser.add_argument("--objects", required=True, help="Inclusive range, e.g. 38:54")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def paths(name):
        return Path(str(args.snapshot) + "-" + name + ".bin")

    regs = paths("registers").read_bytes()
    records = objects(
        paths("vram").read_bytes(),
        paths("oam").read_bytes(),
        paths("cgram").read_bytes(),
        regs[0x2101],
    )
    start, end = map(int, args.objects.split(":"))
    if not 0 <= start <= end < 128:
        raise ValueError("Object indices must be between 0 and 127")
    indices = range(start, end + 1)
    image, bounds = assemble(records, indices)
    args.output.mkdir(parents=True, exist_ok=True)
    image.save(args.output / "sprite-native.png")
    # Preview uses a flat backdrop; the native output preserves transparency.
    preview = Image.new("RGB", image.size, "#303030")
    preview.paste(image, mask=image.getchannel("A"))
    preview.resize((image.width * 6, image.height * 6), Image.Resampling.NEAREST).save(
        args.output / "sprite-preview.png"
    )
    metadata = {
        "snapshot": str(args.snapshot),
        "obsel": regs[0x2101],
        "bounds": bounds,
        "width": image.width,
        "height": image.height,
        "objects": [records[i][0] for i in indices],
    }
    (args.output / "assembly.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({k: v for k, v in metadata.items() if k != "objects"}, indent=2))


if __name__ == "__main__":
    main()
