"""Verify paired cold-boot captures against the black-gear ROM edit."""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from build_bret_gear import ASSETS, PALETTE, build
from decode_sprite_tile import decode_sprite_tile


def verify(rom, before, after):
    edited_rom, patch, tiles, metadata = build(rom)
    prefix = "frame-002940"

    def read(root, suffix):
        return (root / (prefix + suffix)).read_bytes()

    original_vram = read(before, "-vram.bin")
    edited_vram = read(after, "-vram.bin")
    if len(original_vram) != 65536 or len(edited_vram) != 65536:
        raise ValueError("Expected complete VRAM captures")
    for slot, offset, compressed in ASSETS:
        original = (
            decode_sprite_tile(rom, offset)[0]
            if compressed
            else rom[offset : offset + 32]
        )
        if original_vram[slot * 32 : (slot + 1) * 32] != original:
            raise ValueError(f"Original tile {slot} does not match the ROM")
    for slot, data in tiles.items():
        if edited_vram[slot * 32 : (slot + 1) * 32] != data:
            raise ValueError(f"Expected edited tile {slot} was not loaded")
    allowed = {i for slot in tiles for i in range(slot * 32, (slot + 1) * 32)}
    vram_changes = [
        i for i, (a, b) in enumerate(zip(original_vram, edited_vram)) if a != b
    ]
    if not vram_changes or any(i not in allowed for i in vram_changes):
        raise ValueError("Unexpected VRAM changes")
    if read(before, "-oam.bin") != read(after, "-oam.bin"):
        raise ValueError("Object positions or attributes changed")
    c0 = read(before, "-cgram.bin")
    c1 = read(after, "-cgram.bin")
    if len(c0) != 512 or len(c1) != 512:
        raise ValueError("Expected complete CGRAM captures")
    if c0[256:288] != rom[PALETTE : PALETTE + 32]:
        raise ValueError("Original Bret palette does not match the ROM")
    if c1[268:270] != edited_rom[PALETTE + 12 : PALETTE + 14]:
        raise ValueError("Edited boot color not loaded")
    if any(i not in (268, 269) for i, (a, b) in enumerate(zip(c0, c1)) if a != b):
        raise ValueError("Unexpected palette changes")
    a = Image.open(before / (prefix + ".png")).convert("RGB")
    b = Image.open(after / (prefix + ".png")).convert("RGB")
    if a.size != (256, 224) or b.size != a.size:
        raise ValueError("Unexpected screenshot sizes")
    pixels = [
        (x, y)
        for y in range(a.height)
        for x in range(a.width)
        if a.getpixel((x, y)) != b.getpixel((x, y))
    ]
    if not pixels or any(not (67 <= x <= 101 and 73 <= y <= 160) for x, y in pixels):
        raise ValueError("No visible edit, or changes outside Bret body region")
    return {
        "frame": 2940,
        "edited_rom_sha256": hashlib.sha256(edited_rom).hexdigest(),
        "edited_tiles_loaded": list(tiles),
        "changed_vram_bytes": len(vram_changes),
        "other_vram_unchanged": True,
        "oam_unchanged": True,
        "only_bret_palette_color_6_changed": True,
        "changed_screen_pixels": len(pixels),
        "screen_change_bounds": [
            min(x for x, y in pixels),
            min(y for x, y in pixels),
            max(x for x, y in pixels),
            max(y for x, y in pixels),
        ],
        "outside_bret_body_changes": 0,
        "scope": metadata["scope"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify(args.rom.read_bytes(), args.before, args.after)
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        with args.output.open("x") as file:
            file.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
