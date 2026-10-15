"""Labelled side-by-side GIF of two native captures of the same controller recipe.

Both captures must come from the same recipe (tools/run_controller_recipe.py, or
tools/verify_perfect_receivers_native.py --keep), so frame N is the same point in the input
sequence. Frames are native 256x224 screenshots, enlarged with nearest-neighbour only; nothing is
redrawn. Each panel is labelled with its build and the frame number of the recipe.

    python3 tools/make_before_after_gif.py BEFORE_DIR AFTER_DIR --output OUT.gif \
        --base CAPTURE_FROM [--start N] [--end N] [--step 2] [--scale 2] [--crop L T W H] [--labels "Before" "After"]
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw

BAR = 18


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base', type=int, default=0, help='recipe frame of capture frame 0')
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--end', type=int)
    parser.add_argument('--step', type=int, default=2)
    parser.add_argument('--labels', nargs=2, default=['Before (4ca2856 WIP)', 'After (fixed export)'])
    parser.add_argument('--title', default='')
    parser.add_argument('--scale', type=int, default=2)
    parser.add_argument('--crop', type=int, nargs=4, metavar=('LEFT', 'TOP', 'WIDTH', 'HEIGHT'))
    parser.add_argument('--interval', type=int, default=1, help='capture frames between saved screenshots')
    args = parser.parse_args()
    numbers = sorted(int(p.stem.split('-')[1]) for p in args.before.glob('frame-*.png')
                     if (args.after / p.name).exists())
    numbers = [n for n in numbers if n >= args.start and (args.end is None or n <= args.end)][::args.step]
    if not numbers:
        raise SystemExit('No common frames')
    frames = []
    for n in numbers:
        panels = [Image.open(d / f'frame-{n:06d}.png').convert('RGB') for d in (args.before, args.after)]
        if args.crop:
            l, t, cw, ch = args.crop
            panels = [p.crop((l, t, l + cw, t + ch)) for p in panels]
        SCALE = args.scale
        w, h = panels[0].size
        canvas = Image.new('RGB', (2 * w * SCALE + 4, h * SCALE + BAR), (16, 16, 16))
        draw = ImageDraw.Draw(canvas)
        for i, (panel, label) in enumerate(zip(panels, args.labels)):
            canvas.paste(panel.resize((w * SCALE, h * SCALE), Image.NEAREST), (i * (w * SCALE + 4), BAR))
            draw.text((i * (w * SCALE + 4) + 4, 3), label, fill=(255, 255, 255))
        draw.text((2 * w * SCALE - 120, 3), f'{args.title} frame {args.base + n}', fill=(255, 220, 120))
        frames.append(canvas.quantize(colors=255, method=Image.MEDIANCUT))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(args.output, save_all=True, append_images=frames[1:], duration=17 * args.step * args.interval, loop=0,
                   optimize=True)
    print(args.output, len(frames), 'frames', args.output.stat().st_size // 1024, 'KiB')


if __name__ == '__main__':
    main()
