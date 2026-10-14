"""Compare the editor's paired Perfect-Plex preview with native gameplay screenshots.

For each step, takes the middle native frame showing that step (from a measurement made by
tools/measure_perfect_pair.py on a kept capture), renders the same step with tools/preview_points.js and
counts preview pixels whose screen colour matches within 8/255 per channel. Occluders in front of the
pair (the referee) lower the score; nothing in the preview is adjusted to match.

    python3 tools/check_preview_native.py ROM RECEIVER_SLOT MEASUREMENT.json CAPTURE_DIR left|right
"""
import argparse
import json
import subprocess
from pathlib import Path
from PIL import Image

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
        img = Image.open(a.capture / f"frame-{r['frame']:06d}.png").convert('RGB')
        dx = r['attacker_origin_screen'] - (108 if a.facing == 'left' else 148)
        dy = r['vertical']['attacker_origin_y'] - 150
        final = {(x, y): (R, G, B) for x, y, R, G, B, _ in pts}
        match = total = 0
        for (x, y), colour in final.items():
            if 0 <= x + dx < img.width and 0 <= y + dy < img.height:
                total += 1
                match += max(abs(c - d) for c, d in zip(img.getpixel((x + dx, y + dy)), colour)) <= 8
        result.append({'step': k + 1, 'frame': r['frame'], 'pixels': total, 'matching': match})
    print(json.dumps({'receiver': a.receiver, 'facing': a.facing,
                      'match_ratio': [round(s['matching'] / s['pixels'], 3) for s in result], 'steps': result}))


if __name__ == '__main__':
    main()
