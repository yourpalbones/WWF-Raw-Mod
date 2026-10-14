"""Compose controller-only Perfect-Plex recipes from the committed v0.16 replay.

Every scenario is derived from evidence/mr-perfect-import/controller-replay.json
with three deterministic edits:

1. P2 selection: the replay's two P2 Right presses (5451, 5551) become `rights`
   presses 100 frames apart. P2's A press moves accordingly, and every later
   input shifts by (rights - 2) * 100 frames.
2. Damage: the replay's last full damage cycle (1,380 frames) is repeated
   `cycles` more times, so the chosen receiver is in the red before the final R block.
3. Tail (optional): inputs from frame `cut` onward are replaced by
   scenario-specific presses. Their frames are relative to `cut`; they reposition
   both wrestlers (P2 included) and then grab and press R.

Inputs are joypad presses only: [port, start_frame, button, duration].
Buttons: 0 B, 4 Up, 5 Down, 6 Left, 7 Right, 9 X, 11 R.

    python3 tools/compose_perfect_recipes.py            # (re)write evidence/perfect-plex-receivers/recipes/*.json
    python3 tools/compose_perfect_recipes.py --check    # fail if committed recipes differ
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'evidence/mr-perfect-import/controller-replay.json'
OUT = ROOT / 'evidence/perfect-plex-receivers/recipes/previous-builds'   # composed for the earlier builds' timing
CYCLE = (13571, 14951)          # last full damage cycle in the base replay
SELECTION_RIGHTS = (5451, 5551)
SELECTION_A = 5750
RECORDED = ('defect_baseline', 'expected_build', 'expected')


def r_block(start):
    return [[0, start + 30 * k, 11, 20] for k in range(9)]


def compose(rights, cycles, cut=None, tail=None):
    base = json.loads(BASE.read_text())
    delta = (rights - 2) * 100
    inputs = []
    for port, start, button, duration in base['inputs']:
        if port == 1 and start in SELECTION_RIGHTS:
            continue
        if port == 1 and start == SELECTION_A:
            start = 5451 + 100 * rights + 99
        elif start > SELECTION_A:
            start += delta
        inputs.append([port, start, button, duration])
    inputs += [[1, 5451 + 100 * j, 7, 8] for j in range(rights)]
    lo, hi = CYCLE[0] + delta, CYCLE[1] + delta
    block = [i for i in inputs if lo <= i[1] < hi]
    inputs = [i if i[1] < hi else [i[0], i[1] + cycles * (hi - lo), i[2], i[3]] for i in inputs]
    for j in range(1, cycles + 1):
        inputs += [[p, s + j * (hi - lo), b, d] for p, s, b, d in block]
    if cut is not None:
        inputs = [i for i in inputs if i[1] < cut] + [[p, s + cut, b, d] for p, s, b, d in tail]
    inputs.sort(key=lambda i: (i[1], i[0], i[2]))
    return inputs


# Undertaker (slot 2) scenarios. Tail frames are relative to frame 19300 of the
# 3-cycle Undertaker recipe, where Perfect idles at x=314 and Undertaker is dazed at x=344.
UNDERTAKER_CUT = 19300
SCENARIOS = {
    'undertaker-attacker-left-right-rope': dict(rights=5, cycles=3, receiver_slot=2,
        note='Base replay geometry: attacker on the left, receiver against the right rope.'),
    'undertaker-attacker-right-right-rope': dict(rights=5, cycles=3, receiver_slot=2, cut=UNDERTAKER_CUT,
        tail=[[0, 1, 5, 40], [0, 41, 7, 90], [0, 131, 4, 40], [0, 181, 6, 1], [0, 207, 9, 8]] + r_block(297),
        note='Perfect walks below and around to the receiver\'s right, against the right rope; opposite facing.'),
    'undertaker-attacker-left-left-rope': dict(rights=5, cycles=3, receiver_slot=2, cut=UNDERTAKER_CUT,
        tail=[[0, 1, 6, 560], [1, 190, 6, 500], [0, 705, 7, 1], [0, 731, 9, 8]] + r_block(821),
        note='Both walk left; Perfect against the left rope with the receiver on his right.'),
    'undertaker-attacker-right-left-rope': dict(rights=5, cycles=3, receiver_slot=2, cut=UNDERTAKER_CUT,
        tail=[[1, 190, 6, 450], [0, 1, 5, 40], [0, 300, 6, 80], [0, 420, 4, 40], [0, 500, 6, 1],
              [0, 526, 9, 8]] + r_block(616),
        note='Receiver against the left rope with Perfect on his right; opposite facing.'),
    'undertaker-attacker-left-mid-ring': dict(rights=5, cycles=3, receiver_slot=2, cut=UNDERTAKER_CUT,
        tail=[[0, 1, 6, 60], [1, 190, 6, 60], [0, 300, 7, 1], [0, 326, 9, 8]] + r_block(416),
        note='Mid-ring control away from both ropes.'),
    # Other direct counterparts, base geometry. P2 needs 2 * slot + 1 Right presses in this replay.
    'bret-attacker-left-right-rope': dict(rights=3, cycles=3, receiver_slot=1, note='Bret Hart receiving.'),
    'yokozuna-attacker-left-right-rope': dict(rights=7, cycles=0, receiver_slot=3, note='Yokozuna receiving.'),
    'razor-attacker-left-right-rope': dict(rights=11, cycles=0, receiver_slot=5,
        note='Razor Ramon slot (user-edited Scott Hall gear is not in this unmodified base) receiving.'),
    'lex-attacker-left-right-rope': dict(rights=13, cycles=2, receiver_slot=6, note='Lex Luger receiving.'),
    'shawn-attacker-left-right-rope': dict(rights=17, cycles=0, receiver_slot=8, note='Shawn Michaels receiving.'),
}
# First frame of attacker action 600 when the recipe is replayed on the measured build (see
# docs/perfect-plex-native-trace.md). Captures start 150 frames earlier and last 400 frames.
MOVE_START = {
    'undertaker-attacker-left-right-rope': 19721, 'undertaker-attacker-right-right-rope': 19837,
    'undertaker-attacker-left-left-rope': 20365, 'undertaker-attacker-right-left-rope': 20160,
    'undertaker-attacker-left-mid-ring': 19930, 'bret-attacker-left-right-rope': 19521,
    'yokozuna-attacker-left-right-rope': 15781, 'razor-attacker-left-right-rope': 16151,
    'lex-attacker-left-right-rope': 19111, 'shawn-attacker-left-right-rope': 16751,
}
# Slot 12 (Mr. Perfect receiving) is unreachable here: P2 cannot pick the wrestler P1 already chose.


def recipes():
    out = {}
    for name, s in SCENARIOS.items():
        inputs = compose(s['rights'], s['cycles'], s.get('cut'), s.get('tail'))
        last = max(start + duration for _, start, _, duration in inputs)
        out[name] = {'scenario': name, 'receiver_slot': s['receiver_slot'], 'note': s['note'],
                     'composed_by': 'tools/compose_perfect_recipes.py',
                     'parameters': {k: s[k] for k in ('rights', 'cycles', 'cut') if k in s},
                     'controller_only': True, 'frames': last + 900,
                     'move_start': MOVE_START[name], 'capture_from': MOVE_START[name] - 150, 'capture_frames': 400,
                     'inputs': inputs}
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    stale = []
    for name, recipe in recipes().items():
        path = OUT / f'{name}.json'
        old = json.loads(path.read_text()) if path.exists() else {}
        for key in RECORDED:   # written by tools/verify_perfect_receivers_native.py (--record keeps the old baseline)
            if key in old:
                recipe[key] = old[key]
        text = json.dumps(recipe, indent=1) + '\n'
        if args.check:
            if not path.exists() or path.read_text() != text:
                stale.append(path.name)
        else:
            path.write_text(text)
    if stale:
        sys.exit('Stale recipes: ' + ', '.join(stale))
    print(f'{len(SCENARIOS)} recipes', 'up to date' if args.check else 'written')
