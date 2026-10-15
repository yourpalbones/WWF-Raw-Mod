"""Contact sheet of planned receiving drawings: donor colour transfer vs own-art rebuild, per slot.

Renders through the editor code (tools/receiving_art_cli.js). Native size and 4x nearest-neighbour.
The sheet shows pixels derived from the supplied ROMs; keep it local unless it is reviewed gameplay proof.

    python3 tools/receiving_art_sheet.py ROM ROYAL PLAN.json --slot 11:3 --slot 9:3 ... --output SHEET.png
"""
import argparse
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['Luna', 'Bret', 'Undertaker', 'Yokozuna', 'Bam Bam', 'Scott Hall', 'Lex', 'Sting', 'Shawn', 'Syxx',
         'Nash', 'Owen', 'Perfect']


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('rom'); p.add_argument('royal'); p.add_argument('plan')
    p.add_argument('--slot', action='append', required=True, help='SLOT:DONOR')
    p.add_argument('--output', type=Path, required=True); p.add_argument('--scale', type=int, default=3)
    a = p.parse_args()
    W, H, Z = 56, 96, a.scale
    rows = []
    for spec in a.slot:
        slot, donor = spec.split(':')
        data = json.loads(subprocess.check_output(['node', str(ROOT / 'tools/receiving_art_cli.js'), a.rom, a.royal,
                                                   slot, donor, a.plan]))
        rows.append((int(slot), int(donor), data))
    sheet = Image.new('RGB', (12 * W * Z + 90, len(rows) * 2 * H * Z), (44, 46, 56))
    draw = ImageDraw.Draw(sheet)
    for r, (slot, donor, data) in enumerate(rows):
        pal = [tuple((c >> s & 31) * 255 // 31 for s in (0, 5, 10)) for c in data['palette']]
        for half, key in enumerate(('donor', 'image')):
            y0 = (2 * r + half) * H * Z
            draw.text((4, y0 + 4), f"{NAMES[slot]}\n{'donor colours' if key == 'donor' else 'own art'}", fill=(255, 230, 120))
            for i, pose in enumerate(data['poses']):
                img = pose[key]
                for y in range(144):
                    for x in range(144):
                        v = img[y * 144 + x]
                        X, Y = x - 72 + W // 2, y - 105 + H - 6
                        if v and 0 <= X < W and 0 <= Y < H:
                            draw.rectangle([90 + (i * W + X) * Z, y0 + Y * Z, 90 + (i * W + X) * Z + Z - 1, y0 + Y * Z + Z - 1], fill=pal[v])
    sheet.save(a.output)
    print(a.output, sheet.size)


if __name__ == '__main__':
    main()
