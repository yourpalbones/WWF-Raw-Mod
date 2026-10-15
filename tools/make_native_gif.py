"""Native gameplay GIF of one kept capture, cropped around the pair (nearest-neighbour, labelled).

    python3 tools/make_native_gif.py CAPTURE_DIR MEASUREMENT.json --output OUT.gif --label TEXT [--step 2]
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('capture', type=Path); p.add_argument('measurement', type=Path)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--label', default='')
    p.add_argument('--step', type=int, default=2); p.add_argument('--scale', type=int, default=2)
    a = p.parse_args()
    rows = [r for r in json.loads(a.measurement.read_text())['rows'] if 'camera_x' in r]
    cx = sorted(r['attacker_origin_screen'] for r in rows)[len(rows) // 2]
    cy = sorted(r['vertical']['attacker_origin_y'] for r in rows)[len(rows) // 2]
    left, top = max(0, min(256 - 200, cx - 100)), max(0, min(224 - 150, cy - 115))
    first, last = rows[0]['frame'] - 30, rows[-1]['frame'] + 90
    frames = []
    for n in range(first, last + 1, a.step):
        path = a.capture / f'frame-{n:06d}.png'
        if not path.exists():
            continue
        im = Image.open(path).convert('RGB').crop((left, top, left + 200, top + 150))
        im = im.resize((200 * a.scale, 150 * a.scale), Image.NEAREST)
        canvas = Image.new('RGB', (im.width, im.height + 16), (16, 16, 16))
        canvas.paste(im, (0, 16))
        ImageDraw.Draw(canvas).text((4, 2), f'{a.label}  frame {n}', fill=(255, 230, 120))
        frames.append(canvas.quantize(colors=255, method=Image.MEDIANCUT))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(a.output, save_all=True, append_images=frames[1:], duration=17 * a.step, loop=0, optimize=True)
    print(a.output, len(frames), 'frames', a.output.stat().st_size // 1024, 'KiB')


if __name__ == '__main__':
    main()
