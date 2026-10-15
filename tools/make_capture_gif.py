"""GIF of a window of native screenshots from a capture (frame-NNNNNN.png), with a caption line.

    python3 tools/make_capture_gif.py CAPTURE --first N --last M --output OUT.gif [--caption TEXT] [--step 2] [--scale 2]

N and M are capture frame numbers. Screens are native (nearest-neighbour enlargement only).
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('capture', type=Path)
    p.add_argument('--first', type=int, required=True); p.add_argument('--last', type=int, required=True)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--caption', default='')
    p.add_argument('--step', type=int, default=2); p.add_argument('--scale', type=int, default=2)
    a = p.parse_args()
    frames = []
    for f in range(a.first, a.last + 1, a.step):
        screen = Image.open(a.capture / f'frame-{f:06d}.png').convert('RGB')
        screen = screen.resize((screen.width * a.scale, screen.height * a.scale), Image.NEAREST)
        panel = Image.new('RGB', (screen.width, screen.height + 18), 'black')
        panel.paste(screen, (0, 0))
        ImageDraw.Draw(panel).text((4, screen.height + 3), f'{a.caption}  frame {f}', fill='white')
        frames.append(panel.convert('P', palette=Image.ADAPTIVE, colors=255))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(a.output, save_all=True, append_images=frames[1:], duration=int(1000 * a.step / 60), loop=0, optimize=True)
    print(a.output, len(frames), 'frames')


if __name__ == '__main__':
    main()
