"""Side-by-side gameplay GIF of one controller recipe on two builds (same inputs, cold boot, memory only read).

The window defaults to the WINDOW frames after the recipe setup in which Mr. Perfect shows the most pieces that the
newer build replaced with Royal art (unique tiles of 'replaces' rows, as tools/check_perfect_poses_native.py).

    python3 tools/make_compare_gif.py CORE OLD.sfc NEW.sfc RECIPE --output OUT.gif [--labels old new] [--window 480]
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from check_perfect_poses_native import piece_tiles, replaced_rows, perfect_tiles
from libretro_step import Emulator


def image(video):
    raw, width, height, pitch, fmt = video
    bpp = 4 if fmt == 1 else 2
    im = Image.new('RGB', (width, height))
    px = im.load()
    for y in range(height):
        for x in range(width):
            v = int.from_bytes(raw[y * pitch + x * bpp:y * pitch + x * bpp + bpp], 'little')
            if fmt == 1:
                px[x, y] = (v >> 16 & 255, v >> 8 & 255, v & 255)
            elif fmt == 2:
                px[x, y] = ((v >> 11 & 31) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31)
            else:
                px[x, y] = ((v >> 10 & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v & 31) * 255 // 31)
    return im


def schedule(recipe):
    held = {}
    for port, s, b, d in recipe['inputs']:
        for k in range(s, s + d):
            held.setdefault(k, {0: set(), 1: set()})[port].add(b)
    return held


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('core'); p.add_argument('old', type=Path); p.add_argument('new', type=Path); p.add_argument('recipe', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--labels', nargs=2, default=['before', 'after'])
    p.add_argument('--window', type=int, default=480); p.add_argument('--step', type=int, default=3)
    p.add_argument('--start', type=int)
    a = p.parse_args()
    recipe = json.loads(a.recipe.read_text())
    held = schedule(recipe)
    setup = recipe.get('parameters', {}).get('setup_end', 1)
    start = a.start
    if start is None:
        owners, replaced = piece_tiles(a.new.read_bytes()), replaced_rows()
        unique = {t for t, ps in owners.items() if len(ps) == 1 and ps & replaced}
        emu, counts = Emulator(a.core, a.new), {}
        for k in range(1, recipe['frames'] + 1):
            emu.step(held.get(k, {0: set(), 1: set()}))
            if k >= setup and k % 2 == 0:
                counts[k] = sum(t in unique for t in perfect_tiles(emu.memory(3), emu.memory(0x10011), emu.memory(0x10012)))
        keys = sorted(counts)
        best = max(keys, key=lambda s: sum(counts.get(s + i, 0) for i in range(0, a.window, 2)))
        start = max(setup, best - 30)
    panels = []
    for rom in (a.old, a.new):
        emu, frames = Emulator(a.core, rom), []
        for k in range(1, start + a.window + 1):
            emu.step(held.get(k, {0: set(), 1: set()}))
            if k >= start and (k - start) % a.step == 0:
                frames.append(image(emu.last_video))
        panels.append(frames)
    out = []
    for n, (left, right) in enumerate(zip(*panels)):
        w, h = left.size
        canvas = Image.new('RGB', (w * 2 + 4, h + 14), (20, 20, 28))
        canvas.paste(left, (0, 14)); canvas.paste(right, (w + 4, 14))
        d = ImageDraw.Draw(canvas)
        d.text((2, 1), f'{a.labels[0]}  frame {start + n * a.step}', fill=(255, 230, 0))
        d.text((w + 6, 1), a.labels[1], fill=(255, 230, 0))
        out.append(canvas.convert('P', palette=Image.ADAPTIVE, colors=128))
    out[0].save(a.output, save_all=True, append_images=out[1:], duration=a.step * 1000 // 60, loop=0, optimize=True)
    print(json.dumps({'start': start, 'frames': len(out), 'bytes': a.output.stat().st_size}))


if __name__ == '__main__':
    main()
