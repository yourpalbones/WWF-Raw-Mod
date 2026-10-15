"""Labeled frame sheets from verify_perfect_receivers_native.py --keep captures.

For each scenario this picks frames from the measured move window: tie-up, first
lift, mid-lift, bridge, last move frame and 40 frames after. It crops the 150x150
native region around the pair and enlarges it 2x with nearest-neighbour only.

    python3 tools/sheet_perfect_captures.py VERIFY_OUTPUT_DIR --output evidence/perfect-plex-receivers/native-wip/scenarios
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('verify', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
for measurement in sorted(args.verify.glob('*-measurement.json')):
    name = measurement.name[:-len('-measurement.json')]
    capture = args.verify / f'{name}-capture'
    data = json.loads(measurement.read_text())
    move = [c['frame'] for c in data['all_frames'] if c['actions'] == [600, 540]]
    if not move or not capture.exists():
        continue
    first, last = move[0], move[-1]
    picks = [(first - 3, 'tie-up'), (first + 4, 'first lift'), (first + 40, 'lift'), (first + 85, 'bridge'),
             (last, 'last move frame'), (last + 40, 'after move')]
    x_mid = sum(data['all_frames'][move.index(first)]['x']) // 2
    camera = next((r['camera_x'] for r in data['rows'] if 'camera_x' in r), None)
    left = max(0, min(256 - 150, (x_mid - camera - 75) if camera is not None else 53))
    box, scale = (left, 20, left + 150, 170), 2
    cells = [(f, label) for f, label in picks if (capture / f'frame-{f:06d}.png').exists()]
    w, h = 150 * scale, 150 * scale
    sheet = Image.new('RGB', (len(cells) * (w + 4) - 4, h + 14), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for i, (f, label) in enumerate(cells):
        im = Image.open(capture / f'frame-{f:06d}.png').convert('RGB').crop(box).resize((w, h), Image.NEAREST)
        sheet.paste(im, (i * (w + 4), 14))
        draw.text((i * (w + 4) + 2, 1), f'{name} #{f} {label}', fill=(255, 255, 255))
    sheet.save(args.output / f'{name}.png')
    print('wrote', args.output / f'{name}.png')
