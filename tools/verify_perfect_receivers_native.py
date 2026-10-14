"""Replay every committed Perfect-Plex recipe from a cold boot and re-measure it.

For each recipe in evidence/perfect-plex-receivers/recipes/:
1. Cold boot and replay the controller inputs to `capture_from`, then save a state.
2. Capture `capture_frames` frames (memory snapshot every frame) from that state.
3. Run tools/measure_perfect_pair.py on the capture and check the results
   against the recipe's `expected` block, written by --record.

Controller input only; no emulator memory is written. Bulky captures are
deleted unless --keep is given. Only the JSON summaries are kept.

    python3 tools/verify_perfect_receivers_native.py CORE BUILT_ROM ROYAL_ROM --output OUT [--scenario NAME] [--record]

BUILT_ROM must be the measured build (SHA-256 below):
- editor export of the unmodified Raw ROM;
- tools/diagnostic_restore_hirom_mirror.py;
- codex/perfect-receivers-wip @ 2955d5c tools/build_perfect_receivers.py.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPES = ROOT / 'evidence/perfect-plex-receivers/recipes'
MEASURED_BUILD = '4ca2856994fdebba62205a186feb5058c8b3a30760ad95423354012a4a128085'
SUMMARY_KEYS = ('frames_measured', 'frames_fully_matched', 'flip_pairs', 'receiver_body_terms', 'actor_spacing',
                'registration_errors', 'receiver_trailing_palette6_during_move', 'frames_with_foreign_palette6_during_move')


def run(core, rom, recipe_path, output, extra):
    command = [sys.executable, str(ROOT / 'tools/run_controller_recipe.py'), str(core), str(rom), str(recipe_path),
               '--output', str(output)] + extra
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)


def summary(measurement):
    out = {k: measurement[k] for k in SUMMARY_KEYS}
    after = measurement['after_move'] or {}
    out['after_move'] = {k: after.get(k) for k in ('actions', 'attacker_pose_shown', 'receiver_pose_shown')}
    rows = [r for r in measurement['rows'] if 'receiver_pixels' in r]
    out['receiver_pixel_match_min'] = min(r['receiver_pixels_matching_recipe_after_shift'] / r['receiver_pixels']
                                          for r in rows) if rows else None
    out['vertical_offsets'] = sorted({r['vertical']['attacker_origin_y'] - r['vertical']['receiver_origin_y'] for r in rows})
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('core', type=Path)
    parser.add_argument('rom', type=Path)
    parser.add_argument('royal', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenario', action='append')
    parser.add_argument('--record', action='store_true', help='write measured summaries into the recipes as expected')
    parser.add_argument('--keep', action='store_true')
    args = parser.parse_args()
    if hashlib.sha256(args.rom.read_bytes()).hexdigest() != MEASURED_BUILD:
        raise SystemExit('BUILT_ROM is not the measured build; see the module docstring')
    sys.path.insert(0, str(ROOT / 'tools'))
    from measure_perfect_pair import measure
    args.output.mkdir(parents=True, exist_ok=True)
    results, failures = {}, []
    for path in sorted(RECIPES.glob('*.json')):
        recipe = json.loads(path.read_text())
        name = recipe['scenario']
        if args.scenario and name not in args.scenario:
            continue
        pre, capture = args.output / f'{name}-pre', args.output / f'{name}-capture'
        for d in (pre, capture):
            shutil.rmtree(d, ignore_errors=True)
        start = recipe['capture_from']
        run(args.core, args.rom, path, pre, ['--frames', str(start), '--interval', str(start)])
        run(args.core, args.rom, path, capture, ['--from-state', str(pre / f'frame-{start:06d}.state'),
                                                 '--base', str(start), '--frames', str(recipe['capture_frames']),
                                                 '--interval', '1'])
        m = measure(capture, args.rom.read_bytes(), args.royal.read_bytes(), recipe['receiver_slot'])
        (args.output / f'{name}-measurement.json').write_text(json.dumps(m, indent=1) + '\n')
        got = summary(m)
        results[name] = got
        if args.record:
            recipe['expected'] = got
            path.write_text(json.dumps(recipe, indent=1) + '\n')
        elif recipe.get('expected') != json.loads(json.dumps(got)):
            failures.append(name)
        if not args.keep:
            shutil.rmtree(pre)
            shutil.rmtree(capture)
        print(name, 'recorded' if args.record else ('FAIL' if name in failures else 'ok'), flush=True)
    report = {'build_sha256': MEASURED_BUILD, 'controller_only': True, 'results': results, 'failures': failures}
    (args.output / 'verification.json').write_text(json.dumps(report, indent=1) + '\n')
    if failures:
        raise SystemExit('Mismatched scenarios: ' + ', '.join(failures))


if __name__ == '__main__':
    main()
