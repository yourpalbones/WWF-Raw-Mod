"""Build a controller-only Perfect-Plex recipe against any receiver with a small rule-based player.

The bot replays the committed v0.16 selection inputs (P2 picks the receiver with 2 * slot + 1 Right presses),
then plays P1 frame by frame: approach the opponent from the chosen side, grapple (X), mash B for moves,
and after each exchange grapple again and press R. It stops once P1's Perfect-Plex starts (action 600).
Memory is only READ to choose the next press; nothing is written. The output is an ordinary fixed input
list (tools/run_controller_recipe.py replays it frame-identically from a cold boot).

    python3 tools/recipe_bot.py CORE ROM --slot 0 --side left --output RECIPE.json [--max-frames 40000]
"""
import argparse
import json
from pathlib import Path

from compose_perfect_recipes import compose, CYCLE
from libretro_step import Emulator

B, UP, DOWN, LEFT, RIGHT, X, R = 0, 4, 5, 6, 7, 9, 11
PLEX = 600


def word(w, a):
    return w[a] | w[a + 1] << 8


def state(w):
    return {'action': (word(w, 0x6B4), word(w, 0x6B6)), 'x': (word(w, 0x5F0), word(w, 0x5F2)),
            'y': (word(w, 0x600), word(w, 0x602)), 'health': (word(w, 0xA78), word(w, 0xA7A))}


class Recorder:
    """Frame-level held buttons -> merged [port, start, button, duration] presses."""

    def __init__(self):
        self.open, self.presses = {}, []

    def frame(self, k, held):
        for port, buttons in held.items():
            for b in buttons:
                if (port, b) not in self.open:
                    self.open[(port, b)] = k
        for (port, b), start in list(self.open.items()):
            if b not in held.get(port, ()):
                self.presses.append([port, start, b, k - start])
                del self.open[(port, b)]

    def close(self, k):
        self.frame(k, {0: set(), 1: set()})
        return sorted(self.presses, key=lambda p: (p[1], p[0], p[2]))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('core'); p.add_argument('rom')
    p.add_argument('--slot', type=int, required=True)
    p.add_argument('--side', choices=['left', 'right'], default='left', help='P1 (Perfect) side of the receiver')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-frames', type=int, default=40000)
    p.add_argument('--debug', action='store_true')
    a = p.parse_args()
    rights = 2 * a.slot + 1
    setup_end = CYCLE[0] + (rights - 2) * 100
    setup = [i for i in compose(rights, 0) if i[1] + i[3] <= setup_end]
    emu = Emulator(a.core, a.rom)
    rec = Recorder()
    move_start = None
    plan = []          # queued (frames, held) actions
    phase, tries, after = 'approach', 0, 0
    for k in range(1, a.max_frames + 1):
        if k < setup_end:
            held = {0: {b for port, s, b, d in setup if port == 0 and s <= k < s + d},
                    1: {b for port, s, b, d in setup if port == 1 and s <= k < s + d}}
        else:
            w = emu.wram()
            st = state(w)
            if a.debug and k % 300 == 0:
                print(k, st, tries, plan[:1], flush=True)
            if move_start is None and st['action'][0] == PLEX:
                move_start = k - 1
            if move_start is not None:
                held = {0: set(), 1: set()}
                after += 1
                if after > 600:
                    break
            elif plan:
                frames, held = plan[0]
                plan[0] = (frames - 1, held)
                if plan[0][0] <= 0:
                    plan.pop(0)
            else:
                (x1, x2), (y1, y2) = st['x'], st['y']
                want = x2 - 36 if a.side == 'left' else x2 + 36
                walking = (0, 2, 4, 6, 8)
                idle = st['action'][0] in walking and st['action'][1] in walking
                if st['action'][1] not in walking:
                    # The receiver is down or busy: P1 waits; P2 mashes to get up (controller input only).
                    plan = [(4, {0: set(), 1: {(B, 1, 8)[(k // 4) % 3]}}), (4, {0: set(), 1: set()})]
                elif st['action'][0] not in walking:
                    plan = [(8, {0: set(), 1: set()})]
                elif abs(x1 - want) > 3 or abs(y1 - y2) > 8:
                    dirs = set()
                    if x1 < want - 3:
                        dirs.add(RIGHT)
                    elif x1 > want + 3:
                        dirs.add(LEFT)
                    if y1 < y2 - 8:
                        dirs.add(DOWN)
                    elif y1 > y2 + 8:
                        dirs.add(UP)
                    plan = [(4, {0: dirs, 1: set()})]
                elif idle:
                    # Face the opponent, grapple, then either mash moves or try the finisher.
                    face = RIGHT if a.side == 'left' else LEFT
                    plan = [(1, {0: {face}, 1: set()}), (25, {0: set(), 1: set()}), (8, {0: {X}, 1: set()}),
                            (82, {0: set(), 1: set()})]
                    if tries % 2:
                        plan += [(20, {0: {R}, 1: set()}), (10, {0: set(), 1: set()})] * 9
                    else:
                        plan += [(20, {0: {B}, 1: set()}), (10, {0: set(), 1: set()})] * 8
                    plan += [(120, {0: set(), 1: set()})]
                    tries += 1
                else:
                    plan = [(10, {0: set(), 1: set()})]
                held = plan[0][1]
        rec.frame(k, held)
        emu.step(held)
    inputs = rec.close(emu.frame + 1)
    if move_start is None:
        raise SystemExit(f'No Perfect-Plex within {a.max_frames} frames (tries {tries})')
    recipe = {'scenario': a.output.stem, 'receiver_slot': a.slot, 'composed_by': 'tools/recipe_bot.py',
              'note': f'Bot-played: P2 selects slot {a.slot}; P1 grapples from the {a.side} until the Perfect-Plex starts.',
              'parameters': {'rights': rights, 'side': a.side, 'setup_end': setup_end},
              'controller_only': True, 'frames': move_start + 600, 'move_start': move_start,
              'capture_from': move_start - 150, 'capture_frames': 400, 'inputs': inputs}
    a.output.write_text(json.dumps(recipe, indent=1) + '\n')
    print(json.dumps({'slot': a.slot, 'move_start': move_start, 'tries': tries, 'presses': len(inputs)}))


if __name__ == '__main__':
    main()
