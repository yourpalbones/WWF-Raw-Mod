"""Read-only SNES ROM triage. Does not establish compression from entropy."""

import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw


def tile(data, offset, bpp):
    pixels = []
    for y in range(8):
        for x in range(8):
            value = 0
            for plane in range(bpp):
                address = offset + (plane // 2) * 16 + y * 2 + plane % 2
                value |= ((data[address] >> (7 - x)) & 1) << plane
            pixels.append(value)
    return pixels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    data = args.rom.read_bytes()
    args.output.mkdir(parents=True, exist_ok=True)
    if len(data) % 1024 == 512:
        data = data[512:]
    stats = []
    for start in range(0, len(data), 65536):
        block = data[start : start + 65536]
        counts = collections.Counter(block)
        entropy = -sum(
            (n / len(block)) * math.log2(n / len(block)) for n in counts.values()
        )
        stats.append({"offset": f"0x{start:06X}", "entropy": round(entropy, 4)})
    result = {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "banks": stats,
    }
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    # Four evenly spaced strips per bank. Indexed colors show pixel structure,
    # not the game's actual palettes; this is only a raw planar-format probe.
    for bpp in (2, 4):
        width = 6 * 270
        height = 8 * 160
        sheet = Image.new("RGB", (width, height), "#202020")
        draw = ImageDraw.Draw(sheet)
        for bank in range((len(data) + 65535) // 65536):
            cx = (bank % 6) * 270
            cy = (bank // 6) * 160
            draw.text(
                (cx + 4, cy + 2), f"{bank * 65536:06X}   SNES {bpp}bpp", fill="white"
            )
            for sample in range(4):
                base = bank * 65536 + sample * 16384
                panel = Image.new("RGB", (64, 128))
                for t in range(128):
                    off = base + t * 8 * bpp
                    if off + 8 * bpp > len(data):
                        break
                    for k, v in enumerate(tile(data, off, bpp)):
                        shade = round(v * 255 / ((1 << bpp) - 1))
                        panel.putpixel(
                            ((t % 8) * 8 + k % 8, (t // 8) * 8 + k // 8),
                            (shade, shade, shade),
                        )
                sheet.paste(panel, (cx + sample * 66, cy + 22))
        sheet.save(args.output / f"raw-{bpp}bpp.png")
    print(
        json.dumps(
            {
                "size": result["size"],
                "sha256": result["sha256"],
                "outputs": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
