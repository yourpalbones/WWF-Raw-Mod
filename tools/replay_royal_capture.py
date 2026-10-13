"""Verify Mr. Perfect's Royal Rumble source match from cold boot, using inputs only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('core', type=Path)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--recipe', type=Path, default=Path(__file__).resolve().parents[1]
                        / 'data/royal-perfect-source-capture.json')
    args = parser.parse_args()
    recipe = json.loads(args.recipe.read_text())
    if hashlib.sha256(args.rom.read_bytes()).hexdigest() != recipe['rom_sha256']:
        raise ValueError('Requires the verified Royal Rumble USA ROM')
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Choose an empty output directory')
    env = os.environ.copy()
    env.pop('WWF_TRACE_DIR', None)
    env.pop('WWF_ROYAL_PROBE', None)
    state = None
    for stage in recipe['stages']:
        output = args.output / stage['name']
        command = [sys.executable, str(Path(__file__).with_name('run_headless.py')),
                   str(args.core), str(args.rom), '--output', str(output),
                   '--frames', str(stage['frames']), '--interval', str(stage['frames'])]
        if state:
            command += ['--load-state', str(state)]
        for port, frame, button, duration in stage['inputs']:
            command += ['--press-p2' if port else '--press', f'{frame}:{button}:{duration}']
        subprocess.run(command, env=env, check=True)
        prefix = output / f"frame-{stage['frames']:06d}"
        for suffix, expected in stage['snapshot_sha256'].items():
            actual = hashlib.sha256(Path(str(prefix) + suffix).read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f"Snapshot mismatch: {stage['name']}{suffix}")
        state = Path(str(prefix) + '.state')
        print('Verified', stage['name'], flush=True)
    print('Verified controller-only Royal Rumble source match from cold boot')


if __name__ == '__main__':
    main()
