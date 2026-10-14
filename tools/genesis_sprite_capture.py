"""Reconstruct Genesis Mode-5 sprites from private native VDP snapshots.

Genesis Plus GX stores VRAM/CRAM words in host little-endian order. This reader
uses the cached SAT's Y/size/link and VRAM's live X/attributes, like its renderer.
Output images/pixel data must remain private; source gameplay evidence is separate.
"""
import argparse
import json
import struct
from pathlib import Path
from PIL import Image


def word(data, at):
    return struct.unpack_from('<H', data, at)[0]


def packed_tile(vram, ident):
    """64 palette indices from a Genesis 8x8 packed 4bpp tile."""
    at = (ident & 0x7ff) * 32
    values = []
    for y in range(8):
        for x in range(8):
            b = vram[at + y * 4 + ((x // 2) ^ 1)]
            values.append((b >> (0 if x & 1 else 4)) & 15)
    return values


def sprite_entries(vram, sat, registers):
    base = (registers[5] & 127) << 9
    index, seen, entries = 0, set(), []
    limit = 80 if registers[12] & 1 else 64
    while index not in seen and index < limit:
        seen.add(index)
        y, size_link = word(sat, index * 8), word(sat, index * 8 + 2)
        attr, x = word(vram, base + index * 8 + 4), word(vram, base + index * 8 + 6)
        entries.append(dict(index=index, x=(x & 511)-128, y=(y & 511)-128,
                            width=8*(1+((size_link >> 10) & 3)),
                            height=8*(1+((size_link >> 8) & 3)),
                            tile=attr & 2047, palette=(attr >> 13) & 3,
                            hflip=bool(attr & 0x800), vflip=bool(attr & 0x1000),
                            priority=bool(attr & 0x8000)))
        index = size_link & 127
        if not index:
            break
    return entries


def object_pixels(vram, entry):
    w, h = entry['width'], entry['height']
    tiles = {}
    result = []
    for y in range(h):
        for x in range(w):
            sx = w-1-x if entry['hflip'] else x
            sy = h-1-y if entry['vflip'] else y
            ident = (entry['tile'] + (sx//8)*(h//8) + sy//8) & 2047
            if ident not in tiles:
                tiles[ident] = packed_tile(vram, ident)
            result.append(tiles[ident][(sy % 8)*8 + sx % 8])
    return result


def native_color(value):
    # Reproduce GX normal-light RGB565, then the capture runner's RGB expansion.
    r, g, b = [(value >> shift & 7)*2 for shift in (0, 3, 6)]
    return ((r*2+(r >> 3))*255//31,
            (g*4+(g >> 2))*255//63,
            (b*2+(b >> 3))*255//31)


def reconstruct(vram, sat, registers, cram, entries, size=(256,224)):
    image = Image.new('RGBA', size)
    for entry in reversed(entries):
        pixels = object_pixels(vram, entry)
        for y in range(entry['height']):
            for x in range(entry['width']):
                value = pixels[y*entry['width']+x]
                px, py = entry['x']+x, entry['y']+y
                if value and 0 <= px < size[0] and 0 <= py < size[1]:
                    color = native_color(word(cram, entry['palette']*32+value*2))
                    image.putpixel((px,py), (*color,255))
    return image


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('prefix', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--tile-min', type=lambda x:int(x,0), default=0)
    p.add_argument('--tile-max', type=lambda x:int(x,0), default=2048)
    p.add_argument('--palette', type=int)
    a = p.parse_args()
    read = lambda name: Path(str(a.prefix)+'-'+name+'.bin').read_bytes()
    v, s, r, c = map(read, ('vram','oam','registers','cgram'))
    if (len(v),len(s),len(r),len(c)) != (65536,1024,32,128):
        raise ValueError('Not a complete Genesis observation-core snapshot')
    entries = [e for e in sprite_entries(v,s,r) if a.tile_min <= e['tile'] < a.tile_max
               and (a.palette is None or e['palette'] == a.palette)]
    source = Image.open(str(a.prefix)+'.png').convert('RGB')
    image = reconstruct(v,s,r,c,entries,source.size)
    a.output.mkdir(parents=True, exist_ok=True)
    image.save(a.output/'reconstructed.png')
    bounds = image.getbbox()
    if bounds:
        image.crop(bounds).save(a.output/'sprite.png')
    matches, opaque = 0, 0
    for y in range(image.height):
        for x in range(image.width):
            color = image.getpixel((x,y))
            if color[3]:
                opaque += 1
                matches += source.getpixel((x,y)) == color[:3]
    report = dict(entries=entries,bounds=bounds,opaque_pixels=opaque,
                  native_screen_matching_pixels=matches,
                  note='Foreground/background or earlier objects may occlude reconstructed pixels.')
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'entries'}))


if __name__ == '__main__':
    main()
