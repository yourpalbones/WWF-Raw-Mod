"""Check old Sting3 mods in the current editor against archived native snapshots.

Extracts only the four PPU snapshot files for each preserved captured pose.
The old ROM remains private, and no recipe or sprite layout is changed.
"""
import argparse
import hashlib
import json
import tarfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright
from extract_oam import objects

ROOT = Path(__file__).resolve().parents[1]
SUFFIXES = ['vram', 'oam', 'cgram', 'registers']


def old_manifest():
    source = (ROOT / 'editor/legacy-gear-layouts.js').read_text()
    data = json.loads(source.split('=', 1)[1].strip().removesuffix(';'))
    return next(v for v in data['7'] if v['signature'] == 'STING-NATIVE-GEAR3')


def prepare(manifest, archives, destination):
    poses = [p for p in manifest['poses'] if p['category'] == 'captured']
    assert len(poses) == 101
    wanted = {p['capture'] + '-' + suffix + '.bin' for p in poses for suffix in SUFFIXES}
    found = {}
    total = 0
    for archive in archives:
        with tarfile.open(archive) as source:
            # Path components from the archive are never extracted wholesale.
            for member in source.getmembers():
                if not member.isfile():
                    continue
                tail = '/'.join(Path(member.name).parts[-2:])
                if tail not in wanted:
                    continue
                assert tail not in found, ('Duplicate snapshot', tail)
                payload = source.extractfile(member).read()
                assert len(payload) == member.size
                total += len(payload)
                assert total < 20 * 1024 * 1024, 'Snapshot extraction exceeded bounded size'
                target = destination / 'snapshots' / tail
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    assert target.read_bytes() == payload, ('Existing snapshot differs', target)
                else:
                    target.write_bytes(payload)
                found[tail] = {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
    assert set(found) == wanted, ('Missing archived native snapshots', sorted(wanted - set(found)))
    report = {'captured_poses': len(poses), 'snapshot_files': len(found), 'snapshot_bytes': total,
              'only_vram_oam_cgram_registers_extracted': True, 'snapshots': found}
    (destination / 'snapshot-extraction.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check(args, manifest, extraction):
    source_rom = args.rom.read_bytes()
    assert len(source_rom) == 0x800000
    assert source_rom[0x6ff000:0x6ff000 + len(manifest['signature'])] == manifest['signature'].encode()
    source_digest = hashlib.sha256(source_rom).hexdigest()
    poses = [p for p in manifest['poses'] if p['category'] == 'captured']
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
            page = browser.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html')
            page.context.set_offline(True)
            assert page.evaluate('RAW_NWO_GEAR_PATTERNS["7"].signature') == 'STING-NATIVE-GEAR4', 'Final Sting4 editor bundle is not ready'
            assert page.evaluate('RAW_STING_MANIFEST.signature') == 'STING-NATIVE-GEAR4'

            def load(path):
                page.evaluate("rom=null;status('Loading legacy verification ROM')")
                page.locator('#rom').set_input_files(str(path))
                page.wait_for_function("rom!==null||$('status').textContent!=='Loading legacy verification ROM'", timeout=90000)
                assert page.evaluate('rom!==null'), page.locator('#status').inner_text()

            def playable_digest():
                return page.evaluate('async()=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",playableROM())),v=>v.toString(16).padStart(2,"0")).join("")')

            load(args.rom)
            assert playable_digest() == source_digest, 'Loading changed the old edited mod'
            page.locator('#wrestler').select_option('7')
            assert page.evaluate('nativeGearRevision(rom,"7")') == 3
            assert not page.evaluate('hasNativeGear(rom,"7")')
            assert page.locator('#scott-reference-apply').is_enabled(), 'Old Sting3 mod cannot upgrade through the editor'
            active_poses = page.evaluate('M.poses')
            assert len(active_poses) == len(manifest['poses'])
            captured_indices = [(i, p) for i, p in enumerate(active_poses) if p['category'] == 'captured']
            assert [p['capture'] for i, p in captured_indices] == [p['capture'] for p in poses]
            verified = []
            for index, pose in captured_indices:
                prefix = args.output / 'snapshots' / pose['capture']
                read = lambda suffix: Path(str(prefix) + '-' + suffix + '.bin').read_bytes()
                parts = [(r, im) for r, im in objects(read('vram'), read('oam'), read('cgram'), read('registers')[0x2101])
                         if r['palette'] == 0 and 0 <= r['y'] < 190 and -20 <= r['x'] < 256 and im.getbbox()]
                assert parts, pose['capture']
                left, top = min(r['x'] for r, im in parts), min(r['y'] for r, im in parts)
                expected = Image.new('RGBA', (pose['width'], pose['height']))
                for record, image in reversed(parts):
                    expected.alpha_composite(image, (record['x'] - left, record['y'] - top))
                actual = bytes(page.evaluate('i=>{$("pose").value=i;render();return Array.from(ctx.getImageData(0,0,canvas.width,canvas.height).data)}', index))
                assert actual == expected.tobytes(), ('Legacy preview differs from actual native PPU', pose['capture'])
                verified.append(pose['capture'])
            assert len(verified) == 101
            # The unchanged exported bytes cover custom sequences, assignments,
            # stock samples, names, portraits and all existing gear together.
            assert playable_digest() == source_digest
            page.locator('#tab-export').click()
            with page.expect_download() as pending:
                page.locator('#rom-export').click()
            exported = Path(pending.value.path()).read_bytes()
            assert exported == source_rom, 'Save & play changed an unedited legacy mod'
            saved = args.output / 'legacy-roundtrip.sfc'
            saved.write_bytes(exported)
            load(saved)
            assert playable_digest() == source_digest
            page.locator('#wrestler').select_option('7')
            assert page.locator('#scott-reference-apply').is_enabled()
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
    result = {'old_rom_sha256': source_digest, 'old_sting_revision_detected': 3,
              'current_editor_sting_revision': 4, 'legacy_full_manifest_selected': True,
              'captured_legacy_previews_pixel_exact_against_native_ppu': len(verified),
              'legacy_preview_captures': verified, 'upgrade_button_enabled': True,
              'offline_load_save_reopen_byte_exact': True,
              'custom_midi_samples_profiles_and_existing_gear_preserved': True,
              'custom_midi_allocation_sha256': hashlib.sha256(source_rom[0x3c0000:0x400000]).hexdigest(),
              'snapshot_files_extracted': extraction['snapshot_files'],
              'snapshot_bytes_extracted': extraction['snapshot_bytes'],
              'complete_live_animation_coverage_verified': False, 'visual_likeness_verified': False}
    (args.output / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('replays_archive', type=Path)
    parser.add_argument('grapples_archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = old_manifest()
    extraction = prepare(manifest, [args.replays_archive, args.grapples_archive], args.output)
    if args.prepare_only:
        print(json.dumps({key: value for key, value in extraction.items() if key != 'snapshots'}, indent=2))
    else:
        check(args, manifest, extraction)
