"""Summarise both workers' state from a capture's WRAM dumps as runs of unchanged values.

Fields per frame: action ($06B4/$06B6), x ($05F0/$05F2) and health ($0A78/$0A7A). Read-only.

    python3 tools/trace_actor_state.py CAPTURE_DIR [--output JSON]
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    runs, last = [], None
    for path in sorted(args.capture.glob('frame-*-wram.bin')):
        wram = path.read_bytes()
        w = lambda a: int.from_bytes(wram[a:a + 2], 'little')
        frame = int(path.name.split('-')[1])
        actions = (w(0x6b4), w(0x6b6))
        health = (w(0xa78), w(0xa7a))
        if (actions, health) != last:
            runs.append({'frame': frame, 'actions': list(actions), 'health': list(health), 'x': [w(0x5f0), w(0x5f2)]})
            last = (actions, health)
        runs[-1]['until'] = frame
        runs[-1]['x_end'] = [w(0x5f0), w(0x5f2)]
    text = json.dumps(runs, indent=1)
    if args.output:
        args.output.write_text(text + '\n')
    for run in runs:
        print(run['frame'], run['until'], 'actions', run['actions'], 'health', run['health'], 'x', run['x'], '->', run['x_end'])


if __name__ == '__main__':
    main()
