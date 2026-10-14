"""Royal Rumble and Raw side by side through the Perfect-Plex's pin, release and recovery (native screenshots).

Both panels are aligned on the frame the bridge (step 11) first shows and run until both wrestlers have regained
control in both games (the walk that shows it included). A caption under each panel names the phase from that
game's own recovery events (tools/recovery_bot.py). Screens are native; nothing is mirrored or moved.

    python3 tools/make_exit_comparison_gif.py ROYAL_CAPTURE ROYAL_RECIPE ROYAL_BRIDGE RAW_CAPTURE RAW_RECIPE RAW_BRIDGE
        --output OUT.gif [--before 20] [--step 2] [--scale 2]

ROYAL_CAPTURE is tools/capture_royal_perfect_plex.py output (capture.json gives its first recipe frame); RAW_CAPTURE
holds frame-NNNNNN.png from recipe frame --raw-first. *_BRIDGE is the recipe frame where step 11 first shows.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def phase(recipe, frame, release):
    r = recipe['recovery']
    if frame < release:
        return 'pin (bridge held)'
    if frame < r['perfect_stands']:
        return 'release: Perfect gets up'
    if frame < r['receiver_stands']:
        return 'Perfect in control; receiver down (P2 mashing)'
    if frame < r['walk_end']:
        return 'both in control: P1 walks up, P2 walks down'
    return 'both in control'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('royal_capture', type=Path); p.add_argument('royal_recipe', type=Path); p.add_argument('royal_bridge', type=int)
    p.add_argument('raw_capture', type=Path); p.add_argument('raw_recipe', type=Path); p.add_argument('raw_bridge', type=int)
    p.add_argument('--raw-first', type=int, required=True, help='recipe frame of the Raw capture\'s frame 1')
    p.add_argument('--hold', type=int, default=56, help='frames from the bridge to the release')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--before', type=int, default=20); p.add_argument('--step', type=int, default=2)
    p.add_argument('--scale', type=int, default=2)
    a = p.parse_args()
    royal, raw = json.loads(a.royal_recipe.read_text()), json.loads(a.raw_recipe.read_text())
    royal_first = json.loads((a.royal_capture / 'capture.json').read_text())['first_recipe_frame']
    end = max(royal['recovery']['walk_end'] - a.royal_bridge, raw['recovery']['walk_end'] - a.raw_bridge) + 20
    frames = []
    for t in range(-a.before, end, a.step):
        panels = []
        for name, capture, recipe, bridge, first in [('Royal Rumble', a.royal_capture, royal, a.royal_bridge, royal_first),
                                                     ('WWF Raw + Mr. Perfect', a.raw_capture, raw, a.raw_bridge, a.raw_first)]:
            frame = min(bridge + t, recipe['recovery']['end'])
            path = capture / f'frame-{frame - first + 1:06d}.png'
            screen = Image.open(path).convert('RGB')
            screen = screen.resize((screen.width * a.scale, screen.height * a.scale), Image.NEAREST)
            panel = Image.new('RGB', (screen.width, screen.height + 34), 'black')
            panel.paste(screen, (0, 18))
            d = ImageDraw.Draw(panel)
            d.text((4, 3), f'{name} (native)', fill='white')
            d.text((4, screen.height + 21), f'{t:+d} frames from the bridge: {phase(recipe, frame, bridge + a.hold)}', fill='white')
            panels.append(panel)
        sheet = Image.new('RGB', (panels[0].width * 2 + 6, panels[0].height), (40, 40, 40))
        sheet.paste(panels[0], (0, 0)); sheet.paste(panels[1], (panels[0].width + 6, 0))
        frames.append(sheet.convert('P', palette=Image.ADAPTIVE, colors=255))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(a.output, save_all=True, append_images=frames[1:], duration=int(1000 * a.step / 60), loop=0, optimize=True)
    print(a.output, len(frames), 'frames')


if __name__ == '__main__':
    main()
