"""Plan the Perfect-Plex exit (pin hold, release, both wrestlers' recovery) from Royal Rumble's own capture.

Reads local ROMs and a Royal capture; writes geometry only (numbers, stock profile addresses and Royal tile
addresses). Nothing from a ROM is published.

Royal Rumble, after the bridge (step 11): Mr. Perfect holds the bridge, releases, and gets up through six
drawings; the receiver rolls off over Perfect's head and lies on Perfect's far side. Raw steps a stream entry
every 7 frames, and an entry is [bank, profile, x move, y move, draw x, draw y] (x moves and draw x count along
the actor's facing; draw offsets only shift the drawing). This tool:

- finds the bridge in the capture (Royal palette 2 equals the imported step-11 drawing, mirrored into Raw's
  facing) and the transform from Royal's screen to the attacker's actor coordinates;
- splits the frames after the release into Royal's drawings for each wrestler;
- matches each of Perfect's drawings to Raw's own get-up profiles (whose pieces in the imported slot are Royal
  art); a drawing no Raw profile shows exactly becomes a new Royal frame (tile addresses and object packing, as
  the Perfect-Plex frames);
- fits Raw's standing idle drawing to Royal's standing Perfect, which fixes how far the attacker's actor moves;
- fits Raw's own roll-off and lying profiles (the receiver's own art, here Raw's Undertaker) to Royal's
  Undertaker, which fixes how far the receiver's actor moves (lying keeps Raw's downed-action offsets, so
  the downed action continues the drawing without a jump). Raw keeps a standing wrestler more than 40 px from
  a downed one at the same depth and otherwise pushes one of them 7 px in depth; Royal's spacing is closer, so
  the receiver lies at Raw's minimum clearance instead (the difference is recorded).

    python3 tools/plan_perfect_plex_exit.py RAW_IMPORT.sfc ROYAL.sfc ROYAL_WRAM.bin ROYAL_CAPTURE_DIR \\
        [--output data/perfect-plex-exit.json] [--manifest editor/royal-import-layouts.js]

RAW_IMPORT is any ROM with Mr. Perfect added (his pieces hold Royal art); ROYAL_CAPTURE_DIR is the output of
tools/capture_royal_perfect_plex.py (every frame, with OAM/VRAM).
"""
import argparse
import hashlib
import json
from pathlib import Path

import royal_rumble_sprites as royal
from build_bret_gear import planar
from canonical_perfect_geometry import ROYAL_SHA256, paint, chunks_for, load_layouts, LAYOUTS, programs
from extract_oam import objects
from import_perfect_plex import actor_pixels, PAIR_SPACING
from raw_parts import resolve_part, raster, profile_parts

ROOT = Path(__file__).resolve().parents[1]
STEP_FRAMES = 7          # Raw advances the Perfect-Plex streams (actions 600/540) every 7 frames
HOLD_ENTRIES = 7         # held bridge entries after step 11 (Royal holds 56 frames: step 11 + 7 entries)
# Raw's own get-up (action 76 stream at $C0:06CA): profile, first part. Their pieces are Royal frames 70-79
# in the imported slot.
GETUP = [(0xC847BE, 60), (0xC847D6, 66), (0xC847E4, 69), (0xC847F2, 72)]
IDLE = (0xC84692, 30)            # Raw's standing idle (action 0 stream at $C0:050A)
IDLE_STREAM = 0x04050A           # [C84692, 0, 0, draw x, draw y]
ROLL = (0xC8489E, 117)           # Raw's roll-off after a suplex (end of the $C0:0808 stream)
LYING = (0xC8477C, 45)           # Raw's lying drawing
DOWNED_STREAM = 0x04067A         # the downed action's stream: [C8477C, 0, 0, draw x, draw y]
RECEIVER_SLOT = 2                # Raw's Undertaker, the receiver in the Royal capture
ATTACKER_PALETTE, RECEIVER_PALETTE = 2, 3   # Royal: Mr. Perfect (P1) and the Undertaker (P2)
STABLE = 30              # a drawing held this long ends the sequence (standing / lying)
# A downed actor collides with a standing one at the same depth when their x differ by 40 px or less ($80:E0D3);
# Raw then pushes one of them 7 px in depth ($80:DF2E). Royal lays the receiver 33 px from Perfect, so the receiver
# lies at least this far away instead and both stay on Royal's depth line.
DOWNED_CLEARANCE = 41


def sbyte(v):
    return v - 256 if v > 127 else v


def stream_entry(rom, at, address, first):
    entry = rom[at:at + 7]
    if entry[0] != 0xC8 or entry[1] | entry[2] << 8 != address & 0xFFFF or rom[at + 7] != 0xFF:
        raise ValueError(f'Unexpected Raw stream at {at:06x}')
    if profile_parts(rom, address)[0][0] != first:
        raise ValueError(f'Unexpected Raw profile {address:06x}')
    return [sbyte(v) for v in entry[3:7]]


def profile_points(rom, slot, address, flip=False):
    """Actor-relative pixels of a stock profile; a flipped actor shows unflipped column u at 7 - u."""
    out = {}
    for part, dx, dy in reversed(profile_parts(rom, address)):
        points = {}
        raster(resolve_part(rom, slot, part)['parts'], dx, dy, False, points)
        for (u, v), c in points.items():
            out[(7 - u if flip else u, v)] = c
    return out


def bbox(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def fit(target, points, radius=6):
    """Best translation of points onto target (IoU of opaque masks)."""
    t, p = set(target), set(points)
    a, b = bbox(t), bbox(p)
    cx, cy = (a[0] + a[2] - b[0] - b[2]) // 2, (a[1] + a[3] - b[1] - b[3]) // 2
    best = None
    for dx in range(cx - radius, cx + radius + 1):
        for dy in range(cy - radius, cy + radius + 1):
            moved = {(x + dx, y + dy) for x, y in p}
            score = len(moved & t) / len(moved | t)
            if best is None or score > best[0]:
                best = (score, dx, dy)
    return {'iou': round(best[0], 3), 'x': best[1], 'y': best[2]}


def segments(drawing, frames, stable=STABLE):
    """Runs of identical drawings until one lasts `stable` frames: [[first, last, points], ...].
    `drawing(f)` gives frame f's points; frames are read only as far as needed."""
    runs = []
    for f in frames:
        points = drawing(f)
        key = frozenset(points.items())
        if runs and runs[-1][3] == key:
            runs[-1][1] = f
        else:
            runs.append([f, f, points, key])
        if runs[-1][1] - runs[-1][0] + 1 >= stable:
            return [r[:3] for r in runs]
    raise ValueError('The capture ends before the drawing settles')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('raw', type=Path)
    parser.add_argument('royal', type=Path)
    parser.add_argument('royal_wram', type=Path)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/perfect-plex-exit.json')
    parser.add_argument('--manifest', type=Path, default=LAYOUTS)
    args = parser.parse_args()
    raw, source = args.raw.read_bytes(), args.royal.read_bytes()
    if hashlib.sha256(source).hexdigest() != ROYAL_SHA256:
        raise SystemExit('Expected the unmodified Royal Rumble USA ROM')
    if raw[0x70FE00:0x70FE13] != b'PERFECT-SLOT-PROTO1':
        raise SystemExit('RAW_IMPORT must have Mr. Perfect added')
    manifest = load_layouts() if args.manifest == LAYOUTS else json.loads(
        args.manifest.read_text().split('=', 1)[1].strip().rstrip(';'))
    capture = json.loads((args.capture / 'capture.json').read_text())
    frame_numbers = sorted(int(p.name[6:12]) for p in args.capture.glob('frame-*-oam.bin'))

    def prefix(f):
        return args.capture / f'frame-{f:06d}'

    # 1. The bridge: Royal's Perfect (facing left) mirrored onto the imported step-11 drawing.
    cache = {}
    bridge = paint(source, manifest['finisher'][11]['parts'], 112, (56, 100), False, cache)
    bridge = {(x - 56, y - 100): v for x in range(112) for y in range(112) if (v := bridge.getpixel((x, y)))}
    bridge_box = bbox(bridge)
    # The bridge lands with a bounce (the same drawing a few pixels lower); the hold is the last run of frames
    # showing it at one place, and the release is the frame after.
    matches = []
    for f in frame_numbers:
        pixels = actor_pixels(prefix(f), ATTACKER_PALETTE)
        if not pixels:
            continue
        box = bbox(pixels)
        place = (bridge_box[0] + box[2], box[1] - bridge_box[1])
        if {(place[0] - x, y - place[1]): v for (x, y), v in pixels.items()} == bridge:
            matches.append((f, place))
    if not matches:
        raise ValueError('The capture never shows the step-11 bridge')
    held = [matches[-1][0]]
    transform = matches[-1][1]
    for f, place in reversed(matches[:-1]):
        if f != held[0] - 1 or place != transform:
            break
        held.insert(0, f)
    a, b = transform
    release = held[-1] + 1

    def canonical(f, palette):
        return {(a - x, y - b): v for (x, y), v in actor_pixels(prefix(f), palette).items()}

    after = [f for f in frame_numbers if f >= release]
    perfect = segments(lambda f: canonical(f, ATTACKER_PALETTE), after)
    receiver = segments(lambda f: canonical(f, RECEIVER_PALETTE), after)

    # 2. Perfect's get-up drawings: Raw's own get-up profile where one shows the drawing exactly, else a Royal frame.
    for address, first in GETUP:
        if profile_parts(raw, address)[0][0] != first:
            raise ValueError(f'Unexpected Raw get-up profile {address:06x}')
    atlas = {bytes(32): None}
    for frame in royal.catalog(source, args.royal_wram.read_bytes(), 1):
        for part in frame['parts']:
            for ref in part['refs']:
                atlas.setdefault(planar(ref['pixels']), [ref['source'], int(ref['compressed']), ref['length']])
    steps, new_frames = [], []
    for first_frame, last_frame, target in perfect[:-1]:
        candidates = [(fit(target, profile_points(raw, 12, address)), address, part) for address, part in GETUP]
        best = max(candidates, key=lambda c: c[0]['iou'])
        step = {'royal_frames': [first_frame - release, last_frame - release]}
        if best[0]['iou'] == 1.0:
            step.update(profile=best[1], first_part=best[2], draw=[best[0]['x'], best[0]['y']])
        else:
            vram, oam = (Path(f'{prefix(first_frame)}-{n}.bin').read_bytes() for n in ('vram', 'oam'))
            regs = Path(f'{prefix(first_frame)}-registers.bin').read_bytes()
            obsel = regs[0x2101]
            base, select = (obsel & 3) << 14, ((obsel >> 3) & 3) << 13
            parts = []
            for rec, _ in objects(vram, oam, Path(f'{prefix(first_frame)}-cgram.bin').read_bytes(), obsel):
                if rec['palette'] != ATTACKER_PALETTE or rec['y'] >= 224:
                    continue
                n, attr, refs = rec['tile'] & 255, oam[rec['index'] * 4 + 3], []
                for y in range(rec['size'] // 8):
                    for x in range(rec['size'] // 8):
                        number = ((n & 0xF0) + y * 16 + ((n + x) & 15)) & 255
                        address = (base + (select + 8192 if attr & 1 else 0) + number * 32) & 65535
                        if vram[address:address + 32] not in atlas:
                            raise ValueError('A captured get-up tile has no verified Royal source')
                        refs.append(atlas[vram[address:address + 32]])
                # Mirrored into Raw's facing: the object's last column lands on the first.
                parts.append({'x': a - (rec['x'] + rec['size'] - 1), 'y': rec['y'] - b, 'size': rec['size'],
                              'hflip': not rec['hflip'], 'vflip': rec['vflip'], 'refs': refs})
            image = paint(source, parts, 112, (56, 100), False, cache)
            drawn = {(x - 56, y - 100): v for x in range(112) for y in range(112) if (v := image.getpixel((x, y)))}
            if drawn != target:
                raise ValueError('Rebuilt Royal get-up frame differs from the capture')
            step.update(frame=len(new_frames), draw=[0, 0], closest_raw=f'{best[1]:06x}', closest_iou=best[0]['iou'])
            new_frames.append({'source_frame': first_frame - release, 'parts': parts,
                               'chunks': chunks_for(image, 112, (56, 100))})
        steps.append(step)

    # 3. Standing: Raw's idle drawing, turned toward the receiver behind him, against Royal's standing Perfect
    # (lower body: the arm differs). The actor moves `forward` so the idle drawing lands on Royal's.
    idle_draw = stream_entry(raw, IDLE_STREAM, *IDLE)[2:]
    standing = perfect[-1][2]
    low = max(y for _, y in standing) - 40
    idle = profile_points(raw, 12, IDLE[0], flip=True)
    idle_low = max(y for _, y in idle) - 40
    stand_fit = fit({p: v for p, v in standing.items() if p[1] > low}, {p: v for p, v in idle.items() if p[1] > idle_low})
    forward = stand_fit['x'] + idle_draw[0]
    for step in steps:
        step['draw'][0] -= forward

    # 4. Receiver: roll off, then lie where Raw's downed action keeps drawing him (its own draw offsets).
    downed_draw = stream_entry(raw, DOWNED_STREAM, *LYING)[2:]
    lying_fit = fit(receiver[-1][2], profile_points(raw, RECEIVER_SLOT, LYING[0], flip=True))
    royal_receiver_x = lying_fit['x'] + downed_draw[0]      # actor x after the move (flipped: drawn at x - draw)
    receiver_x = min(royal_receiver_x, forward - DOWNED_CLEARANCE)
    roll = [r for r in receiver[:-1] if fit(r[2], profile_points(raw, RECEIVER_SLOT, ROLL[0], True))['iou'] > 0.95]
    if not roll:
        raise ValueError('No Royal receiver drawing matches Raw\'s roll-off')
    roll_fit = fit(roll[-1][2], profile_points(raw, RECEIVER_SLOT, ROLL[0], flip=True))
    roll_frames = (receiver[-1][0] - release)
    roll_entries = max(1, round(roll_frames / STEP_FRAMES))
    plan = {
        'about': __doc__.split('\n\n')[0],
        'royal_capture': capture,
        'transform': {'royal_to_attacker': [a, b], 'note': 'attacker actor coordinates = (a - x, y - b)'},
        'step_frames': STEP_FRAMES,
        'royal': {'bridge_first_shown': matches[0][0], 'bridge_held': [held[0], held[-1]], 'release': release,
                  'perfect': [[s[0] - release, s[1] - release] for s in perfect],
                  'receiver': [[s[0] - release, s[1] - release] for s in receiver]},
        'attacker': {'hold': HOLD_ENTRIES, 'forward': forward, 'steps': steps, 'frames': new_frames,
                     'standing': {'profile': IDLE[0], 'draw': idle_draw, 'royal_fit_lower_body': stand_fit,
                                  'vertical_difference': stand_fit['y'] - idle_draw[1]}},
        'receiver': {'hold': HOLD_ENTRIES, 'forward': PAIR_SPACING - receiver_x,
                     'royal_spacing': forward - royal_receiver_x, 'spacing': forward - receiver_x,
                     'clearance_adjustment': royal_receiver_x - receiver_x,
                     'steps': [{'profile': ROLL[0], 'first_part': ROLL[1], 'entries': roll_entries,
                                'draw': [receiver_x - roll_fit['x'], roll_fit['y']], 'royal_fit': roll_fit},
                               {'profile': LYING[0], 'first_part': LYING[1], 'entries': len(steps) - roll_entries,
                                'draw': downed_draw, 'royal_fit': lying_fit,
                                'vertical_difference': lying_fit['y'] - downed_draw[1]}]},
    }
    if plan['receiver']['steps'][1]['entries'] < 1:
        raise ValueError('The receiver needs at least one lying entry')
    args.output.write_text(json.dumps(plan, indent=1) + '\n')
    # The importer reads the exit from the manifest; the slot-12 worker serves the extra frames' IDs.
    manifest['exit'] = {k: plan[k] for k in ('attacker', 'receiver', 'step_frames')}
    manifest['programs'] = programs(len(manifest['finisher']) + len(new_frames))
    LAYOUTS.write_text('window.RAW_ROYAL_IMPORT_MANIFEST=' + json.dumps(manifest, separators=(',', ':')) + ';\n')
    print(json.dumps({'release': release, 'forward': forward, 'receiver_forward': plan['receiver']['forward'],
                      'steps': [{k: v for k, v in s.items() if k != 'royal_frames'} for s in steps],
                      'new_frames': len(new_frames), 'standing': stand_fit, 'roll': roll_fit, 'lying': lying_fit}))


if __name__ == '__main__':
    main()
