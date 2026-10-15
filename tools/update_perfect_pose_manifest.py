"""Refresh only the frame rows of editor/royal-import-layouts.js from the pose converter (with matches).

The finisher, programs and other recipe fields are kept as published. Rows are addresses and geometry only.

    python3 tools/update_perfect_pose_manifest.py RAW.sfc RAW_WRAM.bin ROYAL.sfc ROYAL_WRAM.bin \\
        --matches data/perfect-pose-matches.json --manifest editor/royal-import-layouts.js \\
        --heads data/perfect-head-sources.json [--previous PREVIOUS_IMPORT.sfc]

A Royal row whose placement changes (a seam override, tools/close_perfect_seams.py) gets 'replaces_royal': the hashes
of the art it held before, read from PREVIOUS_IMPORT (an import made with the manifest being replaced). Update
Perfect-Plex replaces a piece that still holds that art; a piece the user edited is kept.
"""
import argparse
import json
from pathlib import Path

from convert_perfect_poses import convert
from build_royal_import_manifest import frame_rows, coverage, mark_hair, mark_heads
from match_perfect_poses import effective, fnv
from raw_parts import resolve_index, raster

PREFIX = 'window.RAW_ROYAL_IMPORT_MANIFEST='


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('raw_rom', 'raw_wram', 'royal_rom', 'royal_wram'):
        p.add_argument(name, type=Path)
    p.add_argument('--matches', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--heads', type=Path, help='Royal Perfect head sources (tools/rebuild_perfect_heads.py)')
    p.add_argument('--previous', type=Path, help='an import made with the current manifest (for replaces_royal)')
    p.add_argument('--head-review', type=Path, default=Path(__file__).resolve().parents[1] / 'data/perfect-head-review.json')
    a = p.parse_args()
    text = a.manifest.read_text()
    manifest = json.loads(text[len(PREFIX):text.rindex(';')])
    all_rows = json.loads(a.matches.read_text())['rows']
    matches = effective(all_rows)   # accepted silhouette matches + reviewed semantic counterparts
    rows = frame_rows(convert(*(getattr(a, n).read_bytes() for n in ('raw_rom', 'raw_wram', 'royal_rom', 'royal_wram')), matches))
    before = {(r['kind'], r['index']): r for r in manifest['frames']}
    keep = ('hair', 'replaces', 'head', 'replaces_hair', 'replaces_royal')
    previous = a.previous.read_bytes() if a.previous else None
    for r in rows:
        old = before[(r['kind'], r['index'])]
        if 'replaces' not in r and {k: v for k, v in r.items() if k not in keep} != \
                {k: v for k, v in old.items() if k not in keep}:
            raise ValueError(f"Unmatched row changed: {r['kind']}/{r['index']}")
        held = list(old.get('replaces_royal', []))
        if r['royal'] and old['royal'] and r['parts'] != old['parts']:
            if previous is None:
                raise ValueError(f"Royal row {r['kind']}/{r['index']} changes: pass --previous")
            held.append(fnv(raster(resolve_index(previous, 12, r['kind'], r['index'])['parts'])))
        if held and r['royal']:
            r['replaces_royal'] = sorted(set(held))
    mark_hair(rows, a.raw_rom.read_bytes(), all_rows)
    if a.heads:
        review = json.loads(a.head_review.read_text()) if a.head_review.exists() else {}
        manifest['heads'] = mark_heads(rows, json.loads(a.heads.read_text()), a.royal_rom.read_bytes(),
                                       a.royal_wram.read_bytes(), review)
    manifest['frames'] = rows
    manifest['coverage'] = coverage(rows)
    a.manifest.write_text(PREFIX + json.dumps(manifest, separators=(',', ':')) + ';\n')
    print(manifest['coverage'])


if __name__ == '__main__':
    main()
