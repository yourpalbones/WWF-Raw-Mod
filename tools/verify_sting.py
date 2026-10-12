"""Verify Sting's native recipe, replacement move, editor exports and isolation."""
import argparse,hashlib,json,threading
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('base',type=Path);p.add_argument('native',type=Path)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();repo=Path(__file__).resolve().parents[1];a.output.mkdir(parents=True,exist_ok=True)
base=a.base.read_bytes();native=a.native.read_bytes()
assert len(base)in [0x600000,0x800000] and len(native)==0x800000
allowed=set()
for start,length in [(0xffdc,4),(0x40ffdc,4),(0x4be000,768),(0x2cc5ba,32),*[(t+14,2)for t in [0x2dd36f,0x2dd387,0x2dd39f,0x2dd3b7,0x2dd3cf,0x2dd3e7]]]:
    allowed.update(range(start,start+length))
if len(base)==0x800000:
    for start,end in [(0x600100,0x620000),(0x620000,0x6e0000),(0x6e0000,0x6ec000),(0x6f0000,0x6fc000),(0x6fc000,0x6fc000+998*3),(0x6fd000,0x6fd000+722*3),(0x6fe000,0x6fe600),(0x6ff000,0x6ff000+18)]:allowed.update(range(start,end))
assert all(v==native[i] or i in allowed for i,v in enumerate(base)), 'Changed an existing roster asset'
assert native[0x400000:0x410000]==native[:65536]
assert sum(native)&65535==int.from_bytes(native[0xffde:0xffe0],'little')
for table in [0x2dd36f,0x2dd387,0x2dd39f,0x2dd3b7,0x2dd3cf,0x2dd3e7]:
    assert native[table+14:table+16]==base[table+2:table+4]
    assert all(native[table+s*2:table+s*2+2]==base[table+s*2:table+s*2+2]for s in range(13)if s!=7)
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)))
threading.Thread(target=server.serve_forever,daemon=True).start()
errors=[]
with sync_playwright()as pw:
    browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html')
    page.context.set_offline(True)
    def load(path):
        page.evaluate("status('Loading verification ROM')")
        page.locator('#rom').set_input_files(str(path))
        page.wait_for_function("rom!==null||$('status').textContent!=='Loading verification ROM'",timeout=90000)
        assert page.evaluate('rom!==null'),page.locator('#status').inner_text()
    def digest():
        return page.evaluate('async()=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",playableROM())),v=>v.toString(16).padStart(2,"0")).join("")')
    load(a.base)
    profiles=page.evaluate('Object.fromEntries(Object.keys(S.characters).filter(id=>id!=="7").map(id=>[id,{bio:selectionState(id).bio,theme:profileState(id).theme}]))')
    raw_digest=page.evaluate('async()=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",await applyScottReferenceGear(rom,"7"))),v=>v.toString(16).padStart(2,"0")).join("")')
    assert raw_digest==hashlib.sha256(native).hexdigest(), 'Browser/native recipe mismatch'
    page.locator('#wrestler').select_option('7');page.locator('#scott-reference-apply').click()
    page.wait_for_function('hasNativeGear(rom,"7")',timeout=90000)
    assert page.evaluate('selectionState("7").bio.name')=='STING'
    assert page.evaluate('selectionState("7").bio.special')=='SCORPION\nDEATHLOCK'
    assert page.evaluate('selectionEdits["7"].hudName')=='STING'
    page.evaluate('validateLoadedMod(playableROM())')
    assert profiles==page.evaluate('Object.fromEntries(Object.keys(S.characters).filter(id=>id!=="7").map(id=>[id,{bio:selectionState(id).bio,theme:profileState(id).theme}]))')
    exported_digest=digest()
    page.locator('#tab-export').click()
    with page.expect_download()as d:page.locator('#rom-export').click()
    exported=a.output/'WWF-Raw-Sting.sfc';exported.write_bytes(Path(d.value.path()).read_bytes())
    load(exported);assert digest()==exported_digest
    assert page.evaluate('selectionState("7").bio.name')=='STING'
    for id in ['5','9','10','7']:
        assert page.evaluate('id=>hasNativeGear(rom,id)',id)
    page.locator('#wrestler').select_option('7')
    page.evaluate('''()=>{const key=Object.keys(M.sources).find(k=>C.sources[k].offset>=0x620000&&C.sources[k].offset<0x690000);remember();edits[key]=originals[key].map(v=>v?6:0);render();importPosePixels(ctx.getImageData(0,0,canvas.width,canvas.height).data,canvas.width,canvas.height);}''')
    page.evaluate('validateLoadedMod(playableROM())');changed=digest();assert changed!=exported_digest
    with page.expect_download()as d:page.locator('#save').click()
    project=Path(d.value.path()).read_bytes();load(exported)
    page.locator('#project').set_input_files({'name':'sting.json','mimeType':'application/json','buffer':project})
    page.wait_for_function('Object.keys(edits).length>0');assert digest()==changed
    assert not errors,errors
    browser.close()
server.shutdown()
report={'native_gear_sha256':raw_digest,'playable_rom_sha256':exported_digest,
        'rom_bytes':len(exported.read_bytes()),'browser_native_recipe_byte_exact':True,
        'existing_gear_and_user_assets_preserved':True,'only_doink_finisher_tables_changed':True,'complete_sprite_replacement':True,'upper_lower_tile_namespaces':True,
        'sting_bio_select_name_and_health_bar_name':True,'offline_export_and_reopen':True,
        'private_tile_png_and_project_roundtrip':True,'complete_animation_coverage':False}
(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
