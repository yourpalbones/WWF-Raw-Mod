"""Apply the small evidence patch or verify paired emulator captures."""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from decode_sprite_tile import decode_sprite_tile

PACKAGE = Path(__file__).resolve().parents[1] / "evidence" / "bret-tile-edit"
ORIGINAL_HASH = "0af7b0d3022acd24a1fb15865a076519f7f56e7a4b33f12b6d851b3a91e5388c"


def patched_rom(rom):
    if hashlib.sha256(rom).hexdigest() != ORIGINAL_HASH:
        raise ValueError("ROM does not match the verified original USA ROM")
    patch = (PACKAGE / "bret-torso-test.ips").read_bytes()
    if patch[:5] != b"PATCH":
        raise ValueError("Invalid IPS header")
    result = bytearray(rom)
    cursor = 5
    edits = []
    while patch[cursor : cursor + 3] != b"EOF":
        address = int.from_bytes(patch[cursor : cursor + 3], "big")
        length = int.from_bytes(patch[cursor + 3 : cursor + 5], "big")
        cursor += 5
        if not length or cursor + length > len(patch) or address + length > len(rom):
            raise ValueError("Invalid evidence patch record")
        result[address : address + length] = patch[cursor : cursor + length]
        cursor += length
        edits.append((address, length))
    if cursor + 3 != len(patch) or edits != [(0x220152, 13), (0xFFDC, 4)]:
        raise ValueError("Unexpected patch contents")
    checksum = (sum(result[:0x200000]) + 2 * sum(result[0x200000:])) & 0xFFFF
    if result[0xFFDC:0xFFE0] != (checksum ^ 0xFFFF).to_bytes(
        2, "little"
    ) + checksum.to_bytes(2, "little"):
        raise ValueError("ROM checksum mismatch")
    return bytes(result)


def verify_captures(before, after):
    prefix = "frame-002940"

    def read(root, suffix):
        return (root / (prefix + suffix)).read_bytes()

    original_vram = read(before, "-vram.bin")
    edited_vram = read(after, "-vram.bin")
    if len(original_vram) != 65536 or len(edited_vram) != 65536:
        raise ValueError("Invalid VRAM capture size")
    patch = (PACKAGE / "bret-torso-test.ips").read_bytes()
    expected, size = decode_sprite_tile(patch, 10)
    if size != 13 or edited_vram[192:224] != expected:
        raise ValueError("Expected edited tile was not loaded")
    changed = [i for i, (a, b) in enumerate(zip(original_vram, edited_vram)) if a != b]
    if len(changed) != 9 or any(not 192 <= i < 224 for i in changed):
        raise ValueError("Unexpected VRAM changes")
    for suffix in ["-oam.bin", "-cgram.bin"]:
        if read(before, suffix) != read(after, suffix):
            raise ValueError("OAM or palette changed")
    a = Image.open(before / (prefix + ".png")).convert("RGB")
    b = Image.open(after / (prefix + ".png")).convert("RGB")
    if a.size != b.size or a.size != (256, 224):
        raise ValueError("Unexpected screenshot sizes")
    pixels = [
        (x, y)
        for y in range(a.height)
        for x in range(a.width)
        if a.getpixel((x, y)) != b.getpixel((x, y))
    ]
    bounds = (
        [
            min(x for x, y in pixels),
            min(y for x, y in pixels),
            max(x for x, y in pixels),
            max(y for x, y in pixels),
        ]
        if pixels
        else []
    )
    if len(pixels) != 5 or bounds != [73, 109, 80, 111]:
        raise ValueError("Unexpected visible changes")
    return {
        "expected_tile_loaded": True,
        "changed_screen_pixels": len(pixels),
        "screen_change_bounds": bounds,
        "other_vram_oam_palette_unchanged": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path, nargs="?")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    args = parser.parse_args()
    for name, expected in json.loads((PACKAGE / "sha256.json").read_text()).items():
        if hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Package file hash mismatch: {name}")
    if args.rom:
        if not args.output:
            parser.error("--output is required with ROM")
        result = patched_rom(args.rom.read_bytes())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as file:
            file.write(result)
        print("Verified original ROM; wrote separate patched copy:", args.output)
    if args.before or args.after:
        if not args.before or not args.after:
            parser.error("Both --before and --after are required")
        print(json.dumps(verify_captures(args.before, args.after), indent=2))
    if not args.rom and not args.before:
        parser.error("Provide ROM or paired capture directories")


if __name__ == "__main__":
    main()
