"""Replay the browser-exported new slot from reset, using controller input only."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('core', type=Path)
parser.add_argument('rom', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
recipe = json.loads((root/'evidence/mr-perfect-import/controller-replay.json').read_text())
command = [sys.executable, str(root/'tools/run_headless.py'), str(args.core), str(args.rom),
           '--output', str(args.output), '--frames', str(recipe['frames']), '--interval', str(recipe['frames'])]
for frame in recipe['snapshots']:
    command += ['--snapshot-frame', str(frame)]
for port, start, button, duration in recipe['inputs']:
    command += ['--press-p2' if port else '--press', f'{start}:{button}:{duration}']
subprocess.run(command, check=True)

def actors(frame):
    data = (args.output/f'frame-{frame:06d}-wram.bin').read_bytes()
    word = lambda at: int.from_bytes(data[at:at+2], 'little')
    return [{'selector': word(0xb74+i), 'action': word(0x6b4+i), 'health': word(0xa78+i),
             'x': word(0x5f0+i), 'y': word(0x600+i)} for i in (0, 2)]

before = actors(recipe['move_stage_start'])
active = actors(recipe['move_stage_start']+300)
after = actors(recipe['frames'])
assert [a['selector'] for a in after] == [24, 0], after
assert [a['action'] for a in active] == [600, 540], active
assert before[1]['health']-after[1]['health'] == 160, (before, after)
assert [a['action'] for a in after] == [0, 70], after
report = {'cold_boot': True, 'controller_only': True, 'emulator_memory_writes': False,
          'rom_sha256': hashlib.sha256(args.rom.read_bytes()).hexdigest(),
          'frames': recipe['frames'], 'before': before, 'active': active, 'after': after,
          'native_damage': 160, 'attacker_recovered': True}
(args.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
