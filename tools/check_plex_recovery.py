"""Check that both wrestlers regain control after the Perfect-Plex, in Raw or Royal Rumble, from a capture.

The capture covers a recovery recipe (tools/recovery_bot.py): after the move, P2 mashes B while the receiver is
down, then P1 walks up and P2 walks down. Control is shown by the controls taking effect: during the walk each
wrestler's depth (y) moves the way his stick points. Raw also reports each actor's action numbers (0 standing,
70 down, 76 getting up; 14 and 16 walking up). Positions are read from WRAM; nothing is written.

    python3 tools/check_plex_recovery.py CAPTURE RECIPE --game raw|royal --first FRAME [--output OUT.json]

FRAME is the recipe frame of the capture's frame 1 (capture.json's first_recipe_frame for Royal captures).
"""
import argparse
import json
from collections import Counter
from pathlib import Path

ADDRESSES = {'raw': {'x': (0x5F0, 0x5F2), 'y': (0x600, 0x602), 'action': (0x6B4, 0x6B6)},
             'royal': {'x': (0x7F4, 0x7F6), 'y': (0x7F8, 0x7FA)}}
MOVED = 4   # px of depth a held direction must produce during the walk


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('capture', type=Path); p.add_argument('recipe', type=Path)
    p.add_argument('--game', choices=sorted(ADDRESSES), required=True)
    p.add_argument('--first', type=int, required=True)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    events = json.loads(a.recipe.read_text())['recovery']
    at = ADDRESSES[a.game]

    def state(frame):
        wram = (a.capture / f'frame-{frame - a.first + 1:06d}-wram.bin').read_bytes()
        word = lambda o: int.from_bytes(wram[o:o + 2], 'little')
        return {k: [word(o) for o in pair] for k, pair in at.items()}

    walk = events['walk_end'] - 24
    before, after = state(walk), state(events['walk_end'])
    report = {'game': a.game, 'events': events,
              'walk': {'frames': [walk, events['walk_end']], 'y_before': before['y'], 'y_after': after['y']},
              'positions_after_move': state(events['perfect_stands'])}
    checks = {'perfect_walks_up': after['y'][0] <= before['y'][0] - MOVED,
              'receiver_walks_down': after['y'][1] >= before['y'][1] + MOVED,
              'perfect_stands_before_receiver': events['perfect_stands'] < events['receiver_stands']}
    if a.game == 'raw':
        frames = range(events['both_down'], events['end'])
        runs = []
        for f in frames:
            actions = tuple(state(f)['action'])
            if not runs or runs[-1][1] != actions:
                runs.append([f, actions])
        report['actions'] = [[f - events['both_down'], list(acts)] for f, acts in runs]
        receiver = [acts[1] for _, acts in runs]
        checks['receiver_down_then_up'] = 70 in receiver and 76 in receiver and receiver.index(70) < receiver.index(76)
        checks['perfect_never_down_after_move'] = not {acts[0] for _, acts in runs} & {70, 72, 76}
        report['walk']['actions'] = dict(Counter(str(tuple(state(f)['action'])) for f in range(walk, events['walk_end'])))
    report['checks'], report['pass'] = checks, all(checks.values())
    text = json.dumps(report, indent=1)
    if a.output:
        a.output.write_text(text + '\n')
    print(text)
    if not report['pass']:
        raise SystemExit('Recovery check failed: ' + ', '.join(k for k, v in checks.items() if not v))


if __name__ == '__main__':
    main()
