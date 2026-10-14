"""Compare the editor's paired Perfect-Plex preview with native gameplay screenshots.

For each step, takes the middle native frame showing that step (from a measurement made by
tools/measure_perfect_pair.py on a kept capture) and renders the same step with tools/preview_points.js.
The native side is rebuilt from that frame's OAM and VRAM: only the two actors' objects (palettes 0 and 1),
in OAM priority order, so background layers drawn over sprites (the ring ropes) and other sprites (the
referee) do not count. A preview pixel matches when the native actor pixel at that screen position has the
same palette index. Nothing in the preview is adjusted to match.

    python3 tools/check_preview_native.py ROM RECEIVER_SLOT MEASUREMENT.json CAPTURE_DIR left|right
"""
import argparse
import json
import subprocess
from pathlib import Path
from PIL import Image
from measure_perfect_pair import oam_indices
from extract_oam import objects

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('rom', type=Path); p.add_argument('receiver', type=int); p.add_argument('measurement', type=Path)
    p.add_argument('capture', type=Path); p.add_argument('facing', choices=['left', 'right'])
    a = p.parse_args()
    rows = [r for r in json.loads(a.measurement.read_text())['rows'] if 'camera_x' in r]
    result = []
    for k in range(12):
        cand = [r for r in rows if r['attacker_pose'] == k and r['receiver_pose'] == k]
        r = cand[len(cand) // 2]
        pts = json.loads(subprocess.check_output(['node', str(ROOT / 'tools/preview_points.js'), str(a.rom),
                                                  str(a.receiver), str(k), a.facing]))
        prefix = a.capture / f"frame-{r['frame']:06d}"
        vram, oam, cgram, regs = (Path(f'{prefix}-{n}.bin').read_bytes() for n in ('vram', 'oam', 'cgram', 'registers'))
        native = {}
        for rec, _ in sorted(objects(vram, oam, cgram, regs[0x2101]), key=lambda o: -o[0]['index']):
            if rec['palette'] in (0, 1) and rec['y'] < 224:
                for (x, y), v in oam_indices(vram, oam, rec, regs[0x2101]).items():
                    native[rec['x'] + x, rec['y'] + y] = v
        dx = r['attacker_origin_screen'] - (108 if a.facing == 'left' else 148)
        dy = r['vertical']['attacker_origin_y'] - 150
        final = {(x, y): v for x, y, R, G, B, _, v in pts}
        match = total = 0
        for (x, y), v in final.items():
            total += 1
            match += native.get((x + dx, y + dy)) == v
        result.append({'step': k + 1, 'frame': r['frame'], 'pixels': total, 'matching': match})
    print(json.dumps({'receiver': a.receiver, 'facing': a.facing,
                      'match_ratio': [round(s['matching'] / s['pixels'], 3) for s in result], 'steps': result}))


if __name__ == '__main__':
    main()
