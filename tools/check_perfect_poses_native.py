"""Check Mr. Perfect's on-screen art in cold-boot gameplay against his slot's own pieces.

Replays a controller-only recipe (memory is only read) and, every STEP frames, reads Perfect's objects (P1,
OBJ palette 0) from VRAM/OAM. Each 8x8 tile is looked up in the tiles of slot 12's pieces in the same ROM:

- unowned: tiles not in any slot-12 piece (excluding shared shadow/common tiles listed by --allow);
- pieces_seen: pieces identified by a tile no other piece uses;
- replaced_seen: of those, pieces the manifest marks as replaced by Royal Perfect art (rows with 'replaces');
- adapted_tiles: with --old ROM, tiles that only the old build's replaced (adapted Raw Bret) pieces used.

    python3 tools/check_perfect_poses_native.py CORE ROM RECIPE --output REPORT.json [--old OLD.sfc] [--step 2]
"""
import argparse
import json
import subprocess
from pathlib import Path

from libretro_step import Emulator
from raw_parts import resolve_index

ROOT = Path(__file__).resolve().parents[1]


def planar(pixels):
    out = bytearray(32)
    for i, v in enumerate(pixels):
        x, y = i % 8, i // 8
        for p in range(4):
            out[(p >> 1) * 16 + y * 2 + (p & 1)] |= ((v >> p) & 1) << (7 - x)
    return bytes(out)


def piece_tiles(rom):
    """{tile bytes: {(kind, index)}} for every slot-12 piece."""
    owners = {}
    indices = [('primary', i) for i in list(range(998)) + list(range(1000, 1012))] + [('secondary', i) for i in range(722)]
    for kind, i in indices:
        for part in resolve_index(rom, 12, kind, i)['parts']:
            for pixels in part['pixels']:
                if any(pixels):
                    owners.setdefault(planar(pixels), set()).add((kind, i))
    return owners


def replaced_rows():
    text = (ROOT / 'editor/royal-import-layouts.js').read_text()
    manifest = json.loads(text[text.index('=') + 1:text.rindex(';')])
    return {(f['kind'], f['index']) for f in manifest['frames'] if 'replaces' in f}


def perfect_tiles(vram, oam, regs):
    obsel = regs[0x2101]
    base, select = (obsel & 3) << 14, ((obsel >> 3) & 3) << 13
    sizes = [(8, 16), (8, 32), (8, 64), (16, 32), (16, 64), (32, 64)][obsel >> 5]
    out = []
    for i in range(128):
        x, y, number, attr = oam[i * 4:i * 4 + 4]
        if (attr >> 1) & 7 != 0:
            continue
        high = (oam[512 + i // 4] >> (2 * (i % 4))) & 3
        size = sizes[bool(high & 2)]
        if y >= 224 and y + size <= 256:
            continue
        for ty in range(size // 8):
            for tx in range(size // 8):
                n = ((number & 0xF0) + ty * 16 + ((number + tx) & 15)) & 255
                a = (base + ((select + 8192) if attr & 1 else 0) + n * 32) & 65535
                data = bytes(vram[a:a + 32])
                if any(data):
                    out.append(data)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('core'); p.add_argument('rom', type=Path); p.add_argument('recipe', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--old', type=Path, help='earlier build: count tiles only its replaced pieces used')
    p.add_argument('--step', type=int, default=2)
    p.add_argument('--start', type=int, help='first frame to inspect (default: the recipe setup end)')
    a = p.parse_args()
    rom = a.rom.read_bytes()
    owners = piece_tiles(rom)
    replaced = replaced_rows()
    adapted_only = set()
    if a.old:
        old_owners = piece_tiles(a.old.read_bytes())
        adapted_only = {t for t, ps in old_owners.items() if ps & replaced and t not in owners}
    recipe = json.loads(a.recipe.read_text())
    start = a.start or recipe.get('parameters', {}).get('setup_end', 1)
    emu = Emulator(a.core, a.rom)
    held = {}
    for port, s, b, d in recipe['inputs']:
        for k in range(s, s + d):
            held.setdefault(k, {0: set(), 1: set()})[port].add(b)
    totals = {'frames': 0, 'tiles': 0, 'owned': 0, 'unowned': 0, 'adapted_tiles': 0}
    unowned, seen = {}, set()
    for k in range(1, recipe['frames'] + 1):
        emu.step(held.get(k, {0: set(), 1: set()}))
        if k < start or k % a.step:
            continue
        tiles = perfect_tiles(emu.memory(3), emu.memory(0x10011), emu.memory(0x10012))
        if not tiles:
            continue
        totals['frames'] += 1
        for t in tiles:
            totals['tiles'] += 1
            if t in owners:
                totals['owned'] += 1
                if len(owners[t]) == 1:
                    seen |= owners[t]
            else:
                totals['unowned'] += 1
                unowned.setdefault(t.hex(), []).append(k)
            if t in adapted_only:
                totals['adapted_tiles'] += 1
    report = {'rom_sha256': subprocess.run(['sha256sum', str(a.rom)], capture_output=True, text=True).stdout.split()[0],
              'recipe': a.recipe.name, 'start': start, 'step': a.step, **totals,
              'unowned_distinct': len(unowned), 'unowned_first_frames': {h: v[:3] for h, v in list(unowned.items())[:20]},
              'pieces_seen': len(seen), 'replaced_seen': len(seen & replaced),
              'replaced_seen_list': sorted(f'{k}/{i}' for k, i in seen & replaced)}
    a.output.write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('unowned_first_frames', 'replaced_seen_list')}))


if __name__ == '__main__':
    main()
