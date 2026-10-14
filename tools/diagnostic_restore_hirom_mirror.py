"""DIAGNOSTIC ONLY: restore the original cartridge's $F0-$FF mirror in an 8 MiB export.

The stock WWF Raw announcer screen reads graphics through bank $FF ($FF:2F37).
On the original 3 MiB HiROM cartridge, that bank mirrors file 0x2F0000. The
8 MiB ExHiROM expansion maps $F0-$FF to file 0x300000-0x3FFFFF and leaves it
as 0xFF, so every match stalls before it starts (PP-0). This script copies
original bytes 0x200000-0x2FFFFF into that range of a scratch copy, so that
gameplay can be measured.

It is not the importer fix, and its output is never a release. It refuses to
write unless the target range is entirely 0xFF.

    python3 tools/diagnostic_restore_hirom_mirror.py ORIGINAL_RAW.sfc EXPORT.sfc --output SCRATCH.sfc
"""
import argparse
import hashlib
from pathlib import Path

RAW_SHA256 = '0af7b0d3022acd24a1fb15865a076519f7f56e7a4b33f12b6d851b3a91e5388c'

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('original', type=Path)
parser.add_argument('export', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
original, export = args.original.read_bytes(), bytearray(args.export.read_bytes())
if hashlib.sha256(original).hexdigest() != RAW_SHA256:
    raise SystemExit('Expected the unmodified WWF Raw USA ROM')
if len(export) != 0x800000:
    raise SystemExit('Expected an 8 MiB export')
if any(v != 255 for v in export[0x300000:0x400000]):
    raise SystemExit('0x300000-0x3FFFFF is not empty; refusing to overwrite')
export[0x300000:0x400000] = original[0x200000:0x300000]
args.output.write_bytes(export)
print('wrote', args.output, hashlib.sha256(export).hexdigest())
