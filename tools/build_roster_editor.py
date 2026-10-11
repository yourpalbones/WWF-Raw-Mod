"""Build address-only layouts for the 12 verified stock roster characters."""
import argparse
import json
from pathlib import Path
from build_editor_manifest import build
from build_bret_gear import ORIGINAL_HASH

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('rom', type=Path)
parser.add_argument('--capture-root', type=Path, required=True)
parser.add_argument('--movement-root', type=Path, required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[1]
rom = args.rom.read_bytes()
characters, sources = [], {}
for case in json.loads((repo / 'evidence/roster-inventory/identities.json').read_text())['characters']:
    selector = case['selector']
    root = args.movement_root / str(selector)
    snapshots = [(f'Movement sample {p.stem.split("-")[1]}', p.with_suffix(''))
                 for p in sorted(root.glob('frame-*.png')) if int(p.stem.split('-')[1]) >= 30]
    seed = [args.capture_root / case['trace_folder']]
    if selector == 1:
        snapshots = [('Standing', args.capture_root / 'emulator-coldboot/frame-002940')] + [
            (f'Walk sample {i + 1}', p.with_suffix('')) for i, p in enumerate(
                sorted((args.capture_root / 'gear-walk-original').glob('frame-*.png'))[:15])]
    if not snapshots:
        raise ValueError(f'No captures for {case["character"]}')
    character = build(rom, snapshots, case['character'], 0x2CC4DA + selector * 32, seed)
    character['id'] = str(selector)
    for key, source in character['sources'].items():
        if key in sources and sources[key] != source:
            raise ValueError('Conflicting source metadata')
        sources[key] = source
    characters.append(character)
    print(case['character'], len(character['poses']), len(character['sources']))
manifest = {'version': 2, 'original_sha256': ORIGINAL_HASH, 'characters': characters, 'sources': sources}
(repo / 'editor/roster-layouts.js').write_text('window.RAW_EDITOR_MANIFEST = ' + json.dumps(manifest, indent=2) + ';\n')
