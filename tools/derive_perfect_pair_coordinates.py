"""ROM-free derivation of Perfect-Plex paired screen coordinates.

Predicts where the attacker and receiver pixels land on screen, given the
recipe transforms written by the builders and a set of explicit assumptions
about Raw's renderer. Outputs are PREDICTIONS for review: none of the renderer
assumptions has been confirmed by a native trace in this repository.

    python3 tools/derive_perfect_pair_coordinates.py            # write report
    python3 tools/derive_perfect_pair_coordinates.py --check    # fail if stale

Transforms (from code; each is a pure translation or reflection):

  Royal source frame. Both wrestlers come from one Royal OAM capture, so their
  columns share one screen coordinate system. The common anchor is (145, 162).

  Attacker (tools/import_perfect_plex.py, build):
    canvas px = 145 - x + 56, py = y - 162 + 100   (pixel-level mirror of column x)
    descriptor dx = px - 56, dy = py - 100
    => attacker-relative a = 145 - x,  v = y - 162
    profile entry: body (0, 0), shadow 0x8024 at (0, -1)

  Receiver (tools/map_perfect_receivers.py -> tools/build_perfect_receiver_prototype.py
            and codex/perfect-receivers-wip tools/build_perfect_receivers.py):
    part x' = x - 145 (Royal orientation kept); painted at x' + 73; chunks sampled
    at chunk_x + 64, so descriptor dx = x' + 9; dy = y - 162
    profile entry: body (+32, 0), shadow 0x8024 at (0, -1)
    => receiver-relative r = x - 145 + 9 + 32 = x - 104,  v = y - 162

Assumptions varied (all unconfirmed):
  A1 attacker_flipped: whether the attacker's descriptors are mirrored at runtime
     when the receiver is on its right (the observed tie-up arrangement).
  A2 reflection: 'edge' maps relative column c to -c-1 (exact pixel reflection);
     'centre' maps c to -c; 'native+8' maps c to -c+7, which is the object rule
     oam_x = origin - dx - size + 8 MEASURED on the WIP build (one facing; see
     docs/perfect-plex-native-trace.md).
  A3 profile_offset_mirrored: whether the profile dx is negated with facing.
  Fixed: the receiver faces opposite the attacker; descriptor dy and profile dy
  are not affected by horizontal facing; both actors share the same y origin.
"""
import argparse
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANCHOR_X, ANCHOR_Y = 145, 162
ATTACKER_CANVAS = (56, 100)          # import_perfect_plex: px = 145 - x + 56
RECEIVER_PAINT_X, RECEIVER_SAMPLE_X = 73, 64
RECEIVER_PROFILE = (32, 0)           # both receiver builders write [32, 0] for the body
SHADOW = (0, -1)                     # 0x8024 entry in both profiles


def relative_columns(royal_x):
    """Attacker and receiver descriptor-space column for one Royal screen column."""
    attacker = (ANCHOR_X - royal_x + ATTACKER_CANVAS[0]) - ATTACKER_CANVAS[0]
    receiver_descriptor = (royal_x - ANCHOR_X) + (RECEIVER_PAINT_X - RECEIVER_SAMPLE_X)
    return attacker, receiver_descriptor


def screen(origin, relative, profile_dx, flipped, reflection, profile_mirrored):
    """Screen column of a descriptor-relative column under the given assumptions."""
    if not flipped:
        return origin + profile_dx + relative
    mirrored = {'edge': -relative - 1, 'centre': -relative, 'native+8': -relative + 7}[reflection]
    return origin + (-profile_dx if profile_mirrored else profile_dx) + mirrored


def linear(origin, profile_dx, rel_of_x, flipped, reflection, profile_mirrored):
    """Express screen column as s * royal_x + t."""
    p0 = screen(origin, rel_of_x(0), profile_dx, flipped, reflection, profile_mirrored)
    p1 = screen(origin, rel_of_x(1), profile_dx, flipped, reflection, profile_mirrored)
    return p1 - p0, p0


def derive(observed_spacing):
    receivers = json.loads((ROOT / 'data/perfect-receivers.json').read_text())
    poses = receivers['workers'][2]['poses']   # Royal Undertaker; bbox geometry is per worker
    cases = []
    for attacker_flipped, reflection, profile_mirrored in itertools.product(
            (False, True), ('edge', 'centre', 'native+8'), (True, False)):
        sa, ta = linear(0, 0, lambda x: relative_columns(x)[0], attacker_flipped, reflection, profile_mirrored)
        # Receiver origin R is unknown: screen = s * x + (tr0 + R).
        sr, tr0 = linear(0, RECEIVER_PROFILE[0], lambda x: relative_columns(x)[1] + 0,
                         not attacker_flipped, reflection, profile_mirrored)
        rigid = sa == sr
        required = ta - tr0 if rigid else None
        frames = []
        for pose in poses:
            x0, y0, x1, y1 = pose['bbox']
            royal_cols = (x0 + ANCHOR_X, x1 + ANCHOR_X)
            body = sorted(sr * c + tr0 + observed_spacing for c in royal_cols)
            correct = sorted(sa * c + ta for c in royal_cols) if rigid else None
            shadow = observed_spacing + (SHADOW[0] if not profile_mirrored else -SHADOW[0])
            frames.append({
                'source_frame': pose['source_frame'],
                'receiver_body_x_from_attacker_origin': body,
                'royal_registered_x_from_attacker_origin': correct,
                'horizontal_error_px': None if not rigid else body[0] - correct[0],
                'receiver_shadow_x_from_attacker_origin': shadow,
                'shadow_to_nearest_body_edge_px': (0 if body[0] <= shadow <= body[1]
                                                   else min(abs(shadow - body[0]), abs(shadow - body[1]))),
                'vertical_error_px': 0,
            })
        cases.append({
            'assumptions': {'attacker_flipped_when_receiver_on_right': attacker_flipped,
                            'reflection': reflection, 'profile_offset_mirrored': profile_mirrored},
            'scene_vs_royal': None if not rigid else ('mirrored' if sa == -1 else 'same orientation'),
            'rigid': rigid,
            'required_receiver_minus_attacker_x': required,
            'observed_receiver_minus_attacker_x': observed_spacing,
            'predicted_horizontal_error_px': None if not rigid else observed_spacing - required,
            'frames': frames,
        })
    return cases


def report(observed, source):
    cases = derive(observed['spacing'])
    return {
        'generated_by': 'tools/derive_perfect_pair_coordinates.py',
        'status': 'PREDICTION from code and recorded actor positions; renderer assumptions unconfirmed by native trace',
        'observed_actor_positions': observed,
        'observed_source': source,
        'cases': cases,
    }


def observed_positions():
    data = json.loads((ROOT / 'evidence/mr-perfect-import/verification.json').read_text())['native']
    attacker, receiver = data['active']
    return ({'attacker_x': attacker['x'], 'receiver_x': receiver['x'],
             'attacker_y': attacker['y'], 'receiver_y': receiver['y'],
             'spacing': receiver['x'] - attacker['x'], 'rom_sha256': data['rom_sha256'],
             'receiver_selector_word': receiver['selector']},
            'evidence/mr-perfect-import/verification.json native.active (v0.16 release build, Luna receiving, '
            'one facing only). The init hook shifts both actors by the same clamp delta, so it preserves the '
            'tie-up spacing; spacing for other receivers, facings and rope positions is not recorded.')


def markdown(data):
    obs = data['observed_actor_positions']
    out = ['# Perfect-Plex paired coordinate derivation', '',
           f'Generated by `{data["generated_by"]}`. **{data["status"]}.**', '',
           'This is a ROM-free model. It combines the transforms in the builders with actor '
           f'positions recorded in a native replay: attacker x={obs["attacker_x"]}, receiver x={obs["receiver_x"]} '
           f'(spacing **{obs["spacing"]:+d}**), both y={obs["attacker_y"]}. Source: {data["observed_source"]}', '',
           '## Transforms taken from code', '',
           '| Actor | Royal column x → descriptor column | Profile body | Profile shadow |',
           '| --- | --- | --- | --- |',
           '| Attacker (`import_perfect_plex.py`) | `145 - x` (pixel mirror) | (0, 0) | (0, -1) |',
           '| Receiver (prototype and `codex/perfect-receivers-wip`) | `x - 145 + 9` (Royal orientation; +9 from paint 73 / sample 64) | (+32, 0) | (0, -1) |',
           '', 'Both use `y - 162` vertically, so vertical registration is exact when both actor y origins are equal.'
           f' The recorded y values are equal ({obs["attacker_y"]}/{obs["receiver_y"]}).', '',
           '## Predictions under each assumption set', '',
           '| Attacker flipped (receiver on right) | Reflection | Profile dx mirrored | Rigid? | Scene vs Royal | Required R−A | Observed R−A | Predicted error (px) | Shadow to body (px, frame 56 / 144) |',
           '| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |']
    for case in data['cases']:
        a = case['assumptions']
        f0, f11 = case['frames'][0], case['frames'][-1]
        out.append(f"| {a['attacker_flipped_when_receiver_on_right']} | {a['reflection']} | {a['profile_offset_mirrored']} | "
                   f"{case['rigid']} | {case['scene_vs_royal'] or '—'} | {case['required_receiver_minus_attacker_x']} | "
                   f"{case['observed_receiver_minus_attacker_x']:+d} | {case['predicted_horizontal_error_px']} | "
                   f"{f0['shadow_to_nearest_body_edge_px']} / {f11['shadow_to_nearest_body_edge_px']} |")
    best = [c for c in data['cases'] if c['rigid'] and abs(c['predicted_horizontal_error_px']) <= 2]
    out += ['', '## Reading the table', '',
            '- The model fixes the receiver as facing opposite the attacker, so exactly one actor is mirrored in every '
            'case and every case is a rigid copy of Royal (the "Rigid?" column). The open question is only whether '
            'the actor spacing matches the spacing that copy requires. If a trace shows both actors with the same '
            'runtime flip, no spacing can register them, and this model does not apply.']
    if best:
        rules = ' or '.join(sorted({c['assumptions']['reflection'] for c in best}))
        out += [f'- The recorded spacing ({obs["spacing"]:+d}) is within 2 px of the required spacing only when the '
                'attacker is **not** flipped while the receiver is on its right, and the profile dx is negated with '
                f'facing. Either reflection rule ({rules}) fits. Under these assumptions the scene renders as a **mirror** of Royal. '
                'The receiver body is drawn on the attacker\'s *left*, while the receiver actor origin, and therefore its '
                'profile shadow, stays on the right. One cause would then explain both the entry side swap (PP-1) and the '
                'detached shadow (PP-3). The two bodies would stay registered to within 1–2 px, so the overlap on lift '
                'frames (PP-2) would need another explanation, such as OAM draw order, a different spacing for that '
                'receiver, or routing/upload.',
                '- Cross-check for assumption A1: the imported attacker art is a mirror of Royal\'s right-facing Perfect. '
                'Drawn unflipped, it faces left. A trace of the native tie-up OAM flip bits shows whether Raw\'s '
                'unflipped convention also faces left. If it does not, the imported attacker art is reversed relative '
                'to Raw\'s own art.',
                '- The other assumption sets predict errors of 62–82 px. GIF appearance is not used here to choose '
                'between assumption sets.']
    measured = ROOT / 'evidence/perfect-plex-receivers/native-wip/measurement.json'
    if measured.exists():
        m = json.loads(measured.read_text())
        native = next(c for c in data['cases'] if c['assumptions'] == {
            'attacker_flipped_when_receiver_on_right': False, 'reflection': 'native+8', 'profile_offset_mirrored': True})
        spacings = sorted({r['receiver']['x'] - r['attacker']['x'] for r in m['rows'] if 'camera_x' in r})
        out += ['', '## Native measurement', '',
                f'From `evidence/perfect-plex-receivers/native-wip/measurement.json` (WIP build, receiver slot '
                f'{m["receiver_slot"]}, one facing, {m["frames_fully_matched"]} of {m["frames_measured"]} move frames '
                'matched to their descriptors):', '',
                f'- Flip pairs (attacker, receiver): {m["flip_pairs"]}. The attacker is unflipped with the receiver on its right.',
                f'- Receiver object term (oam_x + dx + size minus actor screen x): {m["receiver_object_terms"]}; '
                f'body term after removing the flip pivot: {m["receiver_body_terms"]}. That is -32 (profile dx '
                'negated) + 8, so the flipped object rule is oam_x = origin - dx - size + 8 (`native+8` above), '
                'not edge or centre reflection. All ten scenarios, both facings, agree '
                '(evidence/perfect-plex-receivers/recipes/*.json `expected`).',
                f'- Measured receiver registration error versus Royal: {m["registration_errors"]} px, at actor spacing '
                f'{spacings}. The model row for the measured rule predicts '
                f'{native["predicted_horizontal_error_px"]:+d} px at the recorded spacing.',
                f'- Attacker objects precede receiver objects in OAM (attacker drawn on top): {m["attacker_oam_first"]}.']
    out += ['', '## What a native trace must confirm before any hook edit', '',
            '1. Facing word and runtime flip for attacker and receiver on the Perfect-Plex frames, in both facings.',
            '2. The renderer\'s reflection rule from OAM x for one known object. Measured in both facings and at both ropes: '
            'native+8 (see perfect-plex-native-trace.md).',
            '3. Whether profile dx is negated with facing.',
            '4. Actor x/y for each receiver, both facings and near both ropes. Only the Luna run is recorded here.',
            '5. OAM draw order between the two actors on lift frames.', '',
            'Per-frame predicted body spans are in '
            '[`evidence/perfect-plex-receivers/pair-coordinates.json`](../evidence/perfect-plex-receivers/pair-coordinates.json).', '']
    return '\n'.join(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    observed, source = observed_positions()
    data = report(observed, source)
    outputs = {ROOT / 'evidence/perfect-plex-receivers/pair-coordinates.json': json.dumps(data, indent=1) + '\n',
               ROOT / 'docs/perfect-plex-pair-coordinates.md': markdown(data)}
    stale = [p for p, t in outputs.items() if not p.exists() or p.read_text() != t]
    if args.check:
        raise SystemExit('Stale: ' + ', '.join(map(str, stale)) if stale else 0)
    for path, text in outputs.items():
        path.write_text(text)
    for case in data['cases']:
        print(case['assumptions'], 'rigid' if case['rigid'] else 'not rigid',
              'required', case['required_receiver_minus_attacker_x'], 'error', case['predicted_horizontal_error_px'])
