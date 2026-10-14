"""Extend a Perfect-Plex recipe until both wrestlers have regained control, with the same rule in either game.

After the recipe's own inputs (the move), the bot plays both controllers frame by frame:
1. nothing until the move has put both wrestlers on the mat (both below STANDING) and Mr. Perfect stands
   again (his objects at least STANDING px tall for SETTLE frames);
2. then P2 mashes B (2 frames on, 2 off) while the receiver is down, and stops as soon as he starts to rise
   (objects at least RISING px tall: in Raw, B pressed during the get-up makes him strike a pose once up);
3. once he stands, nothing for IDLE frames; then P1 walks up and P2 walks down for WALK frames (both answer
   the controls), then TAIL idle frames.
It reads only OAM (each wrestler's object palette) to decide; nothing is written to emulator memory. The
output is the recipe with the recorded presses appended, replayable from a cold boot with the same tools as
the input recipe.

    python3 tools/recovery_bot.py CORE ROM RECIPE --game raw|royal --state STATE --base FRAME --output OUT.json

STATE is a save state at recipe frame BASE, made by replaying the recipe (tools/run_controller_recipe.py for
Raw, tools/capture_royal_perfect_plex.py for Royal: its pre/ state). The recipe's own presses after BASE are
replayed first (a press held across BASE keeps being held, as in tools/run_controller_recipe.py).
"""
import argparse
import json
from pathlib import Path

from libretro_step import Emulator
from recipe_bot import Recorder

B, UP, DOWN = 0, 4, 5
PALETTES = {'raw': (0, 1), 'royal': (2, 3)}     # (Mr. Perfect, receiver) object palettes
STANDING, RISING, SETTLE, IDLE, WALK, TAIL, LIMIT = 64, 45, 8, 30, 24, 60, 1500


def heights(oam, obsel, palettes):
    """Vertical extent of each palette's on-screen objects."""
    small, large = [(8, 16), (8, 32), (8, 64), (16, 32), (16, 64), (32, 64)][obsel >> 5]
    out = {}
    for i in range(128):
        x, y, tile, attr = oam[i * 4:i * 4 + 4]
        high = oam[512 + i // 4] >> (2 * (i % 4)) & 3
        size = large if high & 2 else small
        if y >= 224 and y + size <= 256:
            continue
        top = y - 256 if y >= 224 else y
        palette = attr >> 1 & 7
        if palette in palettes:
            lo, hi = out.get(palette, (999, -999))
            out[palette] = (min(lo, top), max(hi, top + size))
    return [out[p][1] - out[p][0] if p in out else 0 for p in palettes]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('core', type=Path)
    parser.add_argument('rom', type=Path)
    parser.add_argument('recipe', type=Path)
    parser.add_argument('--game', choices=sorted(PALETTES), required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--base', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    recipe = json.loads(args.recipe.read_text())
    last = max(start + duration - 1 for _, start, _, duration in recipe['inputs'])

    def scripted(k):
        return {port: {b for p, start, b, duration in recipe['inputs'] if p == port and start <= k < start + duration}
                for port in (0, 1)}
    emu = Emulator(args.core, args.rom, state=args.state)
    recorder, k = Recorder(), args.base
    events, phase, count, walked = {}, 'move', 0, 0
    while k < args.base + LIMIT:
        att, rcv = heights(emu.memory(0x10011), emu.memory(0x10012)[0x2101], PALETTES[args.game])
        held = {0: set(), 1: set()}
        if k + 1 <= last:
            held = scripted(k + 1)
        elif phase == 'move':
            if att < STANDING and rcv < STANDING:
                events['both_down'], phase = k, 'attacker'
        elif phase == 'attacker':
            count = count + 1 if att >= STANDING else 0
            if count >= SETTLE:
                events['perfect_stands'], phase, count = k - SETTLE, 'receiver', 0
        elif phase == 'receiver':
            count = count + 1 if rcv >= STANDING else 0
            if count >= SETTLE:
                events['receiver_stands'], phase = k - SETTLE, 'idle'
            elif rcv < RISING and k % 4 < 2:
                held[1].add(B)
        elif phase == 'idle':
            if k >= events['receiver_stands'] + SETTLE + IDLE:
                phase = 'walk'
        elif phase == 'walk':
            held = {0: {UP}, 1: {DOWN}}
            walked += 1
            if walked == WALK:
                events['walk_end'], phase = k + 1, 'tail'
        elif k >= events['walk_end'] + TAIL:
            break
        k += 1
        recorder.frame(k, held)
        emu.step(held)
    else:
        raise SystemExit(f'Gave up in phase {phase} at frame {k}')
    out = dict(recipe)
    added = [p for p in recorder.close(k + 1) if p[1] > last]
    out['inputs'] = recipe['inputs'] + added
    out['recovery'] = {'composed_by': 'tools/recovery_bot.py', 'game': args.game, 'base': args.base,
                       'rule': 'once Perfect stands, P2 mashes B until the receiver starts to rise; once he stands and '
                               f'{IDLE} frames pass, P1 walks up and P2 walks down for {WALK} frames',
                       **events, 'end': k}
    for key in ('frames', 'frames_from_match'):
        if key in out:
            out[key] = k
    args.output.write_text(json.dumps(out) + '\n')
    print(json.dumps(out['recovery']))


if __name__ == '__main__':
    main()
