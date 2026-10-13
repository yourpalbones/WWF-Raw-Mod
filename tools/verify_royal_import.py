"""Exercise adding, editing, exporting and reopening the independent Raw slot."""
import argparse
import io
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('raw', type=Path)
parser.add_argument('royal', type=Path)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--page', default='editor/gear-workshop.html')
parser.add_argument('--offline', action='store_true', help='Open the standalone HTML directly with file://')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
args.output.mkdir(parents=True, exist_ok=True)
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(root)))
threading.Thread(target=server.serve_forever, daemon=True).start()

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto((root/args.page).as_uri() if args.offline else f'http://127.0.0.1:{server.server_port}/{args.page}')
    page.locator('#rom').set_input_files(str(args.raw.resolve()))
    page.wait_for_function('rom!==null')
    snapshot = '''Object.fromEntries(C.characters.filter(c=>c.id!=='12').map(c=>[c.id,{
      bio:selectionState(c.id).bio,palette:Array.from(rom.slice(c.palette_offset,c.palette_offset+32)),
      hud:Array.from(originalHUD(c.id)),theme:profileState(c.id).theme,
      portrait:selectionState(c.id).portrait.pixels}]))'''
    original = page.evaluate(snapshot)
    # A wrong donor must be rejected without changing the loaded Raw ROM.
    page.locator('#royal-rom').set_input_files(str(args.raw.resolve()))
    page.wait_for_function("document.getElementById('royal-status').textContent.includes('Choose the unmodified')")
    assert page.evaluate('royalSource===null&&C.characters.length===12')
    page.locator('#royal-rom').set_input_files(str(args.royal.resolve()))
    page.wait_for_function('royalSource!==null')
    with page.expect_download() as download:
        page.locator('#royal-add').click()
    imported = args.output/'perfect-imported.sfc'
    download.value.save_as(imported)
    page.wait_for_function("M.id==='12'&&C.characters.length===13")
    assert len(imported.read_bytes()) == 0x800000
    assert page.evaluate(snapshot) == original
    assert page.evaluate("selectionState('12').bio.name") == 'MR PERFECT'
    assert page.evaluate('M.poses.length') == 1732
    assert page.locator('#royal-add').is_disabled()
    page.screenshot(path=str(args.output/'editor-import.png'), full_page=True)

    # Exercise real packet growth: preserve the silhouette, add color detail,
    # then import that rendered PNG through the same path used by the UI.
    growth = page.evaluate('''(()=>{
      for(const [key,source]of Object.entries(M.sources)){
        if(!source.pointer_offsets?.length)continue;
        const tile=originals[key].map((v,i)=>v?1+(i*7)%15:0);
        if(encode(tile,source.compressed).length<=source.length)continue;
        const pose=M.poses.findIndex(p=>p.parts.some(part=>part.tiles.includes(key)));
        if(pose<0)continue;
        document.getElementById('pose').value=String(pose);edits[key]=tile;render();
        importPosePixels(ctx.getImageData(0,0,canvas.width,canvas.height).data,canvas.width,canvas.height);
        return {key,offset:source.offset,length:source.length,pointers:source.pointer_offsets,pixels:tile};
      }throw Error('No growing packet exercised');
    })()''')
    page.locator('#tab-profile').click()
    rgba = page.evaluate("Array.from(document.getElementById('portrait').getContext('2d').getImageData(0,0,128,120).data)")
    photo = Image.frombytes('RGBA', (128,120), bytes(rgba))
    ImageDraw.Draw(photo).rectangle((0,0,7,7), fill=(255,0,255,255))
    buffer = io.BytesIO()
    photo.save(buffer, format='PNG')
    page.locator('#portrait-import').set_input_files({'name':'perfect-photo.png','mimeType':'image/png','buffer':buffer.getvalue()})
    page.wait_for_function("Boolean(selectionEdits['12']?.portrait&&selectionEdits['12']?.monitor)")
    expected_photo = page.evaluate("selectionState('12').portrait")
    expected_monitor = page.evaluate("profileState('12').monitor")
    theme = page.evaluate("Array.from(document.getElementById('theme-choice').options).find(o=>Number(o.value)!==profileState('12').theme).value")
    page.locator('#theme-choice').select_option(theme)
    page.locator('#theme-apply').click()
    for field, value in {'name':'CURT HENNIG','from':'DULUTH','weight':'257','height':'6\'4"','special':'PERFECT-\nPLEX'}.items():
        page.locator('#bio-'+field).fill(value)
    page.locator('#bio-apply').click()
    assert page.evaluate("selectionEdits['12'].bio.name") == 'CURT HENNIG'
    palette_at=page.evaluate('M.palette_offset')
    page.evaluate("palettes['12']={1:31};render();")
    with page.expect_download() as download:
        page.locator('#save').click()
    project = Path(download.value.path()).read_bytes()
    expected = page.evaluate('({edits,palettes,selectionEdits})')
    page.locator('#reset').click()
    page.locator('#project').set_input_files({'name':'perfect-project.json','mimeType':'application/json','buffer':project})
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Project loaded')")
    assert page.evaluate('({edits,palettes,selectionEdits})') == expected
    page.locator('#tab-export').click()
    with page.expect_download() as download:
        page.locator('#rom-export').click()
    edited = args.output/'perfect-edited.sfc'
    download.value.save_as(edited)
    data = edited.read_bytes()
    pointer = int.from_bytes(data[growth['pointers'][0]:growth['pointers'][0]+3], 'little')
    assert pointer != growth['offset'] and 0x750000 <= pointer < 0x7d0000
    for offset in growth['pointers']:
        assert int.from_bytes(data[offset:offset+3], 'little') == pointer
    assert int.from_bytes(data[palette_at+2:palette_at+4], 'little') == 31
    page.locator('#rom').set_input_files(str(edited.resolve()))
    page.wait_for_function('rom!==null&&C.characters.length===13')
    page.locator('#wrestler').select_option('12')
    assert page.evaluate(snapshot) == original
    assert page.evaluate("selectionState('12').bio.name") == 'CURT HENNIG'
    assert page.evaluate("selectionState('12').bio.from") == 'DULUTH'
    assert page.evaluate("selectionState('12').portrait.pixels") == expected_photo['pixels']
    assert page.evaluate("selectionState('12').portrait.colors") == expected_photo['colors']
    assert page.evaluate("profileState('12').monitor") == expected_monitor
    assert page.evaluate("profileState('12').theme") == int(theme)
    assert page.evaluate('(key)=>originals[key]', str(pointer)) == growth['pixels']
    assert not errors, errors
    report = {'slot_count':13,'piece_count':1732,'original_twelve_preserved':True,
              'wrong_donor_rejected':True,'project_roundtrip':True,'edited_rom_reopened':True,
              'sprite_packet_relocated':True,'portrait_and_monitor_roundtrip':True,
              'theme_reassigned':True,'offline_file':args.offline,'page_errors':errors}
    (args.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    browser.close()
server.shutdown()
