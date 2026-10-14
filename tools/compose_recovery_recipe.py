"""Extend a Perfect-Plex controller recipe past the move to show recovery (PP-4).

The base recipe's inputs are kept unchanged up to the move, so the run is frame-identical until then. After
the receiver is down, player 1 walks away and back and then attacks, so the capture shows the receiver's own
downed/get-up art and both workers acting again. Controller presses only (libretro ids: B=0, Y=1, LEFT=6,
RIGHT=7).

    python3 tools/compose_recovery_recipe.py BASE.json OUT.json
"""
import argparse
import json
from pathlib import Path

B, Y, LEFT, RIGHT = 0, 1, 6, 7


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('base', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--after', type=int, default=330, help='frames after move_start before P1 moves')
    args = parser.parse_args()
    recipe = json.loads(args.base.read_text())
    start = recipe['move_start'] + args.after
    away, back = (LEFT, RIGHT) if 'attacker-left' in recipe['scenario'] else (RIGHT, LEFT)
    extra = [[0, start, away, 40], [0, start + 60, back, 50]]
    extra += [[0, start + 130 + i * 40, (Y, B)[i % 2], 6] for i in range(10)]
    extra += [[0, start + 560, back, 60], [0, start + 640, away, 60]]
    recipe.update({
        'scenario': recipe['scenario'] + '-recovery',
        'note': recipe['note'] + ' Extended after the move: P1 walks away and back, then attacks (PP-4 recovery).',
        'composed_by': 'tools/compose_recovery_recipe.py',
        'base_recipe': args.base.name,
        'frames': start + 760,
        'capture_frames': start + 760 - recipe['capture_from'],
        'inputs': recipe['inputs'] + extra,
    })
    for key in ('expected', 'expected_build', 'defect_baseline'):
        recipe.pop(key, None)
    args.output.write_text(json.dumps(recipe, indent=1) + '\n')


if __name__ == '__main__':
    main()
