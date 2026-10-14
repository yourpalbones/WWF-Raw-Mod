"""Refresh only the frame rows of editor/royal-import-layouts.js from the pose converter (with matches).

The finisher, programs and other recipe fields are kept as published. Rows are addresses and geometry only.

    python3 tools/update_perfect_pose_manifest.py RAW.sfc RAW_WRAM.bin ROYAL.sfc ROYAL_WRAM.bin \\
        --matches data/perfect-pose-matches.json --manifest editor/royal-import-layouts.js
"""
import argparse
import json
from pathlib import Path

from convert_perfect_poses import convert
from build_royal_import_manifest import frame_rows, coverage, mark_hair

PREFIX = 'window.RAW_ROYAL_IMPORT_MANIFEST='


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('raw_rom', 'raw_wram', 'royal_rom', 'royal_wram'):
        p.add_argument(name, type=Path)
    p.add_argument('--matches', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    a = p.parse_args()
    text = a.manifest.read_text()
    manifest = json.loads(text[len(PREFIX):text.rindex(';')])
    matches = json.loads(a.matches.read_text())['rows']
    rows = frame_rows(convert(*(getattr(a, n).read_bytes() for n in ('raw_rom', 'raw_wram', 'royal_rom', 'royal_wram')), matches))
    before = {(r['kind'], r['index']): r for r in manifest['frames']}
    for r in rows:
        old = before[(r['kind'], r['index'])]
        if 'replaces' not in r and {k: v for k, v in r.items() if k not in ('hair', 'replaces')} != \
                {k: v for k, v in old.items() if k not in ('hair', 'replaces')}:
            raise ValueError(f"Unmatched row changed: {r['kind']}/{r['index']}")
    mark_hair(rows, a.raw_rom.read_bytes(), matches)
    manifest['frames'] = rows
    manifest['coverage'] = coverage(rows)
    a.manifest.write_text(PREFIX + json.dumps(manifest, separators=(',', ':')) + ';\n')
    print(manifest['coverage'])


if __name__ == '__main__':
    main()
