"""Compare the editor's paired Perfect-Plex preview with native gameplay screenshots.

For each of the move's 12 steps, takes the middle native frame showing that step (from a measurement made by
tools/measure_perfect_pair.py on a kept capture) and renders the same step with tools/preview_points.js.
The exit's steps (held pin, release, recovery: docs/perfect-plex-exit.md):
- The held pin entries follow step 11 every 7 frames; each is checked on the sixth frame of its 7 (step 11 lands
  with a short bounce).
- The release entries are found where Mr. Perfect's drawing changes on screen, so frames the game drops do not
  shift them; each is checked in the middle of its run.
- The preview's last step (Perfect standing, the receiver down) is checked 30 frames into the standing run.
- Raw's camera follows the pair and shakes when the bridge lands (WRAM $2E/$30 hold its x/y); the comparison
  follows it. A frame's OAM was built with the previous frame's camera; while the camera pans, the sprites'
  scroll can trail by a pixel, so then the best of +-1 px is taken and recorded as 'pan_shift'.
- Each wrestler is compared at his actual position. Where the game moved an actor away from the planned
  position (the ring edge stopping the receiver, Raw's collision rule pushing someone in depth), the preview is
  shifted by that amount, so the drawings are still checked; the deviation is reported per step.
The native side is rebuilt from that frame's OAM and VRAM: only the two actors' objects (palettes 0 and 1),
in OAM priority order, so background layers drawn over sprites (the ring ropes) and other sprites (the
referee) do not count. A preview pixel matches when the native actor pixel at that screen position has the
same palette index. Nothing in the preview is adjusted to match.

    python3 tools/check_preview_native.py ROM RECEIVER_SLOT MEASUREMENT.json CAPTURE_DIR left|right
"""
import argparse
import json
import subprocess
from pathlib import Path
from PIL import Image
from measure_perfect_pair import oam_indices
from extract_oam import objects

ROOT = Path(__file__).resolve().parents[1]


def word(data, at):
    return int.from_bytes(data[at:at + 2], 'little')


def stream_moves(rom, base):
    """x moves of a stream's entries ([bank, profile, x move, ...] until FF)."""
    out = []
    while rom[base] != 0xFF and len(out) < 40:
        out.append(rom[base + 3] - 256 if rom[base + 3] > 127 else rom[base + 3])
        base += 7
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('rom', type=Path); p.add_argument('receiver', type=int); p.add_argument('measurement', type=Path)
    p.add_argument('capture', type=Path); p.add_argument('facing', choices=['left', 'right'])
    a = p.parse_args()
    rom = a.rom.read_bytes()
    rows = [r for r in json.loads(a.measurement.read_text())['rows'] if 'camera_x' in r]
    plan = json.loads(subprocess.check_output(['node', str(ROOT / 'tools/preview_points.js'), str(a.rom),
                                               str(a.receiver), 'plan', a.facing]))
    held = [r for r in rows if r['attacker_pose'] == 11 and r['receiver_pose'] == 11]
    first, hold = held[0]['frame'], plan.count('pin')
    settled = [r for r in held if r['frame'] <= first + 7 * hold][-1]   # before the release entry moves the actors
    wram = lambda f: Path(f'{a.capture}/frame-{f:06d}-wram.bin').read_bytes()
    oam_path = lambda f: Path(f'{a.capture}/frame-{f:06d}-oam.bin')
    # Planned x moves along each actor's facing (the attacker faces the receiver at the start of the move).
    own = int.from_bytes(rom[0x71d040 + a.receiver * 3:0x71d040 + a.receiver * 3 + 3], 'little')
    moves = {'attacker': stream_moves(rom, 0x730000),
             'receiver': stream_moves(rom, own if own else 0x735000)}
    facing = {'attacker': 1 if a.facing == 'left' else -1, 'receiver': -1 if a.facing == 'left' else 1}
    planned = lambda actor, k: facing[actor] * sum(moves[actor][:k + 1])

    def signature(f):
        """Mr. Perfect's objects, independent of camera position and OAM order."""
        oam = oam_path(f).read_bytes()
        objs = [(oam[i * 4] | (oam[512 + i // 4] >> (2 * (i % 4)) & 1) << 8, oam[i * 4 + 1], oam[i * 4 + 2], oam[i * 4 + 3])
                for i in range(128) if (oam[i * 4 + 3] >> 1 & 7) == 0 and oam[i * 4 + 1] < 224]
        if not objs:
            return None
        x0, y0 = min(o[0] for o in objs), min(o[1] for o in objs)
        return tuple(sorted((x - x0, y - y0, t, at) for x, y, t, at in objs))

    # Runs of Mr. Perfect's drawing from the release (the frame after the last step-11 frame) on.
    runs, f = [], held[-1]['frame'] + 1
    while oam_path(f).exists() and len(runs) < 8:
        sig = signature(f)
        if runs and runs[-1][2] == sig:
            runs[-1][1] = f
        else:
            runs.append([f, f, sig])
        f += 1
    release = [r for r in runs if r[1] - r[0] >= 3]   # skip one-frame transitions
    result = []
    for k in range(len(plan)):
        if k < 12:
            cand = [r for r in rows if r['attacker_pose'] == k and r['receiver_pose'] == k and
                    (k < 11 or r['frame'] < first + 7)]
            r = cand[len(cand) // 2]
            frame = r['frame']
        else:
            r = settled
            n = k - 12 - hold
            if n < 0:
                frame = first + 7 * (k - 11) + 5
            elif n < len(release):
                run = release[n]
                frame = run[0] + (min(30, run[1] - run[0]) if k == len(plan) - 1 else (run[1] - run[0] + 1) // 2)
            else:
                frame = None
        if frame is None or not oam_path(frame).exists():
            result.append({'step': k + 1, 'label': plan[k], 'frame': frame, 'pixels': 0, 'matching': 0})
            continue
        pts = json.loads(subprocess.check_output(['node', str(ROOT / 'tools/preview_points.js'), str(a.rom),
                                                  str(a.receiver), str(k), a.facing]))
        prefix = a.capture / f"frame-{frame:06d}"
        vram, oam, cgram, regs = (Path(f'{prefix}-{n}.bin').read_bytes() for n in ('vram', 'oam', 'cgram', 'registers'))
        native, owner = {}, {}
        for rec, _ in sorted(objects(vram, oam, cgram, regs[0x2101]), key=lambda o: -o[0]['index']):
            if rec['palette'] in (0, 1) and rec['y'] < 224:
                for (x, y), v in oam_indices(vram, oam, rec, regs[0x2101]).items():
                    native[rec['x'] + x, rec['y'] + y] = v
        # Screen offset from the preview canvas (camera at the previous frame, as the OAM was built then).
        before, now = wram(r['frame'] - 1), wram(frame - 1)
        dx = r['attacker_origin_screen'] - (108 if a.facing == 'left' else 148) + word(before, 0x2E) - word(now, 0x2E)
        dy = r['vertical']['attacker_origin_y'] - 150 + word(before, 0x30) - word(now, 0x30)
        # Each actor's deviation from the planned position (ring edge, collision push), from WRAM.
        deviation = {}
        for actor, off in (('attacker', 0), ('receiver', 2)):
            step = min(k, len(moves[actor]) - 1) if k < len(plan) - 1 else len(moves[actor]) - 1
            moved = word(now, 0x5F0 + off) - word(before, 0x5F0 + off)
            deviation[actor] = (moved - (planned(actor, step) - planned(actor, 11)) if k >= 12 else 0,
                                word(now, 0x600 + off) - word(before, 0x600 + off) if k >= 12 else 0)
        final = {}
        for x, y, R, G, B, actor, v in pts:
            ddx, ddy = deviation[actor]
            final[(x + ddx, y + ddy)] = v
        panning = k >= 12 and len({word(wram(g), 0x2E) for g in range(frame - 3, frame + 1)}) > 1
        best = None
        for shift in ((0, -1, 1) if panning else (0,)):
            match = sum(native.get((x + dx + shift, y + dy)) == v for (x, y), v in final.items())
            if best is None or match > best[0]:
                best = (match, shift)
        match, shift = best
        # Native actor pixels the preview does not draw (a missing or misplaced drawing).
        extra = sum(1 for (x, y) in native if (x - dx - shift, y - dy) not in final)
        entry = {'step': k + 1, 'label': plan[k], 'frame': frame, 'pixels': len(final), 'matching': match,
                 'native_only': extra}
        if shift:
            entry['pan_shift'] = shift
        if any(deviation[actor] != (0, 0) for actor in deviation):
            entry['deviation'] = {actor: list(v) for actor, v in deviation.items()}
        result.append(entry)
    ratio = lambda s: round(s['matching'] / max(s['pixels'] + s.get('native_only', 0), 1), 3)
    print(json.dumps({'receiver': a.receiver, 'facing': a.facing, 'match_ratio': [ratio(s) for s in result[:12]],
                      'exit_match_ratio': [ratio(s) for s in result[12:]],
                      'deviations': {s['step']: s['deviation'] for s in result if 'deviation' in s}, 'steps': result}))


if __name__ == '__main__':
    main()
