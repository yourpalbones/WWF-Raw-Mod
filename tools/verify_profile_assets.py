"""Verify independent monitor photos, name artwork, native themes and projects."""
import argparse,io,json,threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from decode_graphics import decode_block
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom',type=Path);parser.add_argument('--edited-rom',type=Path);parser.add_argument('--output',type=Path,default=Path('outputs/profile-assets-proof'));args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
repo=Path(__file__).resolve().parents[1];server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)));threading.Thread(target=server.serve_forever,daemon=True).start();rom=args.rom.read_bytes()
def planar(data,width,height,bpp):
 return [sum(((data[((y//8)*(width//8)+x//8)*bpp*8+(p//2)*16+(y%8)*2+p%2]>>(7-x%8))&1)<<p for p in range(bpp)) for y in range(height) for x in range(width)]
def logo_pixels(data,tilemap):
 output=[0]*(256*224)
 for t in range(896):
  word=int.from_bytes(tilemap[t*2:t*2+2],'little');tile=word&1023;pixels=planar(data[tile*32:tile*32+32],8,8,4)
  for y in range(8):
   for x in range(8):output[(t//32*8+y)*256+t%32*8+x]=pixels[(7-y if word&0x8000 else y)*8+(7-x if word&0x4000 else x)]
 return output
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1200,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html');page.locator('#rom').set_input_files(str(args.rom));page.wait_for_function('rom!==null');page.locator('#tab-profile').click();characters=page.evaluate('C.characters');expected={}
 for character in characters:
  id=character['id'];page.locator('#wrestler').select_option(id);meta=page.evaluate('S.characters[M.id]');original=page.evaluate('originalProfileAssets(M.id)');data,_=decode_block(rom,meta['monitor_offset']);assert original['monitor']['pixels']==planar(data,48,48,8)
  page.locator('#bio-apply').click();assert page.evaluate('selectionEdits[M.id].bio')==page.evaluate('originalSelection(M.id).bio')
  data,_=decode_block(rom,meta['logo_offset']);tilemap,_=decode_block(rom,meta['logo_map_offset']);assert original['logo']['pixels']==logo_pixels(data,tilemap)
  # Real PNG upload, distinctive replacement marker; preserve the original main portrait.
  image=Image.frombytes('RGBA',(48,48),bytes(page.evaluate('Array.from(document.getElementById("monitor").getContext("2d").getImageData(0,0,48,48).data)')));ImageDraw.Draw(image).rectangle((0,0,9,9),fill=(255,0,255,255));buf=io.BytesIO();image.save(buf,format='PNG');page.locator('#monitor-import').set_input_files({'name':'monitor.png','mimeType':'image/png','buffer':buf.getvalue()});page.wait_for_function('(id)=>Boolean(selectionEdits[id]?.monitor)',arg=id)
  name='TEST '+['ALPHA','BRAVO','CHARLIE','DELTA','ECHO','FOXTROT','GOLF','HOTEL','INDIA','JULIET','KILO','LIMA'][int(id)];page.locator('#bio-name').fill(name);page.locator('#bio-apply').click();assert page.evaluate('selectionEdits[M.id].logoName')==name
  theme=page.evaluate('S.characters[String((Number(M.id)+1)%12)].theme');page.locator('#theme-choice').select_option(str(theme));page.locator('#theme-apply').click();expected[id]=page.evaluate('({meta:S.characters[M.id],state:profileState(M.id),bio:selectionState(M.id).bio})')
 # Main-portrait copy and isolated restore/undo.
 saved=page.evaluate('selectionEdits');page.locator('#monitor-copy').click();assert page.evaluate('selectionEdits[M.id].monitor')!=saved[id]['monitor'];page.locator('#undo').click();assert page.evaluate('selectionEdits')==saved
 page.locator('#theme-restore').click();assert page.evaluate('profileState(M.id).theme')==page.evaluate('S.characters[M.id].theme');page.locator('#undo').click()
 with page.expect_download() as d:page.locator('#save').click()
 project=Path(d.value.path()).read_bytes();assert json.loads(project)['version']==7
 page.locator('#reset').click();page.locator('#project').set_input_files({'name':'project.json','mimeType':'application/json','buffer':project});page.wait_for_function('Object.keys(selectionEdits).length===12');assert page.evaluate('selectionEdits')==saved
 legacy=json.loads(project);legacy['version']=4
 for e in legacy['selection_edits'].values():
  for key in ['monitor','logoName','theme']:e.pop(key,None)
 page.locator('#project').set_input_files({'name':'old-v4.json','mimeType':'application/json','buffer':json.dumps(legacy).encode()});page.wait_for_function("document.getElementById('status').textContent.startsWith('Project loaded')");assert page.evaluate('selectionEdits[M.id].logoName')==legacy['selection_edits'][id]['bio']['name']
 page.locator('#project').set_input_files({'name':'project.json','mimeType':'application/json','buffer':project});page.wait_for_function('Boolean(selectionEdits[M.id].monitor)')
 invalid=json.loads(project);invalid['selection_edits']['1']['theme']=999
 page.locator('#project').set_input_files({'name':'invalid.json','mimeType':'application/json','buffer':json.dumps(invalid).encode()});page.wait_for_function("document.getElementById('status').textContent.includes('Invalid theme')");assert page.evaluate('selectionEdits')==saved
 # Over-detailed logo import must fail atomically.
 image=Image.new('RGBA',(256,224));image.putdata([((x*17+y*31)%256,(x*47+y*13)%256,(x*29+y*53)%256,255) for y in range(224) for x in range(256)]);buf=io.BytesIO();image.save(buf,format='PNG');page.locator('#logo-import').set_input_files({'name':'detailed.png','mimeType':'image/png','buffer':buf.getvalue()});page.wait_for_function("document.getElementById('status').textContent.includes('Simplify')");assert page.evaluate('selectionEdits')==saved
 # An authored simple transparent logo can be uploaded too, then undone.
 image=Image.new('RGBA',(256,224));ImageDraw.Draw(image).rectangle((80,80,160,140),fill='white');buf=io.BytesIO();image.save(buf,format='PNG');page.locator('#logo-import').set_input_files({'name':'simple.png','mimeType':'image/png','buffer':buf.getvalue()});page.wait_for_function('Boolean(selectionEdits[M.id].logo)');assert page.evaluate('selectionEdits[M.id].logoName') is None;page.locator('#undo').click();assert page.evaluate('selectionEdits')==saved
 page.locator('#tab-export').click()
 with page.expect_download() as d:page.locator('#rom-export').click()
 result=Path(d.value.path()).read_bytes();assert len(result)==0x400000;assert sum(result)&65535==int.from_bytes(result[0xffde:0xffe0],'little')
 for id,case in expected.items():
  meta=case['meta'];state=case['state'];record=meta['record'];ptr=lambda o:int.from_bytes(result[record+o:record+o+3],'little')&0x3fffff
  data,_=decode_block(result,ptr(20));assert planar(data,48,48,8)==state['monitor']['pixels'];assert result[ptr(24):ptr(24)+64]==b''.join(c.to_bytes(2,'little')for c in state['monitor']['colors'])
  data,_=decode_block(result,ptr(8));tilemap,_=decode_block(result,ptr(12));assert logo_pixels(data,tilemap)==state['logo']['pixels'];assert result[ptr(16):ptr(16)+32]==b''.join(c.to_bytes(2,'little')for c in state['logo']['colors']);assert result[meta['theme_offset']]==state['theme'];assert result[meta['monitor_directory_offset']:meta['monitor_directory_offset']+3]==result[record+20:record+23];assert result[meta['monitor_palette_directory_offset']:meta['monitor_palette_directory_offset']+3]==result[record+24:record+27]
  assert result[meta['announcer_monitor_word']:meta['announcer_monitor_word']+2]==result[record+20:record+22];assert result[meta['announcer_monitor_bank']]==result[record+22];assert result[meta['announcer_palette_word']:meta['announcer_palette_word']+2]==result[record+24:record+26];assert result[meta['announcer_palette_bank']]==result[record+26]
  assert result[record:record+8]==rom[record:record+8] # main portrait and palette unchanged
 # Invalid edited ROMs must leave the current project intact.
 bad=bytearray(result);bad[0x100]^=1
 page.locator('#recover-rom').set_input_files({'name':'corrupt.sfc','mimeType':'application/octet-stream','buffer':bytes(bad)});page.wait_for_function("document.getElementById('status').textContent.includes('checksum is invalid')");assert page.evaluate('selectionEdits')==saved
 checksum=sum(bad)&65535;bad[0xffdc:0xffe0]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
 page.locator('#recover-rom').set_input_files({'name':'unsupported.sfc','mimeType':'application/octet-stream','buffer':bytes(bad)});page.wait_for_function("document.getElementById('status').textContent.includes('changes the editor cannot recover')");assert page.evaluate('selectionEdits')==saved
 # Recover the actual exported ROM through the file picker and export it again.
 page.locator('#recover-rom').set_input_files({'name':'edited.sfc','mimeType':'application/octet-stream','buffer':result});page.wait_for_function("document.getElementById('status').textContent.startsWith('Edits recovered')")
 assert page.evaluate('Array.from(playableROM())')==list(result)
 if args.edited_rom:
  page.locator('#recover-rom').set_input_files(str(args.edited_rom));page.wait_for_function("document.getElementById('status').textContent.startsWith('Edits recovered')")
  recovered=page.evaluate('({profiles:selectionEdits,tiles:Object.keys(edits).length,colors:palettes})')
  assert recovered['profiles']['5']['bio']['name']=='SCOTT HALL' and recovered['profiles']['9']['bio']['name']=='SYXX' and recovered['profiles']['10']['bio']['name']=='KEVIN NASH'
  assert len([e for e in recovered['profiles'].values() if 'portrait' in e])==7
  (args.output/'recovered-project.json').write_text(page.evaluate('JSON.stringify({version:7,original_sha256:C.original_sha256,edits,palettes,selection_edits:selectionEdits})'))
  (args.output/'recovered-test.sfc').write_bytes(bytes(page.evaluate('Array.from(playableROM())')))
  page.locator('#tab-profile').click();page.locator('#wrestler').select_option('5');page.locator('#monitor-copy').click();page.screenshot(path=str(args.output/'recovered-workshop.png'),full_page=True)
  page.locator('#project').set_input_files({'name':'project.json','mimeType':'application/json','buffer':project});page.wait_for_function('Boolean(selectionEdits[M.id].monitor)')
 (args.output/'profile-test.sfc').write_bytes(result);(args.output/'expected.json').write_text(json.dumps(expected))
 page.locator('#tab-profile').click();page.locator('#wrestler').select_option('5');page.screenshot(path=str(args.output/'workshop.png'),full_page=True)
 assert not errors,errors;browser.close()
server.shutdown();(args.output/'verification.json').write_text(json.dumps({'original_monitor_decodes':12,'original_logo_decodes':12,'monitor_import_roundtrips':12,'generated_logo_roundtrips':12,'theme_assignments':12,'main_portraits_preserved':True,'version7_reload_undo':True,'version4_name_art_migration':True,'invalid_theme_and_logo_refusal':True,'expanded_rom_checksum':True,'edited_rom_recovery_roundtrip':True,'unsupported_rom_recovery_atomic':True,'uploaded_rom_recovery':bool(args.edited_rom)},indent=2)+'\n');print('All 12 monitor photos, native name artwork, theme assignments, imports, project compatibility and export checks passed')
