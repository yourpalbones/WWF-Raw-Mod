"""Run tools/run_headless.py from a committed controller-only recipe file.

Recipe JSON keys: frames, interval, inputs ([port, start_frame, button, duration]),
optional snapshots. No emulator memory is written; inputs are joypad presses only.

    python3 tools/run_controller_recipe.py CORE ROM RECIPE --output DIR [--from-state STATE --base FRAME]

With --from-state, inputs at or before --base are skipped and later ones are
shifted so that frame BASE+1 of the recipe becomes frame 1 of the new run.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('core', type=Path)
parser.add_argument('rom', type=Path)
parser.add_argument('recipe', type=Path)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--from-state', type=Path)
parser.add_argument('--base', type=int, default=0)
parser.add_argument('--frames', type=int)
parser.add_argument('--interval', type=int)
args = parser.parse_args()
recipe = json.loads(args.recipe.read_text())
frames = args.frames or recipe['frames'] - args.base
interval = args.interval or recipe.get('interval', frames)
command = [sys.executable, str(ROOT / 'tools/run_headless.py'), str(args.core), str(args.rom),
           '--output', str(args.output), '--frames', str(frames), '--interval', str(interval)]
if args.from_state:
    command += ['--load-state', str(args.from_state)]
for frame in recipe.get('snapshots', []):
    if 0 < frame - args.base <= frames:
        command += ['--snapshot-frame', str(frame - args.base)]
for port, start, button, duration in recipe['inputs']:
    start -= args.base
    if 1 <= start <= frames:
        command += ['--press-p2' if port else '--press', f'{start}:{button}:{duration}']
subprocess.run(command, check=True)
