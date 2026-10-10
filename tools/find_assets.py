"""Find mode-1/mode-2 input candidates from immediate source-pointer assignments.

This is a conservative static heuristic, not a complete asset inventory or
proof that a candidate is graphics. Dynamic pointers are deliberately skipped.
"""

import argparse
import json
from pathlib import Path
import re
from decode_graphics import DecodeError, decode_block, render


def candidates(rom):
    found = {}
    pattern = rb"\xa9(..)\x85\x40\xa9(..)\x85\x42"
    for match in re.finditer(pattern, rom, re.S):
        low = int.from_bytes(match[1], "little")
        bank = int.from_bytes(match[2], "little")
        if not (0xC0 <= bank <= 0xFF or (0x80 <= bank <= 0xBF and low >= 0x8000)):
            continue
        offset = ((bank & 0x3F) << 16) | low
        if offset + 3 > len(rom) or rom[offset + 2] not in (1, 2):
            continue
        try:
            data, metadata = decode_block(rom, offset)
        except DecodeError:
            continue
        metadata["source_cpu_address"] = f"{bank:02X}:{low:04X}"
        metadata["pointer_assignment_offset"] = f"0x{match.start():06X}"
        found[offset] = (data, metadata)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-reference", action="store_true")
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    if len(rom) % 1024 == 512:
        rom = rom[512:]
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for offset, (data, metadata) in sorted(candidates(rom).items()):
        if args.verify_reference:
            from decoder_reference import reference_decode

            original, cpu = reference_decode(rom, offset)
            if original != data:
                raise DecodeError(f"Reference mismatch at {offset:06X}")
            metadata["reference_match"] = True
            metadata["reference_instructions"] = cpu.steps
        (args.output / f"{offset:06x}.bin").write_bytes(data)
        render(data, args.output / f"{offset:06x}-4bpp.png")
        results.append(metadata)
    (args.output / "candidates.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
