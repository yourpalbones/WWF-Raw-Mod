"""Compare extractors with live decoder/tile snapshots from the patched core."""

import argparse
import hashlib
import json
from pathlib import Path
from decode_graphics import decode_block
from decode_sprite_tile import decode_sprite_tile, encode_sprite_tile


def validate(rom, root):
    results = {
        "complete_blocks": 0,
        "partial_blocks_skipped": 0,
        "tile_events": 0,
        "distinct_tile_sources": 0,
        "byte_identical_tile_encodings": 0,
    }
    errors = []
    sources = set()
    blocks = root / "decodes.jsonl"
    if blocks.exists():
        for line in blocks.read_text().splitlines():
            entry = json.loads(line)
            if "partial" not in entry:
                raise ValueError(
                    "Older trace has no partial-return flag; recapture with the current patch"
                )
            if entry["partial"]:
                results["partial_blocks_skipped"] += 1
                continue
            source = entry["source"]
            data, _ = decode_block(rom, source & 0x3FFFFF)
            captured = (
                root / "assets" / f"decoded-{entry['event']:06d}-{source:06x}.bin"
            ).read_bytes()
            if captured != data:
                errors.append(
                    {"kind": "block", "event": entry["event"], "source": source}
                )
            else:
                results["complete_blocks"] += 1
    tiles = root / "tiles.jsonl"
    if tiles.exists():
        for line in tiles.read_text().splitlines():
            entry = json.loads(line)
            source = entry["source"]
            offset = source & 0x3FFFFF
            data, consumed = decode_sprite_tile(rom, offset)
            captured = (
                root / "assets" / f"tile-{entry['event']:06d}-{source:06x}.bin"
            ).read_bytes()
            if captured != data:
                errors.append(
                    {"kind": "tile", "event": entry["event"], "source": source}
                )
            results["tile_events"] += 1
            sources.add(source)
            if encode_sprite_tile(data) == rom[offset : offset + consumed]:
                results["byte_identical_tile_encodings"] += 1
            else:
                errors.append(
                    {
                        "kind": "tile_reencoding",
                        "event": entry["event"],
                        "source": source,
                    }
                )
    results["distinct_tile_sources"] = len(sources)
    results["rom_sha256"] = hashlib.sha256(rom).hexdigest()
    results["errors"] = errors
    if not results["complete_blocks"] and not results["tile_events"]:
        raise ValueError(
            "Trace contains no complete blocks or sprite tiles to validate"
        )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    if len(rom) % 1024 == 512:
        rom = rom[512:]
    result = validate(rom, args.trace)
    (args.trace / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
