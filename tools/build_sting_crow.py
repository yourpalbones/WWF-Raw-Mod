"""Apply the alternate Crow Sting art (tools/sting_crow_art.py) to the Doink/Sting slot of a WWF Raw ROM.

The current Sting gear is left exactly as it is in the repository and the editor; this is a second take you can
compare it with. The result uses the same storage, worker and marker (STING-NATIVE-GEAR4) as the current Sting, so
the editor, Add Mr. Perfect and every tool read it as the Sting gear; only the art and the slot palette differ.
Apply it before Add Mr. Perfect (the Perfect-Plex receivers copy Sting's pixels when they are installed).

The donor is the Undertaker's native art in the input ROM (slot 2), read with the static part resolver
(tools/raw_parts.py), so no memory dump is needed. Its pixels stay in your ROM; the repository holds only the
authoring rules. Nothing else in the ROM changes: other wrestlers, portraits, names, songs and the Doink/Sting
moves (Scorpion Deathlock) are kept.

    python3 tools/build_sting_crow.py RAW.sfc --output OUT.sfc

RAW.sfc must still hold the native Undertaker (slot 2) art; Sting may already be applied or not.
"""
import argparse
import hashlib
from pathlib import Path

import build_sting_replacement
import sting_crow_art
from raw_parts import TABLES, descriptor_address, parse_descriptor, tile_source, packet_length, decode_packet, planar_pixels

DONOR = 2


def donor_catalog(rom, slot=DONOR):
    """The donor's 1,720 frame pieces in the shape scott_frame_catalog.catalog() gives, read without WRAM."""
    frames = []
    for kind in ('primary', 'secondary'):
        own, total = TABLES[kind][2], TABLES[kind][3]
        for index in range(total):
            parts, offset, length = parse_descriptor(rom, kind, descriptor_address(rom, slot, kind, index))
            out = []
            for part in parts:
                refs = []
                for tile_id, field in part['tiles']:
                    source, compressed = tile_source(rom, kind, tile_id, -1)
                    raw = decode_packet(rom, source) if compressed else bytes(rom[source:source + 32])
                    refs.append({'field': field, 'relative': field - offset, 'tile_id': tile_id, 'source': source,
                                 'compressed': compressed, 'length': packet_length(rom, source) if compressed else 32,
                                 'pixels': planar_pixels(raw)})
                out.append({k: part[k] for k in ('x', 'y', 'size', 'hflip', 'vflip')} | {'refs': refs})
            frames.append({'offset': offset, 'length': length, 'kind': kind, 'index': index, 'common': index >= own,
                           'parts': out})
    return frames


def build(rom):
    out, recipe, report = build_sting_replacement.build(rom, None, art=sting_crow_art.author, frames=donor_catalog(rom),
                                                        palette=sting_crow_art.PALETTE)
    return out, recipe, report


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('rom', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out, _, report = build(a.rom.read_bytes())
    a.output.write_bytes(out)
    print({'private_tiles': report['private_tiles_by_kind'], 'sha256': hashlib.sha256(out).hexdigest()})


if __name__ == '__main__':
    main()
