"""Capture Royal Rumble's Perfect-Plex and its aftermath from cold boot, with controller input only.

Replays the verified source match (data/royal-perfect-source-capture.json, checked against its snapshot
hashes), then a Royal recipe from the match state: Mr. Perfect (P1) performs the Perfect-Plex on the
Undertaker (P2), plus any later inputs the recipe holds (getting up, walking). Every frame from --start is
captured (PNG, WRAM, VRAM, OAM, CGRAM, registers), and capture.json records which recipe frame each capture
frame is. Nothing is written to emulator memory. Captures stay local.

    python3 tools/capture_royal_perfect_plex.py CORE ROYAL.sfc --output DIR \\
        [--recipe evidence/perfect-plex-exit/recipes/royal.json] [--start FRAME] [--frames N]

--start defaults to 10 frames before the recipe's move_start; --frames to the rest of the recipe.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/royal-perfect-source-capture.json'


def run(core, rom, output, frames, interval, state, inputs, base=0, env=None):
    command = [sys.executable, str(ROOT / 'tools/run_headless.py'), str(core), str(rom), '--output', str(output),
               '--frames', str(frames), '--interval', str(interval)]
    if state:
        command += ['--load-state', str(state)]
    for port, start, button, duration in inputs:
        start -= base
        if start < 1 <= start + duration - 1:      # held across the saved state: keep holding
            start, duration = 1, start + duration - 1
        if 1 <= start <= frames:
            command += ['--press-p2' if port else '--press', f'{start}:{button}:{duration}']
    subprocess.run(command, env=env, check=True, stdout=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('core', type=Path)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--recipe', type=Path, default=ROOT / 'evidence/perfect-plex-exit/recipes/royal.json')
    parser.add_argument('--start', type=int)
    parser.add_argument('--frames', type=int)
    args = parser.parse_args()
    source, recipe = json.loads(SOURCE.read_text()), json.loads(args.recipe.read_text())
    if hashlib.sha256(args.rom.read_bytes()).hexdigest() != source['rom_sha256'] or recipe['rom_sha256'] != source['rom_sha256']:
        raise SystemExit('Requires the verified Royal Rumble USA ROM')
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit('Choose an empty output directory')
    env = {k: v for k, v in os.environ.items() if k not in ('WWF_TRACE_DIR', 'WWF_ROYAL_PROBE')}
    state = None
    for stage in source['stages']:
        out = args.output / 'source' / stage['name']
        run(args.core, args.rom, out, stage['frames'], stage['frames'], state, stage['inputs'], env=env)
        prefix = out / f"frame-{stage['frames']:06d}"
        for suffix, expected in stage['snapshot_sha256'].items():
            if hashlib.sha256(Path(str(prefix) + suffix).read_bytes()).hexdigest() != expected:
                raise SystemExit(f"Snapshot mismatch: {stage['name']}{suffix}")
        state = Path(str(prefix) + '.state')
        if stage['name'] == recipe['match_state_stage']:
            break
    start = args.start if args.start is not None else recipe['move_start'] - 10
    frames = args.frames or recipe['frames_from_match'] - start
    run(args.core, args.rom, args.output / 'pre', start, start, state, recipe['inputs'], env=env)
    run(args.core, args.rom, args.output / 'capture', frames, 1, args.output / 'pre' / f'frame-{start:06d}.state',
        recipe['inputs'], base=start, env=env)
    (args.output / 'capture' / 'capture.json').write_text(json.dumps(
        {'recipe': str(args.recipe.relative_to(ROOT)) if args.recipe.is_relative_to(ROOT) else args.recipe.name,
         'first_recipe_frame': start + 1, 'frames': frames, 'move_start': recipe['move_start']}, indent=1) + '\n')
    print('Captured', frames, 'frames from recipe frame', start + 1)


if __name__ == '__main__':
    main()
