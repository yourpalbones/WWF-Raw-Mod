"""Verify all selection portraits/bios and exported patches in Chromium."""
import argparse
import io
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from decode_graphics import decode_block

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('rom',type=Path)
parser.add_argument('--chromium',default='/usr/bin/chromium')
parser.add_argument('--output',type=Path,default=Path('outputs/selection-editor'))
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
repo=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)))
threading.Thread(target=server.serve_forever,daemon=True).start()
original=args.rom.read_bytes();cases=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=args.chromium,headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1200,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html')
 page.locator('#rom').set_input_files(str(args.rom));page.wait_for_function('rom!==null');page.locator('#tab-profile').click()
 characters=page.evaluate('C.characters')
 for character in characters:
  id=character['id'];page.locator('#wrestler').select_option(id)
  meta=page.evaluate('S.characters[M.id]');decoded,_=decode_block(original,meta['portrait_offset'])
  assert page.evaluate('Array.from(decodePortrait(rom,S.characters[M.id].portrait_offset))')==list(decoded)
  original_bio=page.evaluate('originalSelection(M.id).bio')
  assert all(original_bio.values())
  pixels=page.evaluate('Array.from(document.getElementById("portrait").getContext("2d").getImageData(0,0,128,120).data)')
  image=Image.frombytes('RGBA',(128,120),bytes(pixels));ImageDraw.Draw(image).rectangle((0,0,7,7),fill=(255,0,255,255))
  buffer=io.BytesIO();image.save(buffer,format='PNG')
  page.locator('#portrait-import').set_input_files({'name':'test.png','mimeType':'image/png','buffer':buffer.getvalue()})
  page.wait_for_function('(id)=>Boolean(selectionEdits[id]?.portrait)',arg=id)
  assert page.evaluate('Boolean(selectionEdits[M.id].monitor)') # default portrait/monitor link
  name='TEST '+['ALPHA','BRAVO','CHARLIE','DELTA','ECHO','FOXTROT','GOLF','HOTEL','INDIA','JULIET','KILO','LIMA'][int(id)]
  for field,value in {'name':name,'from':'TEST CITY','weight':'999','height':'6\'0"','special':'TEST KICK'}.items():page.locator('#bio-'+field).fill(value)
  page.locator('#bio-apply').click();assert page.evaluate('selectionEdits[M.id].bio.name')==name
  cases.append({'character':character['character'],'id':id,'meta':meta,'expected':page.evaluate('selectionEdits[M.id]')})
 # Undo restores selection edits too, then redo the bio through the form.
 page.locator('#undo').click();assert page.evaluate('selectionEdits[M.id].bio') is None
 for field,value in cases[-1]['expected']['bio'].items():page.locator('#bio-'+field).fill(value)
 page.locator('#bio-apply').click()
 with page.expect_download() as d:page.locator('#save').click()
 project=Path(d.value.path()).read_bytes();page.locator('#reset').click()
 page.locator('#project').set_input_files({'name':'selection.json','mimeType':'application/json','buffer':project})
 page.wait_for_function('Object.keys(selectionEdits).length===12')
 assert page.evaluate('selectionEdits')==json.loads(project)['selection_edits']
 # Invalid portrait imports in projects must be rejected without losing edits.
 invalid=json.loads(project);invalid['selection_edits']['1']['portrait']['pixels'][0]=64
 page.locator('#project').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':json.dumps(invalid).encode()})
 page.wait_for_function("document.getElementById('status').textContent.includes('Invalid portrait')")
 assert page.evaluate('selectionEdits')==json.loads(project)['selection_edits']
 # Overlong text must be rejected before replacing saved bio.
 page.locator('#bio-from').fill('X'*13);page.locator('#bio-apply').click()
 assert 'Check from' in page.locator('#status').inner_text()
 assert page.evaluate('selectionEdits[M.id].bio.from')=='TEST CITY'
 with page.expect_download() as d:
  page.locator('#tab-export').click();page.locator('#patch').click();page.locator('#tab-profile').click()
 patch=Path(d.value.path()).read_bytes();(args.output/'selection-test.ips').write_bytes(patch)
 result=bytearray(original);cursor=5
 while patch[cursor:cursor+3]!=b'EOF':
  address=int.from_bytes(patch[cursor:cursor+3],'big');length=int.from_bytes(patch[cursor+3:cursor+5],'big');cursor+=5
  if length:packet=patch[cursor:cursor+length];cursor+=length
  else:
   length=int.from_bytes(patch[cursor:cursor+2],'big');packet=bytes([patch[cursor+2]])*length;cursor+=3
  if address+length>len(result):result.extend(b'\xff'*(address+length-len(result)))
  result[address:address+length]=packet
 page.locator('#tab-export').click()
 with page.expect_download() as d:page.locator('#rom-export').click()
 assert Path(d.value.path()).read_bytes()==bytes(result)
 page.locator('#tab-profile').click()
 assert len(result)==0x400000
 assert sum(result)&65535==int.from_bytes(result[0xffde:0xffe0],'little')
 for case in cases:
  meta=case['meta'];pointer=int.from_bytes(result[meta['record']:meta['record']+3],'little')&0x3fffff
  expected=page.evaluate('(id)=>Array.from(portraitPacket(selectionEdits[id].portrait.pixels))',case['id'])
  decoded,_=decode_block(result,pointer);wanted,_=decode_block(bytes(expected),0);assert decoded==wanted
  colors=case['expected']['portrait']['colors'];assert result[meta['palette_offset']:meta['palette_offset']+128]==b''.join(c.to_bytes(2,'little')for c in colors)
  for field,text in case['expected']['bio'].items():
   address=meta['fields'][field]
   if field!='weight':address=0x2e0000+int.from_bytes(result[address:address+2],'little')
   end=result.index(0,address);assert bytes(result[address:end]).decode('ascii').replace('\r','\n')==text
 # Excess combined text must fail instead of corrupting another bank.
 saved=page.evaluate('selectionEdits')
 page.evaluate("for(const c of C.characters){selectionEdits[c.id].bio.from='CITY '+c.id+' ABCDE'+'\\n'+'SECOND LINE'+'\\n'+'THIRD LINE';}")
 assert page.evaluate("(()=>{try{selectionRecords();return false;}catch(e){return e.message.includes('text space');}})()")
 page.evaluate('(state)=>{selectionEdits=state;render();}',saved)
 # Original shared string pool and original portrait allocations must remain intact.
 assert result[0x2ef8dc:0x2efaf5]==original[0x2ef8dc:0x2efaf5]
 for case in cases:
  meta=case['meta'];a=meta['portrait_offset'];assert result[a:a+meta['portrait_length']]==original[a:a+meta['portrait_length']]
 (args.output/'selection-test.sfc').write_bytes(result)
 (args.output/'verification.json').write_text(json.dumps({'characters':12,'portrait_decodes_matched':12,'portrait_patch_roundtrips':12,'bios_patch_roundtrips':12,'expanded_rom_bytes':len(result),'checksum_verified':True,'shared_original_strings_preserved':True,'project_undo_and_validation_passed':True},indent=2)+'\n')
 page.locator('#wrestler').select_option('1');page.locator('#portrait').scroll_into_view_if_needed();page.screenshot(path=str(args.output/'workshop.png'),full_page=True)
 assert not errors,errors;browser.close()
server.shutdown()
print('All 12 portrait decodes, imports, bios, expanded patches/checksum, project reload/undo and invalid input checks passed')
