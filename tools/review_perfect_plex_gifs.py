"""Labeled frame-by-frame review sheets from the committed Perfect-Plex GIFs.

Inputs are the published gameplay captures (no ROM needed):
  evidence/perfect-plex-receivers/royal-native-reference.gif
  evidence/perfect-plex-receivers/raw-undertaker-prototype.gif
  evidence/mr-perfect-import/perfect-plex.gif
Each GIF frame is 768x672 (3x native 256x224). Crops are taken at native
coordinates and enlarged with nearest-neighbour only.

    python3 tools/review_perfect_plex_gifs.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/perfect-plex-receivers/frame-review'
SOURCES = {
    'royal': ROOT / 'evidence/perfect-plex-receivers/royal-native-reference.gif',
    'raw': ROOT / 'evidence/perfect-plex-receivers/raw-undertaker-prototype.gif',
    'luna': ROOT / 'evidence/mr-perfect-import/perfect-plex.gif',
}
# Every cell is a 140x100 native crop at (left, top) in that source frame.
W, H, SCALE = 140, 100, 2
SHEETS = [
    ('entry-side-swap', [('royal', 0, 'Royal tie-up', 110, 40), ('royal', 2, 'Royal lift', 110, 40),
                         ('raw', 1, 'Raw tie-up', 40, 20), ('raw', 2, 'Raw first lift', 40, 20),
                         ('luna', 1, 'v0.16 tie-up', 40, 20), ('luna', 2, 'v0.16 first lift', 40, 20)]),
    ('lift-registration', [('royal', 3, 'Royal lift', 110, 40), ('royal', 5, 'Royal lift', 110, 40),
                           ('raw', 3, 'Raw lift', 40, 20), ('raw', 5, 'Raw lift', 40, 20)]),
    ('detached-shadow', [('raw', 4, 'Raw lift', 60, 50), ('raw', 9, 'Raw lift', 60, 50),
                         ('raw', 13, 'Raw drop', 60, 60), ('raw', 15, 'Raw bridge', 70, 60)]),
    ('bridge', [('royal', 10, 'Royal bridge', 100, 70), ('royal', 11, 'Royal bridge', 100, 80),
                ('raw', 15, 'Raw bridge', 70, 70), ('raw', 17, 'Raw bridge', 70, 70)]),
    ('exit', [('raw', 18, 'Raw bridge end', 60, 50), ('raw', 19, 'Raw exit', 60, 50),
              ('raw', 21, 'Raw exit', 60, 30), ('raw', 24, 'Raw exit', 60, 30)]),
]


def frames(path):
    with Image.open(path) as image:
        return [f.convert('RGB').resize((256, 224), Image.NEAREST) for f in ImageSequence.Iterator(image)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    loaded = {k: frames(v) for k, v in SOURCES.items()}
    w, h = W * SCALE, H * SCALE
    for name, cells in SHEETS:
        sheet = Image.new('RGB', (len(cells) * (w + 4) - 4, h + 14), (24, 24, 24))
        draw = ImageDraw.Draw(sheet)
        for i, (source, index, label, left, top) in enumerate(cells):
            crop = loaded[source][index].crop((left, top, left + W, top + H)).resize((w, h), Image.NEAREST)
            sheet.paste(crop, (i * (w + 4), 14))
            draw.text((i * (w + 4) + 2, 1), f'{label} [{source} #{index}]', fill=(255, 255, 255))
        sheet.save(OUT / f'{name}.png')
        print('wrote', (OUT / f'{name}.png').relative_to(ROOT))


if __name__ == '__main__':
    main()
