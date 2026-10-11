"""Exercise health-bar names, preserve shared HUD graphics, and export proof ROMs locally."""
import argparse,json,threading,hashlib
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from decode_graphics import decode_block
parser=argparse.ArgumentParser();parser.add_argument('rom',type=Path);parser.add_argument('--edited-rom',type=Path);parser.add_argument('--output',type=Path,default=Path('outputs/match-name-proof'));args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
repo=Path(__file__).resolve().parents[1];server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)));threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=browser.new_page(viewport={'width':1200,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html');page.locator('#rom').set_input_files(str(args.rom));page.wait_for_function('rom!==null');page.locator('#tab-profile').click()
 stock=page.evaluate('Object.fromEntries(C.characters.map(c=>[c.id,originalHUD(c.id)]))');font=page.evaluate('Object.keys(matchFont())');assert all(c in font for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
 # Stock names, including the longer retained Bam Bam name, reproduce original graphics.
 for character in page.evaluate('C.characters'):
  page.locator('#wrestler').select_option(character['id']);page.locator('#bio-apply').click();assert page.evaluate('matchState(M.id)')==stock[character['id']]
 page.locator('#reset').click();names={id:'TEST '+word for id,word in zip(map(str,range(12)),['ALPHA','BRAVO','CHARLIE','DELTA','ECHO','FOXTROT','GOLF','HOTEL','INDIA','JULIET','KILO','LIMA'])}
 for id,name in names.items():
  page.locator('#wrestler').select_option(id);page.locator('#match-name').fill(name);page.locator('#match-name-apply').click();assert page.evaluate('selectionEdits[M.id].hudName')==name
 expected=page.evaluate('Object.fromEntries(C.characters.map(c=>[c.id,matchState(c.id)]))');saved=page.evaluate('selectionEdits');page.locator('#match-name').fill('WWWWWWWWWWWWWW');page.locator('#match-name-apply').click();assert page.evaluate('selectionEdits')==saved;assert 'too wide' in page.locator('#status').text_content()
 page.locator('#match-name-restore').click();assert page.evaluate('matchState(M.id)')==stock['11'];page.locator('#undo').click();assert page.evaluate('selectionEdits')==saved
 page.locator('#tab-export').click()
 with page.expect_download() as d:page.locator('#save').click()
 project=Path(d.value.path()).read_bytes();page.locator('#reset').click();page.locator('#project').set_input_files({'name':'names.json','mimeType':'application/json','buffer':project});page.wait_for_function('Object.keys(selectionEdits).length===12');assert page.evaluate('selectionEdits')==saved
 with page.expect_download() as d:page.locator('#rom-export').click()
 result=Path(d.value.path()).read_bytes();(args.output/'all-12-names.sfc').write_bytes(result)
 graphics,_=decode_block(result,0x3a0000);original,_=decode_block(args.rom.read_bytes(),0x2ace03)
 assert graphics[:64*32]==original[:64*32];assert graphics[135*32:237*32]==original[135*32:237*32],'Other HUD assets and fallback label must survive'
 page.locator('#rom').set_input_files({'name':'names.sfc','mimeType':'application/octet-stream','buffer':result});page.wait_for_function('rom!==null&&hudSource(rom)===H.destination');assert page.evaluate('Object.fromEntries(C.characters.map(c=>[c.id,originalHUD(c.id)]))')==expected
 with page.expect_download() as d:page.locator('#rom-export').click()
 assert Path(d.value.path()).read_bytes()==result
 (args.output/'expected.json').write_text(json.dumps({'names':names,'pixels':expected},indent=2))
 if args.edited_rom:
  page.locator('#rom').set_input_files(str(args.edited_rom));page.wait_for_function("rom!==null&&selectionState('5').bio.name==='SCOTT HALL'");page.locator('#wrestler').select_option('5');page.locator('#tab-profile').click();before=page.evaluate('originalHUD(M.id)');page.locator('#bio-apply').click();assert page.evaluate('selectionEdits[M.id].hudName')=='SCOTT HALL';assert page.evaluate('matchState(M.id)')!=before
  page.screenshot(path=str(args.output/'workshop.png'),full_page=True);page.locator('#tab-export').click()
  with page.expect_download() as d:page.locator('#rom-export').click()
  (args.output/'Scott-Hall-name-fixed.sfc').write_bytes(Path(d.value.path()).read_bytes())
 assert not errors,errors
 browser.close()
server.shutdown();print('PASS: all 12 match names; native lettering; shared graphics preserved; width refusal; undo; projects; edited-ROM reopen; Scott Hall bio synchronizes health-bar name')
