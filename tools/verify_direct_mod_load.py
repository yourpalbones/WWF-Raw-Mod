"""Check loading, retaining, editing and reopening an exported ROM directly."""
import argparse,threading
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser();parser.add_argument('rom',type=Path);args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)));threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html');page.locator('#rom').set_input_files(str(args.rom));page.wait_for_function("document.getElementById('status').textContent.startsWith('Edited ROM loaded')")
 states=page.evaluate('Object.fromEntries(C.characters.map(c=>[c.id,{selection:selectionState(c.id),assets:profileState(c.id)}]))')
 page.locator('#tab-export').click()
 with page.expect_download() as download:page.locator('#rom-export').click()
 assert Path(download.value.path()).read_bytes()==args.rom.read_bytes(),'No-edit export must preserve the whole mod'
 page.locator('#wrestler').select_option('5');page.locator('#tab-profile').click();assert page.locator('#bio-name').input_value()=='SCOTT HALL'
 page.locator('#bio-name').fill('TEST HALL');page.locator('#bio-apply').click()
 page.locator('#tab-export').click()
 with page.expect_download() as download:page.locator('#rom-export').click()
 edited=Path(download.value.path()).read_bytes();
 with page.expect_download() as saved:page.locator('#save').click()
 project=Path(saved.value.path()).read_bytes();page.locator('#reset').click();page.locator('#project').set_input_files({'name':'project.json','mimeType':'application/json','buffer':project});page.wait_for_function("selectionState('5').bio.name==='TEST HALL'");page.locator('#rom').set_input_files({'name':'reopened.sfc','mimeType':'application/octet-stream','buffer':edited});page.wait_for_function("rom!==null&&selectionState('5').bio.name==='TEST HALL'")
 for id,before in states.items():
  after=page.evaluate('(id)=>({selection:selectionState(id),assets:profileState(id)})',id)
  if id=='5':assert all(after['selection']['portrait'][key]==before['selection']['portrait'][key] for key in ['pixels','colors']);assert after['assets']['monitor']==before['assets']['monitor']
  else:assert after==before,f'Existing profile {id} lost'
 assert not errors,errors
 print('PASS: direct edited ROM load; byte-identical unchanged export; rename/export/reopen; other 11 profiles and all portraits preserved')
 browser.close()
server.shutdown()
