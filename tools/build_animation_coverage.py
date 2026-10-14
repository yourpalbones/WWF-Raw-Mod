"""Build the roster animation coverage inventory from tracked evidence only.

No ROM is read. Every status below is derived from a committed data file or
evidence directory; anything not traced to evidence is recorded as
`not_audited`, never inferred from piece counts or screenshots.

Outputs `data/animation-coverage.json` (machine-readable, maintained) and
`docs/animation-coverage.md` (readable report). Re-run after evidence changes:

    python3 tools/build_animation_coverage.py
    python3 tools/build_animation_coverage.py --check   # fail if outputs are stale
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_perfect_receivers import analyse as analyse_receivers  # noqa: E402

# Art provenance. Kept separate from gameplay verification on purpose.
ART_STATUSES = {
    'original': 'Stock WWF Raw artwork, unmodified by this project',
    'customized': 'Stock Raw body/animation with user-edited gear, head or palette',
    'native_port': 'Donor-game drawing reproduced from native source tiles and anchors',
    'authored_replacement': 'Newly drawn native-resolution artwork',
    'own_art_adapted': "The worker's own native drawings (identity, gear, user edits) privately copied and re-timed for a move they were not drawn for",
    'adapted_placeholder': 'Existing Raw artwork standing in for a pose it was not drawn for',
    'decoded_only': 'Source recipe decoded/mapped; not inserted into any shipped Raw build',
    'prototype_private': 'Inserted only in a private test build; not released',
    'missing': 'No suitable art exists for this role',
    'not_audited': 'No tracked evidence either way',
}
GAMEPLAY_STATUSES = {
    'verified_visual': 'Native gameplay capture reviewed for this role and art',
    'verified_functional': 'Controller replay proves the action runs (damage/recovery); visuals not accepted',
    'defective': 'Native gameplay capture exists and shows a visible defect',
    'untested': 'No native gameplay capture for this role and art',
}

# Raw logical slot -> identity. Display names are what the user currently ships.
SLOTS = [
    {'slot': 0, 'original': 'Luna Vachon', 'display': 'Luna Vachon', 'customization': None},
    {'slot': 1, 'original': 'Bret Hart', 'display': 'Bret Hart', 'customization': 'black gear, bare arms',
     'customization_evidence': ['evidence/bret-black-gear/README.md', 'evidence/bret-bare-arms/README.md',
                                'evidence/bret-movement/README.md']},
    {'slot': 2, 'original': 'Undertaker', 'display': 'Undertaker', 'customization': None},
    {'slot': 3, 'original': 'Yokozuna', 'display': 'Yokozuna', 'customization': None},
    {'slot': 4, 'original': 'Bam Bam Bigelow', 'display': 'Bam Bam Bigelow', 'customization': None},
    {'slot': 5, 'original': 'Razor Ramon', 'display': 'Scott Hall', 'customization': 'NWO gear on native body',
     'customization_evidence': ['evidence/scott-hall-gear/README.md', 'evidence/nwo-gear/README.md',
                                'evidence/nwo-art-revision/README.md']},
    {'slot': 6, 'original': 'Lex Luger', 'display': 'Lex Luger', 'customization': None},
    {'slot': 7, 'original': 'Doink', 'display': 'Sting', 'customization': 'rebuilt from Undertaker donor body with authored head/gear',
     'customization_evidence': ['evidence/sting-rebuild/README.md', 'evidence/sting-native-heads/README.md']},
    {'slot': 8, 'original': 'Shawn Michaels', 'display': 'Shawn Michaels', 'customization': 'experimental superkick art',
     'customization_evidence': ['evidence/shawn-superkick-animation/README.md']},
    {'slot': 9, 'original': '1-2-3 Kid', 'display': 'Syxx', 'customization': 'NWO gear, registered head art',
     'customization_evidence': ['evidence/nwo-gear/README.md', 'evidence/syxx-head-revision/README.md']},
    {'slot': 10, 'original': 'Diesel', 'display': 'Kevin Nash', 'customization': 'NWO gear on native body',
     'customization_evidence': ['evidence/nwo-gear/README.md', 'evidence/nwo-art-revision/README.md']},
    {'slot': 11, 'original': 'Owen Hart', 'display': 'Owen Hart', 'customization': None},
    {'slot': 12, 'original': None, 'display': 'Mr. Perfect', 'customization': 'imported thirteenth slot (Royal Rumble)',
     'customization_evidence': ['evidence/mr-perfect-import/README.md']},
]
ROYAL_ROSTER = ['Randy Savage', 'Mr. Perfect', 'Undertaker', 'Bret Hart', 'Tatanka', 'Crush',
                'Ric Flair', 'Shawn Michaels', 'Razor Ramon', 'Yokozuna', 'Lex Luger', 'Ted DiBiase']
# Slots whose user-edited appearance a donor receiving drawing would not carry.
GEAR_EDITED = {1, 5, 7, 9, 10}
RAW_TO_ROYAL = {1: 3, 2: 2, 3: 9, 5: 8, 6: 10, 8: 7, 12: 1}

# Routing facts recovered by earlier evidence (docs/in-ring-sprites.md,
# evidence/roster-inventory). Addresses are CPU addresses in the Raw ROM.
STOCK_ROUTING = {
    'primary_lookup': '80:EC80-80:ECD0; selector word at WRAM 0B74+actor; tables AD:D513 (base) / AD:D52D (bank)',
    'secondary_lookup': '80:ED10-80:ED39; tables AD:D547 / AD:D561; part IDs >= 04FE use selector 8',
    'common_fallback': 'Primary part IDs >= 062D and secondary >= 04FE resolve through selector 8 (Shawn)',
    'tile_lookup': 'AC:F6E4 logical tile -> source pointer; AC:F959 sparse/direct copy',
}
PERFECT_ROUTING = {
    'primary_worker': 'hook 80:ECC1 -> 70:F000; slot 12 indices < 0BB2 (0BDC with Perfect-Plex) via table 71:0000',
    'secondary_worker': 'hook 80:ED19 -> 70:F100; table 71:1000 (limit 087F with Perfect-Plex)',
    'tile_lookup': 'hook AC:F6E4 -> 70:F200; private tile IDs C000+ -> pointers at 7D:0000 / 74:9800',
    'perfect_plex_attacker': 'init hook AC:ECB0 -> 70:F300, sequence hook 80:F073 -> 70:F400; stream 73:0000, descriptors 73:0100',
    'perfect_plex_receiver_released': 'stream 73:5000 / profiles 73:5100: stock receiving-suplex profiles + per-frame translate',
}

ORDINARY_CATEGORIES = ['idle_walk', 'strikes', 'grapples', 'running', 'ropes', 'turnbuckles',
                       'weapons', 'falls_knockdowns', 'recovery_getup', 'pins', 'submissions']


def load(path):
    return json.loads((ROOT / path).read_text())


def exists(paths):
    return [p for p in paths if (ROOT / p).exists()]


def row(slot, action, role, art, gameplay, **extra):
    assert art in ART_STATUSES and gameplay in GAMEPLAY_STATUSES, (art, gameplay)
    base = {'slot': slot, 'display_name': SLOTS[slot]['display'], 'action': action, 'role': role,
            'art_status': art, 'gameplay_status': gameplay}
    base.update(extra)
    base['evidence'] = exists(base.get('evidence', []))
    base.setdefault('defects', [])
    base.setdefault('aliases', 'not_audited')
    return base


def special_rows(moves):
    rows = []
    by_selector = {c['selector']: c for c in moves['characters']}
    for slot in range(12):
        info = by_selector[slot]
        customized = SLOTS[slot]['customization'] is not None
        for key, label in [('finisher', 'finisher'), ('mega_move', 'mega_move')]:
            move = info[key]
            name = move.get('in_game_special_move_name') or move.get('name')
            for role, flag in [('performer', 'attacker_sequence_verified'), ('receiver', 'defender_sequence_verified')]:
                ok = bool(move.get(flag))
                evidence = list(move.get('evidence', []))
                if customized:
                    evidence += SLOTS[slot].get('customization_evidence', [])
                defects = []
                if not ok:
                    defects.append(f'{flag} is false in data/wrestler-move-coverage.json')
                if customized and not move.get('edited_gear_verified'):
                    defects.append('Original-outfit capture only; edited gear not verified for this role')
                if move.get('complete_variant_coverage') is False:
                    defects.append('Only the first verified setup; directions/escapes/variants open')
                gameplay = 'verified_visual' if ok and not customized else 'untested'
                if customized and slot in (5, 9, 10) and role == 'performer':
                    # evidence/nwo-gear publishes finisher and mega performer GIFs with edited gear.
                    gameplay = 'verified_visual'
                rows.append(row(slot, f'{label}:{name or "unnamed"}', role,
                                'customized' if customized else 'original', gameplay,
                                source_game='WWF Raw', evidence=evidence, defects=defects,
                                runtime_routing=STOCK_ROUTING['primary_lookup'],
                                palette_owner=f'slot {slot}',
                                transitions='entry/exit captured in roster-specials GIFs' if ok else 'not verified'))
    return rows


# The Perfect-Plex exit works natively; these are its remaining differences from Royal (docs/perfect-plex-exit.md).
EXIT_DIFFERENCES = ("Exit (pin, release, recovery) native-verified, awaiting review; differs from Royal: Raw's 7-frame "
                    "step (get-up 42 frames, Royal 35), receiver lies 41 px away (Royal 33; Raw's downed-collision "
                    "rule), Raw's camera pans 13 px during the get-up")
RECEIVER_EXIT = ("Exit (roll-off, lying on Perfect's far side) uses Raw's own drawings in this slot's art, 41 px from "
                 "Perfect (Royal 33); native-verified, awaiting review (docs/perfect-plex-exit.md)")


def perfect_plex_rows(receivers):
    rows = []
    workers = {w['selector']: w for w in receivers['workers']}
    # Performer
    rows.append(row(12, 'finisher:Perfect-Plex', 'performer', 'native_port', 'verified_visual',
                    source_game='Royal Rumble', source_ids={'royal_poses': '783-806 (12 captured attacker drawings); exit '
                                                                           'get-up frames 76/77 and 80/81',
                                                            'raw_primary_indices': '1000-1011, exit 1012-1013',
                                                            'exit_plan': 'data/perfect-plex-exit.json'},
                    descriptor_locations={'stream': '0x730000', 'descriptors': '0x730100+', 'profiles': '0x734000+'},
                    runtime_routing=PERFECT_ROUTING['perfect_plex_attacker'], palette_owner='slot 12',
                    facing='canonical: attacker drawings unmirrored (Raw art faces right unflipped); '
                           'tools/canonical_perfect_geometry.py',
                    implementation={'branch': 'claude/charming-allen-njttcx', 'marker': 'PLEX-CANON2'},
                    evidence=['docs/perfect-plex-fix-report.md', 'docs/perfect-plex-exit.md', 'data/perfect-plex-exit.json',
                              'evidence/perfect-plex-exit/README.md',
                              'evidence/perfect-plex-receivers/fixed/verification.json',
                              'evidence/perfect-plex-receivers/fixed/undertaker-left-right-rope-before-after.gif',
                              'evidence/perfect-plex-receivers/fixed/undertaker-right-right-rope-before-after.gif',
                              'evidence/perfect-plex-receivers/fixed/undertaker-recovery-before-after.gif',
                              'evidence/perfect-plex-receivers/fixed/luna-generic-before-after.gif',
                              'evidence/mr-perfect-import/README.md',
                              'docs/perfect-plex-native-trace.md', 'docs/perfect-plex-gaps.md'],
                    aliases='private (tile IDs C000+ written per pose, no sharing with stock slots)',
                    defects=[EXIT_DIFFERENCES,
                             "Perfect's shadow is drawn green in every capture inspected, also outside the "
                             'Perfect-Plex (palette entry of the imported worker; not changed)'],
                    fixed=['PP-0 announcer bank-table stride (stock 3 MiB imports reach a match)',
                           'PP-1 side swap', 'PP-4 frozen Perfect-Plex pose after the move',
                           'PP-5 pin hold, release and both wrestlers\' recovery after the bridge (docs/perfect-plex-exit.md)']))
    for slot in range(13):
        royal = RAW_TO_ROYAL.get(slot)
        common = dict(source_game='Royal Rumble' if royal is not None else None,
                      palette_owner=f'slot {slot}',
                      runtime_routing=PERFECT_ROUTING['perfect_plex_receiver_released'])
        released = row(slot, 'finisher:Perfect-Plex', 'receiver', 'adapted_placeholder',
                       'verified_functional' if slot == 0 else 'untested',
                       source_ids={'raw_profiles': 'data/perfect-victim-layouts.json rows (stock receiving-suplex)'},
                       evidence=['data/perfect-victim-layouts.json', 'evidence/mr-perfect-import/verification.json'],
                       defects=['Generic Raw vertical-suplex parts; poses do not match Royal Perfect-Plex'],
                       variant='released v0.16.1', **{k: v for k, v in common.items() if k != 'source_game'},
                       source_game='WWF Raw')
        rows.append(released)
        recipes_all = [json.loads(r.read_text()) for r in sorted((ROOT / 'evidence/perfect-plex-receivers/recipes').glob('*.json'))]
        if royal is None or slot == 5:
            # Royal's receiving drawings rebuilt from the slot's own pixels (own art and gear). Slot 5 uses them when
            # Scott Hall's gear replaces Razor.
            own = [r for r in recipes_all if r['receiver_slot'] == slot and 'expected_build' in r
                   and (slot != 5 or 'gear' in r['scenario'])]
            gifs = [f"evidence/complete-wrestler-art/{r['scenario']}.gif" for r in own
                    if (ROOT / f"evidence/complete-wrestler-art/{r['scenario']}.gif").exists()]
            rows.append(row(slot, 'finisher:Perfect-Plex', 'receiver', 'own_art_adapted',
                            'verified_visual' if own else 'untested',
                            variant='target (Royal drawings in own pixels' + (', Scott Hall gear applied)' if slot == 5 else ')'),
                            implementation={'branch': 'claude/charming-allen-njttcx', 'marker': 'ROYAL-RX4',
                                            'source': 'editor/receiving-art.js reskin + recipes.reskin'},
                            source_ids={'plan': 'data/receiver-reskin-plan.json (tools/plan_receiver_reskin.py): '
                                                'per pixel of the Royal donor drawing, an own piece and offset'},
                            native={'scenarios': [r['scenario'] for r in own],
                                    'builds': sorted({r['expected_build'][:16] for r in own}),
                                    'preview_equals_native': 'every step, 100% of actor pixels'} if own else None,
                            aliases='private tiles per worker (RX3); editing one worker changes no other worker '
                                    '(tools/check_receiver_isolation.py)',
                            evidence=['docs/complete-wrestler-art.md', 'tools/verify_perfect_receivers_native.py']
                                     + ([] if slot == 5 else ['evidence/complete-wrestler-art/verification-stock-v5.json'])
                                     + (['evidence/complete-wrestler-art/verification-gear-mod-v5.json']
                                        if any('gear' in r['scenario'] for r in own) else [])
                                     + [f"evidence/perfect-plex-receivers/recipes/{r['scenario']}.json" for r in own] + gifs,
                            defects=["Automatic rebuild of Royal's drawings from the wrestler's own pixels; some regions "
                                     "are blotchy where the costume differs most from the donor's (awaiting visual review)",
                                     RECEIVER_EXIT, 'Not released; draft PR #1 for review'],
                            **common))
            if royal is None:
                continue
        worker = workers[royal]
        analysis = receivers_analysis['workers'][royal]
        if slot == 2:
            rows.append(row(slot, 'finisher:Perfect-Plex', 'receiver', 'prototype_private', 'defective',
                            variant='older Undertaker-only prototype (tools/build_perfect_receiver_prototype.py)',
                            evidence=['tools/build_perfect_receiver_prototype.py',
                                      'evidence/perfect-plex-receivers/raw-undertaker-prototype.gif',
                                      'evidence/perfect-plex-receivers/frame-review/README.md',
                                      'docs/perfect-plex-gaps.md', 'docs/perfect-plex-pair-coordinates.md'],
                            aliases='de-duplicates inserted tiles within this single receiver only',
                            defects=['Receiver largely hidden behind the attacker on lift frames (PP-2; cause open)',
                                     'Shadow appears detached from the body (PP-3; cause provisional)',
                                     'Apparent standing overlap after the bridge in this GIF (PP-4); native action '
                                     'state elsewhere is 70 (downed); build of this GIF not recorded',
                                     'Nearest-colour Royal->Raw palette remap not reviewed per region (PP-6)'],
                            **common))
        defects = ['WIP build on codex/perfect-receivers-wip (tools/build_perfect_receivers.py); not released; '
                   'no committed gameplay capture; editor isolation test not run',
                   'Nearest-colour Royal->Raw palette remap not reviewed per region (PP-6)']
        art, gameplay = 'prototype_private', 'untested'
        evidence = ['data/perfect-receivers.json', 'docs/perfect-plex-gaps.md']
        recipes = sorted((ROOT / 'evidence/perfect-plex-receivers/recipes').glob('*.json'))
        measured = [json.loads(r.read_text()) for r in recipes]
        measured = [r for r in measured if r['receiver_slot'] == slot and 'expected_build' in r and 'gear' not in r['scenario']]
        native = None
        if measured:
            gameplay = 'verified_visual'
            evidence = ['data/perfect-receivers.json', 'docs/perfect-plex-fix-report.md',
                        'evidence/complete-wrestler-art/verification-stock-v5.json',
                        'evidence/perfect-plex-receivers/fixed/verification.json',
                        'tools/verify_perfect_receivers_native.py']
            evidence += [f"evidence/perfect-plex-receivers/recipes/{r['scenario']}.json" for r in measured]
            if slot == 2:
                evidence += ['evidence/perfect-plex-receivers/fixed/undertaker-left-right-rope-before-after.gif',
                             'evidence/perfect-plex-receivers/fixed/undertaker-right-right-rope-before-after.gif',
                             'evidence/perfect-plex-receivers/fixed/undertaker-recovery-before-after.gif']
            errors = sorted({int(k) for r in measured for k in r['expected']['registration_errors']})
            native = {'scenarios': [r['scenario'] for r in measured], 'build_sha256': measured[0]['expected_build'],
                      'registration_error_px': errors,
                      'foreign_palette6_frames': sum(r['expected']['frames_with_foreign_palette6_during_move']
                                                     for r in measured),
                      'defect_baseline': 'recipes[].defect_baseline (WIP 2955d5c: PP-1/2/3/4/7)'}
            defects = ['Not released; draft PR #1 for Codex review',
                       RECEIVER_EXIT,
                       'Nearest-colour Royal->Raw palette remap not reviewed per region (PP-6)']
        if slot == 12:
            gameplay = 'untested'
            defects.append('Mirror match unreachable in one-on-one: P2 cannot pick the wrestler P1 chose (2P) and '
                           'the 1P "player chooses opponent" screen refuses the same wrestler; other modes untested')
        if slot == 5:
            defects.append('Royal Razor drawings are used only while slot 5 keeps its stock identity; with Scott '
                           "Hall's gear the slot uses its own native drawings (row above)")
        rows.append(row(slot, 'finisher:Perfect-Plex', 'receiver', art, gameplay,
                        variant='target (own receiving art): seven-counterpart build',
                        native=native,
                        implementation={'branch': 'claude/charming-allen-njttcx (from codex/perfect-receivers-wip '
                                                  '@ 2955d5c)', 'marker': 'ROYAL-RX4',
                                        'tile_allocation': 'per-slot private map, global ID counter and packet '
                                                           'cursor (code inspection only)'},
                        source_ids={'royal_selector': royal, 'royal_name': ROYAL_ROSTER[royal],
                                    'royal_component_poses': sorted({c['pose'] for r in receivers['components']
                                                                     for c in r['components']}),
                                    'source_frames': [p['source_frame'] for p in worker['poses']]},
                        anchors='data/perfect-receivers.json components[] (Royal OAM anchors, relative to x=145,y=162)',
                        facing='canonical: receiver drawings mirrored (MIRROR_SHIFT 2, body_dx 45, per-pose shadow_dx)',
                        budget={'max_objects_incl_shadow': analysis['max_objects'],
                                'max_tiles_incl_shadow': analysis['max_tiles']},
                        aliases={'royal_source_tiles': analysis['source_tiles'],
                                 'private_to_this_worker': analysis['private_tiles'],
                                 'shared_with_all_12_workers': analysis['shared_all'],
                                 'shared_with_some': analysis['shared_some'],
                                 'note': 'Royal ROM addresses; Raw insertion must give each slot private copies'},
                        evidence=evidence, defects=defects, **common))
    return rows


def ordinary_rows(manifest):
    rows = []
    known = {
        (1, 'idle_walk'): ('customized', 'verified_visual', ['evidence/bret-movement/README.md',
                                                              'evidence/bret-gear-anatomy/README.md']),
        (1, 'running'): ('customized', 'verified_visual', ['evidence/bret-movement/README.md']),
        (1, 'strikes'): ('customized', 'untested', ['evidence/action-mapping/README.md']),
        (7, 'idle_walk'): ('customized', 'verified_visual', ['evidence/sting/walk.gif']),
        (7, 'strikes'): ('customized', 'verified_visual', ['evidence/sting-rebuild/punch.gif',
                                                            'evidence/sting-rebuild/kick.gif']),
        (7, 'ropes'): ('customized', 'verified_visual', ['evidence/sting-rebuild/run-ropes.gif']),
        (7, 'grapples'): ('customized', 'verified_visual', ['evidence/sting-rebuild/give-vertical-suplex.gif',
                                                             'evidence/sting-rebuild/take-atomic-drop.gif']),
        (7, 'submissions'): ('customized', 'verified_visual', ['evidence/sting-rebuild/scorpion-deathlock.gif']),
    }
    for slot in (5, 9, 10):
        known[(slot, 'idle_walk')] = ('customized', 'verified_visual', ['evidence/nwo-gear/README.md'])
        known[(slot, 'strikes')] = ('customized', 'verified_visual', ['evidence/nwo-gear/README.md'])
    for slot in range(12):
        for cat in ORDINARY_CATEGORIES:
            art, gameplay, evidence = known.get((slot, cat), (
                'customized' if SLOTS[slot]['customization'] else 'original', 'untested', []))
            defects = [] if evidence else ['No action-to-frame map for this category']
            if slot == 1 and cat == 'strikes':
                defects.append('Punch/kick part IDs mapped in original outfit only')
            rows.append(row(slot, cat, 'performer_and_receiver', art, gameplay, source_game='WWF Raw',
                            runtime_routing=STOCK_ROUTING['primary_lookup'], palette_owner=f'slot {slot}',
                            aliases='stock directories share sources; see evidence/roster-inventory/secondary-graphics.md',
                            evidence=evidence, defects=defects))
    # Mr. Perfect ordinary pieces: only per-piece provenance is known, not per action.
    counts = defaultdict(int)
    for frame in manifest['frames']:
        counts[(frame['kind'], frame['royal'], frame['common'])] += 1
    pieces = {f'{k}_{"royal" if r else "raw"}{"_common" if c else ""}': n for (k, r, c), n in sorted(counts.items())}
    cov = manifest['coverage']
    pieces['royal_by_pose_match'] = cov.get('matched_royal_poses', 0)
    for cat in ORDINARY_CATEGORIES:
        rows.append(row(12, cat, 'performer_and_receiver', 'adapted_placeholder', 'untested',
                        source_game='Royal Rumble + adapted WWF Raw',
                        runtime_routing=PERFECT_ROUTING['primary_worker'], palette_owner='slot 12',
                        aliases='private copies (slot-12 tables 71:0000/71:1000); common-range pieces need audit',
                        piece_provenance=pieces,
                        evidence=['evidence/mr-perfect-import/README.md', 'editor/royal-import-layouts.js',
                                  'data/perfect-pose-matches.json'],
                        defects=[f"Per-action provenance not mapped; {cov['royal_poses']:,} Royal vs {cov['adapted_raw_poses']:,} adapted pieces overall",
                                 'Royal has no counterpart for several Raw-only actions (needs authored art)']))
    return rows


receivers_analysis = None


def build():
    global receivers_analysis
    moves = load('data/wrestler-move-coverage.json')
    receivers = load('data/perfect-receivers.json')
    receivers_analysis = analyse_receivers(receivers)
    text = (ROOT / 'editor/royal-import-layouts.js').read_text()
    manifest = json.loads(text[text.index('=') + 1:].strip().rstrip(';'))
    slots = []
    for s in SLOTS:
        entry = dict(s)
        royal = RAW_TO_ROYAL.get(s['slot'])
        entry['royal_counterpart'] = None if royal is None else {'selector': royal, 'name': ROYAL_ROSTER[royal]}
        entry['raw_selector_word'] = s['slot'] * 2
        entry['customization_evidence'] = exists(s.get('customization_evidence', []))
        slots.append(entry)
    rows = special_rows(moves) + perfect_plex_rows(receivers) + ordinary_rows(manifest)
    summary = defaultdict(lambda: defaultdict(int))
    for r in rows:
        summary[r['art_status']][r['gameplay_status']] += 1
    return {
        'schema_version': 1,
        'generated_by': 'tools/build_animation_coverage.py',
        'scope': 'Twelve original Raw slots plus Mr. Perfect. Derived from tracked evidence only; no ROM read.',
        'claim': 'Complete roster animation coverage is NOT established.',
        'art_statuses': ART_STATUSES,
        'gameplay_statuses': GAMEPLAY_STATUSES,
        'routing': {'stock': STOCK_ROUTING, 'perfect_slot': PERFECT_ROUTING},
        'slots': slots,
        'rows': rows,
        'perfect_plex_static_checks': receivers_analysis['findings'],
        'summary': {a: dict(g) for a, g in sorted(summary.items())},
    }


def report(data):
    out = ['# Animation coverage inventory', '',
           'Generated by `tools/build_animation_coverage.py` from tracked evidence; '
           'machine-readable source: [`data/animation-coverage.json`](../data/animation-coverage.json). '
           'Do not edit by hand.', '',
           f'**{data["claim"]}** Art provenance and gameplay verification are tracked separately. '
           '`not_audited`/`untested` mean no tracked evidence, not "probably fine".', '',
           '## Slots', '', '| Slot | Original | Display | Customization | Royal counterpart |',
           '| ---: | --- | --- | --- | --- |']
    for s in data['slots']:
        rc = s['royal_counterpart']
        out.append(f"| {s['slot']} | {s['original'] or '—'} | {s['display']} | {s['customization'] or '—'} | "
                   f"{'%s (%d)' % (rc['name'], rc['selector']) if rc else 'none'} |")
    out += ['', '## Status totals (art × gameplay)', '', '| Art | ' + ' | '.join(GAMEPLAY_STATUSES) + ' |',
            '| --- |' + ' ---: |' * len(GAMEPLAY_STATUSES)]
    for art, counts in data['summary'].items():
        out.append(f'| {art} | ' + ' | '.join(str(counts.get(g, 0)) for g in GAMEPLAY_STATUSES) + ' |')
    out += ['', '## Perfect-Plex receiving coverage', '',
            '| Slot | Display | Variant | Art | Gameplay | Royal source | Private/shared Royal tiles | Open defects |',
            '| ---: | --- | --- | --- | --- | --- | --- | --- |']
    for r in data['rows']:
        if r['action'] != 'finisher:Perfect-Plex':
            continue
        src = r.get('source_ids', {})
        al = r['aliases'] if isinstance(r['aliases'], dict) else None
        tiles = f"{al['private_to_this_worker']}/{al['royal_source_tiles']}" if al else '—'
        royal = f"{src['royal_name']} ({src['royal_selector']})" if 'royal_name' in src else '—'
        out.append(f"| {r['slot']} | {r['display_name']} | {r.get('variant', r['role'])} | {r['art_status']} | "
                   f"{r['gameplay_status']} | {royal} | {tiles} | {'; '.join(r['defects']) or '—'} |")
    out += ['', 'The performer row is listed first (slot 12, `variant` = performer).', '',
            '## Stock finishers and Mega Moves', '', '| Slot | Display | Action | Role | Art | Gameplay | Open defects |',
            '| ---: | --- | --- | --- | --- | --- | --- |']
    for r in data['rows']:
        if r['action'].startswith(('finisher:', 'mega_move:')) and r['action'] != 'finisher:Perfect-Plex':
            out.append(f"| {r['slot']} | {r['display_name']} | {r['action']} | {r['role']} | {r['art_status']} | "
                       f"{r['gameplay_status']} | {'; '.join(r['defects']) or '—'} |")
    out += ['', '## Ordinary actions', '',
            'Rows are per category, not per pose: no complete action-to-frame map exists yet for any slot. ',
            '', '| Slot | ' + ' | '.join(ORDINARY_CATEGORIES) + ' |', '| ---: |' + ' --- |' * len(ORDINARY_CATEGORIES)]
    grid = defaultdict(dict)
    for r in data['rows']:
        if r['action'] in ORDINARY_CATEGORIES:
            grid[r['slot']][r['action']] = r
    abbreviation = {'verified_visual': 'V', 'verified_functional': 'F', 'defective': 'D', 'untested': '?'}
    for slot in sorted(grid):
        out.append(f'| {slot} {SLOTS[slot]["display"]} | ' + ' | '.join(
            f"{grid[slot][c]['art_status']} {abbreviation[grid[slot][c]['gameplay_status']]}"
            for c in ORDINARY_CATEGORIES) + ' |')
    out += ['', 'V = verified visually in native gameplay, F = functional only, D = defective, ? = untested.', '',
            '## Static Perfect-Plex receiver checks', '',
            'From `tools/check_perfect_receivers.py` (ROM-free, over `data/perfect-receivers.json`):', '']
    out += [f'- **{f["id"]}** ({f["severity"]}): {f["summary"]}' for f in data['perfect_plex_static_checks']]
    out += ['', 'See [perfect-plex-gaps.md](perfect-plex-gaps.md) for the prioritized gap list.', '']
    return '\n'.join(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='fail if committed outputs differ')
    args = parser.parse_args()
    data = build()
    outputs = {ROOT / 'data/animation-coverage.json': json.dumps(data, indent=1) + '\n',
               ROOT / 'docs/animation-coverage.md': report(data)}
    stale = [p for p, text in outputs.items() if not p.exists() or p.read_text() != text]
    if args.check:
        if stale:
            sys.exit('Stale coverage outputs: ' + ', '.join(str(p.relative_to(ROOT)) for p in stale))
        print('Coverage outputs up to date')
    else:
        for path, text in outputs.items():
            path.write_text(text)
        print(f'{len(data["rows"])} rows; summary {json.dumps(data["summary"])}')
