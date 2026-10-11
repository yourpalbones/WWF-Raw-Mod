from pathlib import Path
import sys
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from PIL import Image
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract_oam import objects,assemble
import argparse
parser=argparse.ArgumentParser(description='Verify assembled editor poses and patch/project behavior in Chromium.')
parser.add_argument('rom',type=Path)
parser.add_argument('--capture-root',type=Path,required=True)
parser.add_argument('--movement-root',type=Path,default=Path('outputs/editor-roster-live'))
parser.add_argument('--page',default='index.html',choices=['index.html','gear-workshop.html'])
parser.add_argument('--chromium',default='/usr/bin/chromium')
parser.add_argument('--output',type=Path,default=Path('outputs/editor-preview.png'))
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]
rom=args.rom
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=args.chromium,headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1100,'height':1000})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/editor/{args.page}')
 page.locator('#rom').set_input_files(str(rom))
 page.wait_for_function('rom !== null')
 assert page.evaluate('Object.entries(C.sources).every(([key,source])=>{const packet=encode(originals[key],source.compressed);return packet.length===source.length && packet.every((v,i)=>v===rom[source.offset+i]);})')
 # Every published layout must match the native captured OAM composition.
 characters=page.evaluate('C.characters')
 count=0
 for character in characters:
  page.locator('#wrestler').select_option(character['id'])
  for i,pose in enumerate(character['poses']):
   page.locator('#pose').select_option(str(i))
   capture=pose['capture']
   prefix=(args.capture_root/capture) if character['id']=='1' else (args.movement_root/capture)
   def read(name):return Path(str(prefix)+'-'+name+'.bin').read_bytes()
   records=objects(read('vram'),read('oam'),read('cgram'),read('registers')[0x2101])
   indices=[j for j,(r,im) in enumerate(records) if r['palette']==0 and 0<=r['y']<190 and -20<=r['x']<256 and im.getbbox()]
   native,_=assemble(records,indices)
   data=page.evaluate('Array.from(ctx.getImageData(0,0,canvas.width,canvas.height).data)')
   size=page.evaluate('[canvas.width,canvas.height]')
   actual=Image.frombytes('RGBA',tuple(size),bytes(data))
   assert actual.crop(actual.getbbox()).tobytes()==native.tobytes(), (character['character'],pose['label'])
   count+=1
 print(f'{len(characters)} characters, {count} poses match native captures; all sources re-encode byte for byte')
 page.locator('#wrestler').select_option('1')
 page.locator('#pose').select_option('0')
 # Palette changes must recolor precisely the selected slot, without changing tiles.
 page.get_by_role('button',name='Native color 4',exact=True).click()
 before=page.evaluate('Array.from(ctx.getImageData(0,0,canvas.width,canvas.height).data)')
 matches=page.evaluate('cells.map(c=>Boolean(c && pixels(c.key)[c.index]===4))')
 page.locator('#palette-color').fill('#00ff00')
 page.locator('#palette-apply').click()
 assert page.evaluate('paletteEdits')=={'4': 992}
 after=page.evaluate('Array.from(ctx.getImageData(0,0,canvas.width,canvas.height).data)')
 assert any(matches)
 for index,match in enumerate(matches):
  assert after[index*4:index*4+4]==([0,255,0,255] if match else before[index*4:index*4+4])
 assert page.evaluate('Object.keys(edits).length')==0
 page.locator('#palette-restore').click()
 assert page.evaluate('paletteEdits')=={}
 page.locator('#undo').click()
 assert page.evaluate('paletteEdits')=={'4':992}
 page.get_by_role('button',name='Native color 1',exact=True).click()
 # Paint a visible, nonblack source pixel, export and verify actual tile changes.
 target=page.evaluate('cells.findIndex(c=>c && [4,5].includes(pixels(c.key)[c.index]))')
 width=page.evaluate('canvas.width');rect=page.locator('#sprite').bounding_box()
 page.mouse.click(rect['x']+(target%width+.5)*rect['width']/width,rect['y']+(target//width+.5)*rect['height']/page.evaluate('canvas.height'))
 assert page.evaluate('Object.keys(edits).length')==1
 with page.expect_download() as d:
  page.locator('#tab-export').click();page.locator('#patch').click();page.locator('#tab-sprite').click()
 patch=Path(d.value.path()).read_bytes();data=bytearray(rom.read_bytes());cursor=5
 while patch[cursor:cursor+3]!=b'EOF':
  offset=int.from_bytes(patch[cursor:cursor+3],'big');length=int.from_bytes(patch[cursor+3:cursor+5],'big');cursor+=5
  assert length>0;data[offset:offset+length]=patch[cursor:cursor+length];cursor+=length
 from decode_sprite_tile import decode_sprite_tile
 from inspect_rom import tile
 edited=page.evaluate('edits');sources=page.evaluate('C.sources')
 for key,pixels_ in edited.items():
  source=sources[key];decoded=decode_sprite_tile(data,source['offset'])[0] if source['compressed'] else data[source['offset']:source['offset']+32]
  assert tile(decoded,0,4)==pixels_
 args.output.parent.mkdir(parents=True,exist_ok=True)
 (args.output.parent/'editor-test.sfc').write_bytes(data)
 palette_offset=page.evaluate('M.palette_offset')
 assert int.from_bytes(data[palette_offset+8:palette_offset+10],'little')==992
 assert (sum(data[:0x200000])+2*sum(data[0x200000:]))&65535==int.from_bytes(data[0xffde:0xffe0],'little')
 with page.expect_download() as d:page.locator('#save').click()
 project=Path(d.value.path()).read_bytes()
 page.locator('#undo').click();assert page.evaluate('Object.keys(edits).length')==0
 page.locator('#project').set_input_files({'name':'project.json','mimeType':'application/json','buffer':project})
 page.wait_for_function("document.getElementById('status').textContent.startsWith('Project loaded')")
 assert page.evaluate('edits')==edited
 assert page.evaluate('paletteEdits')=={'4':992}
 # Character switching must retain edits and use distinct palette addresses.
 page.locator('#wrestler').select_option('2')
 assert page.evaluate('paletteEdits')=={}
 page.get_by_role('button',name='Native color 4',exact=True).click()
 page.locator('#palette-color').fill('#0000ff');page.locator('#palette-apply').click()
 assert page.evaluate('paletteEdits')=={'4':31744}
 page.locator('#wrestler').select_option('1')
 assert page.evaluate('paletteEdits')=={'4':992} and page.evaluate('edits')==edited
 both=page.evaluate('Array.from(patch())')
 merged=bytearray(rom.read_bytes());pos=5
 while bytes(both[pos:pos+3])!=b'EOF':
  offset=int.from_bytes(bytes(both[pos:pos+3]),'big');length=int.from_bytes(bytes(both[pos+3:pos+5]),'big');pos+=5
  merged[offset:offset+length]=bytes(both[pos:pos+length]);pos+=length
 assert int.from_bytes(merged[0x2cc502:0x2cc504],'little')==992
 assert int.from_bytes(merged[0x2cc522:0x2cc524],'little')==31744
 # Restoring a saved project replaces all characters' edit states.
 page.locator('#project').set_input_files({'name':'project.json','mimeType':'application/json','buffer':project})
 page.wait_for_function("Object.keys(palettes['2']||{}).length===0")
 # Old projects load with the original palette; invalid transparency edits fail atomically.
 import json
 legacy=json.loads(project);legacy['version']=2;legacy.pop('palettes');legacy['palette_edits']={'4':992}
 page.locator('#project').set_input_files({'name':'legacy.json','mimeType':'application/json','buffer':json.dumps(legacy).encode()})
 page.wait_for_function("paletteEdits['4']===992 && Object.keys(palettes['2']||{}).length===0")
 old=json.loads(project);old['version']=1;old.pop('palettes')
 page.locator('#project').set_input_files({'name':'old.json','mimeType':'application/json','buffer':json.dumps(old).encode()})
 page.wait_for_function('Object.keys(paletteEdits).length===0')
 invalid=json.loads(project);invalid['palettes']={'1':{'0':992}}
 page.locator('#project').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':json.dumps(invalid).encode()})
 page.wait_for_function("document.getElementById('status').textContent.includes('invalid palette')")
 assert page.evaluate('edits')==edited and page.evaluate('paletteEdits')=={}
 # Failed oversized sparse packets must be blocked rather than corrupt neighbors.
 page.evaluate("const key=Object.keys(M.sources).find(k=>M.sources[k].compressed && M.sources[k].length<36); edits[key]=Array(64).fill(15)")
 assert page.evaluate("(()=>{try{patch();return false}catch(e){return e.message.includes('more space')}})()")
 page.locator('#reset').click()
 args.output.parent.mkdir(parents=True,exist_ok=True)
 page.get_by_role('button',name='Native color 4',exact=True).click()
 page.locator('#palette-color').fill('#00ff00')
 page.locator('#palette-apply').click()
 page.screenshot(path=str(args.output),full_page=True)
 # Exercise painting and palette export for every wrestler, not just Bret.
 page.locator('#reset').click()
 for character in characters:
  page.locator('#wrestler').select_option(character['id'])
  page.locator('#pose').select_option('0')
  page.get_by_role('button',name='Native color 1',exact=True).click()
  target=page.evaluate('cells.findIndex(c=>c && !C.sources[c.key].compressed && pixels(c.key)[c.index]!==1)')
  assert target>=0,character['character']
  page.evaluate('window.scrollTo(0,0)')
  width=page.evaluate('canvas.width');rect=page.locator('#sprite').bounding_box()
  page.mouse.click(rect['x']+(target%width+.5)*rect['width']/width,rect['y']+(target//width+.5)*rect['height']/page.evaluate('canvas.height'))
  assert page.evaluate('(target)=>{const c=cells[target];return pixels(c.key)[c.index]===1;}',target),character['character']
  page.get_by_role('button',name='Native color 4',exact=True).click()
  page.locator('#palette-color').fill('#00ff00');page.locator('#palette-apply').click()
 combined=page.evaluate('Array.from(patch())');multi=bytearray(rom.read_bytes());pos=5
 while bytes(combined[pos:pos+3])!=b'EOF':
  offset=int.from_bytes(bytes(combined[pos:pos+3]),'big');length=int.from_bytes(bytes(combined[pos+3:pos+5]),'big');pos+=5
  multi[offset:offset+length]=bytes(combined[pos:pos+length]);pos+=length
 for character in characters:
  assert int.from_bytes(multi[character['palette_offset']+8:character['palette_offset']+10],'little')==992
 for key,p in page.evaluate('edits').items():
  source=page.evaluate('C.sources')[key]
  actual=decode_sprite_tile(multi,source['offset'])[0] if source['compressed'] else multi[source['offset']:source['offset']+32]
  assert tile(actual,0,4)==p
 assert (sum(multi[:0x200000])+2*sum(multi[0x200000:]))&65535==int.from_bytes(multi[0xffde:0xffe0],'little')
 (args.output.parent/'editor-roster-test.sfc').write_bytes(multi)
 # Verify a saved multi-wrestler project restores edits and all 12 palettes.
 with page.expect_download() as d:page.locator('#save').click()
 roster_project=Path(d.value.path()).read_bytes();expected=page.evaluate('({edits,palettes})')
 page.locator('#reset').click()
 page.locator('#project').set_input_files({'name':'roster.json','mimeType':'application/json','buffer':roster_project})
 page.wait_for_function('Object.keys(edits).length>0')
 assert page.evaluate('({edits,palettes})')==expected
 page.locator('#reset').click()
 # A shared-source edit must identify another loaded wrestler using it.
 shared=page.evaluate('C.characters.flatMap(c=>Object.keys(c.sources).filter(k=>C.characters.some(other=>other.id!==c.id && other.sources[k])).map(k=>({id:c.id,key:k}))).find(s=>originals[s.key].some(v=>v>1))')
 assert shared
 page.locator('#wrestler').select_option(shared['id'])
 page.evaluate('(key)=>{remember();edits[key]=originals[key].map(v=>v>1?1:v);render();}',shared['key'])
 assert 'also used by:' in page.locator('#shared').inner_text()
 page.locator('#reset').click()
 print('All 12 painting, palette export, multi-wrestler project reload and shared-source warning checks passed')
 page.locator('#wrestler').select_option('8')
 page.evaluate('window.scrollTo(0,0)')
 page.screenshot(path=str(args.output.parent/'roster-workshop.png'),full_page=True)
 assert not errors,errors
 browser.close()
 print('Paint, palette recoloring/restore/undo, IPS colors/checksum, current and legacy projects, invalid palette and overflow refusal passed')

server.shutdown()
