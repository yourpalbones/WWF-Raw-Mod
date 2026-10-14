"""Replay every committed Perfect-Plex recipe from a cold boot, re-measure it and check the defects stay fixed.

For each recipe in evidence/perfect-plex-receivers/recipes/ (recovery recipes are traced separately):
1. Cold boot and replay the controller inputs to `capture_from`, then save a state.
2. Capture `capture_frames` frames (memory snapshot every frame) from that state.
3. Run tools/measure_perfect_pair.py on the capture and check:
   - the defect assertions below, on any build;
   - the recipe's `expected` block, written by --record, when BUILT_ROM is the build recorded in `expected_build`.

Defect assertions (each fails on the pre-fix build 4ca2856..., kept in each recipe as `defect_baseline`):
- PP-0  the announcer bank tables match the profile records (an import whose stock-input match stalled
        fails this check), and the replay reaches the move from a cold boot;
- PP-1/2 every fully matched frame registers the receiver to within 1 px, both actors 40 px apart;
- PP-3  the receiver's shadow centre stays within 12 px of its body's opaque centre;
- PP-7  no receiver palette-6 object shows foreign VRAM, and no more than 4 trail the receiver body;
- PP-4  after the move neither actor shows a Perfect-Plex pose except the final pose for at most
        2 frames (OAM is one frame behind), and the receiver loses health exactly once.

--record writes `expected` only after every assertion passes. Controller input only; no emulator memory is
written. Bulky captures are deleted unless --keep is given. Only the JSON summaries are kept.

    python3 tools/verify_perfect_receivers_native.py CORE BUILT_ROM ROYAL_ROM --output OUT [--scenario NAME] [--record]
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
DEFECT_BUILD = '4ca2856994fdebba62205a186feb5058c8b3a30760ad95423354012a4a128085'
SUMMARY_KEYS = ('frames_measured', 'frames_fully_matched', 'flip_pairs', 'receiver_body_terms', 'actor_spacing',
                'registration_errors', 'receiver_trailing_palette6_during_move', 'frames_with_foreign_palette6_during_move',
                'receiver_shadow_offset_during_move', 'receiver_health_changes')


def run(core, rom, recipe_path, output, extra):
    command = [sys.executable, str(ROOT / 'tools/run_controller_recipe.py'), str(core), str(rom), str(recipe_path),
               '--output', str(output)] + extra
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)


def summary(measurement):
    out = {k: measurement.get(k) for k in SUMMARY_KEYS}
    after = measurement['after_move'] or {}
    out['after_move'] = {k: after.get(k) for k in ('actions', 'attacker_pose_shown', 'receiver_pose_shown')}
    rows = [r for r in measurement['rows'] if 'receiver_pixels' in r]
    out['receiver_pixel_match_min'] = min(r['receiver_pixels_matching_recipe_after_shift'] / r['receiver_pixels']
                                          for r in rows) if rows else None
    out['vertical_offsets'] = sorted({r['vertical']['attacker_origin_y'] - r['vertical']['receiver_origin_y'] for r in rows})
    return out


def announcer_tables_consistent(rom):
    """PP-0: four announcer tables, one 16-bit entry per slot, must match the 13 profile records."""
    for target, field, bank in [(0x70e400, 20, False), (0x70e420, 20, True), (0x70e440, 24, False), (0x70e460, 24, True)]:
        for i in range(13):
            pointer = int.from_bytes(rom[0x708000 + i * 45 + field:0x708000 + i * 45 + field + 3], 'little')
            if int.from_bytes(rom[target + i * 2:target + i * 2 + 2], 'little') != (pointer >> 16 if bank else pointer & 0xffff):
                return False
    return True


def defects(m, rom):
    """Names of the defect assertions this measurement fails."""
    failed = []
    if not announcer_tables_consistent(rom):
        failed.append('PP-0 announcer tables')
    if not m['frames_measured']:
        failed.append('PP-0 move not reached')
        return failed
    if not m['frames_fully_matched'] or any(abs(int(e)) > 1 for e in m['registration_errors']) or \
            any(abs(int(k)) != 40 for k in m['actor_spacing']):
        failed.append('PP-1/2 registration')
    shadow = m.get('receiver_shadow_offset_during_move')
    if not shadow or max(abs(shadow['min']), abs(shadow['max'])) > 12:
        failed.append('PP-3 shadow')
    if m['frames_with_foreign_palette6_during_move'] or any(int(k) > 4 for k in m['receiver_trailing_palette6_during_move']):
        failed.append('PP-7 extra objects')
    after = m['after_move'] or {}
    for key in ('attacker_pose_shown', 'receiver_pose_shown'):
        shown = after.get(key) or {}
        if any(p not in ('None', '11') for p in shown) or shown.get('11', 0) > 2:
            failed.append('PP-4 exit art')
            break
    if len(m.get('receiver_health_changes', [])) != 1:
        failed.append('PP-4 damage count')
    return failed


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
    rom = args.rom.read_bytes()
    build = hashlib.sha256(rom).hexdigest()
    sys.path.insert(0, str(ROOT / 'tools'))
    from measure_perfect_pair import measure
    args.output.mkdir(parents=True, exist_ok=True)
    results, failures = {}, []
    for path in sorted(RECIPES.glob('*.json')):
        recipe = json.loads(path.read_text())
        name = recipe['scenario']
        if 'base_recipe' in recipe:
            continue
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
        m = measure(capture, rom, args.royal.read_bytes(), recipe['receiver_slot'])
        (args.output / f'{name}-measurement.json').write_text(json.dumps(m, indent=1) + '\n')
        got = json.loads(json.dumps(summary(m)))
        failed = defects(m, rom)
        results[name] = {'summary': got, 'defects': failed}
        if failed:
            failures.append(name)
        elif args.record:
            recipe['expected_build'], recipe['expected'] = build, got
            path.write_text(json.dumps(recipe, indent=1) + '\n')
        elif recipe.get('expected_build') == build and recipe.get('expected') != got:
            failures.append(name)
            results[name]['defects'].append('differs from expected')
        if not args.keep:
            shutil.rmtree(pre)
            shutil.rmtree(capture)
        print(name, 'FAIL ' + ', '.join(results[name]['defects']) if name in failures else
              ('recorded' if args.record else 'ok'), flush=True)
    report = {'build_sha256': build, 'controller_only': True, 'results': results, 'failures': failures}
    (args.output / 'verification.json').write_text(json.dumps(report, indent=1) + '\n')
    if failures:
        raise SystemExit('Failed scenarios: ' + ', '.join(failures))


if __name__ == '__main__':
    main()
