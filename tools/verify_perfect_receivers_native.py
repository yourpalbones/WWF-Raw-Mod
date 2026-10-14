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
- PP-1/2 every fully matched frame registers the receiver to within 1 px, both actors 40 px apart (receivers
        drawn from their own native sequence: every step equals the editor preview on >= 97% of pixels);
- PP-3  the receiver's shadow centre stays within 12 px of its body's opaque centre;
- PP-7  no receiver palette-6 object shows foreign VRAM, and no more than 4 trail the receiver body;
- PP-4  after the move neither actor shows a Perfect-Plex pose except the final pose for at most
        2 frames (OAM is one frame behind), and the receiver loses health exactly once.
- PP-5  the exit (docs/perfect-plex-exit.md):
        - the bridge (step 11) is held for 8 stream entries, Royal's 56 frames: 55 to 59 frames of the match
          clock (WRAM $0F70) when it runs, else of the screen (the clock stands still in some matches). Raw's
          stream steps last 6 to 8 frames each, in the move itself too;
        - every later step (held pin, release, Mr. Perfect's get-up, the receiver rolling off and lying, then
          Perfect standing) equals the editor preview on >= 97% of pixels, for every receiver, each wrestler at
          his actual position (tools/check_preview_native.py);
        - the receiver ends on Perfect's far side at the planned spacing (data/perfect-plex-exit.json), unless
          the ring edge stopped him short ('ring_stop', px);
        - neither wrestler's depth (y) changed, except Raw's 7 px collision push after a ring stop brought the
          pair within 40 px ('depth_push').

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
                'receiver_shadow_offset_during_move', 'receiver_health_changes', 'receiver_source', 'preview_match', 'exit')
EXIT = json.loads((ROOT / 'data/perfect-plex-exit.json').read_text())
HOLD_FRAMES = 56   # Royal Rumble shows the bridge for 56 frames before the release (data/perfect-plex-exit.json)


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
    own = m.get('receiver_source') == 'own_art'
    # Spacing while both actors are still where the move put them; at the release the actors move and OAM shows
    # step 11 for one more frame (one row per actor).
    rows = [r for r in m['rows'] if 'camera_x' in r]
    start = rows and (rows[0]['attacker']['x'], rows[0]['receiver']['x'])
    moved = [r for r in rows if (r['attacker']['x'], r['receiver']['x']) != start]
    if not rows or len(moved) > 2 or any(abs(r['receiver']['x'] - r['attacker']['x']) != 40 for r in rows if r not in moved) or \
            (not own and any(abs(int(e)) > 1 for e in m['registration_errors'])):
        failed.append('PP-1/2 registration')
    # Own-native receivers: the drawn pair must equal the editor preview (tools/check_preview_native.py).
    if own and min(m.get('preview_match') or [0]) < 0.97:
        failed.append('PP-1/2 preview mismatch')
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
    # The move's damage: exactly one loss of health. A downed wrestler also regains health a little later in the
    # capture (+16 for Owen and Kid); a rise is not damage, two losses would be.
    if len([c for c in m.get('receiver_health_changes', []) if c[2] < c[1]]) != 1:
        failed.append('PP-4 damage count')
    x = m.get('exit') or {}
    held = x.get('hold_game_frames') or x.get('hold_frames') or 0
    if not HOLD_FRAMES - 1 <= held <= HOLD_FRAMES + 3:
        failed.append('PP-5 pin length')
    if not x.get('exit_preview_match') or min(x['exit_preview_match']) < 0.97:
        failed.append('PP-5 exit drawings')
    planned = EXIT['receiver']['spacing']
    far = x.get('start_spacing') and x['final_spacing'] * x['start_spacing'] < 0
    if not far or abs(x['final_spacing']) != planned - x.get('ring_stop', 0):
        failed.append('PP-5 receiver side')
    push = [b - a for a, b in zip(x.get('start_y', []), x.get('final_y', []))]
    if any(push) and not (x.get('ring_stop') and abs(x['final_spacing']) <= 40 and sorted(map(abs, push)) == [0, 7]):
        failed.append('PP-5 depth')
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
        if m['frames_fully_matched']:
            measurement = args.output / f'{name}-measurement.json'
            measurement.write_text(json.dumps(m) + '\n')
            facing = 'left' if '(False, True)' in m['flip_pairs'] else 'right'
            check = json.loads(subprocess.run([sys.executable, str(ROOT / 'tools/check_preview_native.py'), str(args.rom),
                                               str(recipe['receiver_slot']), str(measurement), str(capture), facing],
                                              check=True, capture_output=True, text=True).stdout)
            # The move's steps are compared for receivers drawn from their own art (Royal-drawn ones are registered
            # against Royal instead); the exit's steps for every receiver.
            m['preview_match'] = check['match_ratio'] if m.get('receiver_source') == 'own_art' else None
            last = max(capture.glob('frame-*-wram.bin'))
            final = last.read_bytes()
            word = lambda a: int.from_bytes(final[a:a + 2], 'little')
            timer = lambda f: int.from_bytes((capture / f'frame-{f:06d}-wram.bin').read_bytes()[0xF70:0xF72], 'little')
            first = m['rows'][0]
            bridge = [r['frame'] for r in m['rows'] if r.get('attacker_pose') == 11]
            # The receiver's deviation from its planned spot at the end (Raw's ring edge stops him short).
            stop = abs((check['deviations'].get(str(len(check['steps']))) or {}).get('receiver', [0])[0])
            m['exit'] = {'hold_frames': len(bridge), 'hold_game_frames': timer(bridge[0]) - timer(bridge[-1] + 1),
                         'exit_preview_match': check['exit_match_ratio'],
                         'start_spacing': first['receiver']['x'] - first['attacker']['x'],
                         'final_spacing': word(0x5f2) - word(0x5f0),
                         'start_y': [first['attacker']['y'], first['receiver']['y']], 'final_y': [word(0x600), word(0x602)],
                         'final_actions': [word(0x6b4), word(0x6b6)], **({'ring_stop': stop} if stop else {})}
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
