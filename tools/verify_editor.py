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
 assert page.evaluate('Object.entries(M.sources).every(([key,source])=>{const packet=encode(originals[key],source.compressed);return packet.length===source.length && packet.every((v,i)=>v===rom[source.offset+i]);})')
 # Native compositor must match capture byte for byte before any editing.
 for i in range(15):
  page.locator('#pose').select_option(str(i))
  label=page.locator('#pose option:checked').inner_text()
  prefix=(args.capture_root/'emulator-coldboot/frame-002940') if i==0 else sorted((args.capture_root/'gear-walk-original').glob('frame-*.png'))[int(label.split()[-1])-1].with_suffix('')
  def read(name):return Path(str(prefix)+'-'+name+'.bin').read_bytes()
  records=objects(read('vram'),read('oam'),read('cgram'),read('registers')[0x2101])
  indices=[j for j,(r,im) in enumerate(records) if r['palette']==0 and 0<=r['y']<190 and -20<=r['x']<256 and im.getbbox()]
  native,_=assemble(records,indices)
  data=page.evaluate('Array.from(ctx.getImageData(0,0,canvas.width,canvas.height).data)')
  size=page.evaluate('[canvas.width,canvas.height]')
  actual=Image.frombytes('RGBA',tuple(size),bytes(data))
  assert actual.crop(actual.getbbox()).tobytes()==native.tobytes(),label
 print('15 assembled poses match native OAM captures exactly; all 215 sources re-encode byte for byte')
 page.locator('#pose').select_option('0')
 # Paint a visible, nonblack source pixel, export and verify actual tile changes.
 target=page.evaluate('cells.findIndex(c=>c && [4,5].includes(pixels(c.key)[c.index]))')
 width=page.evaluate('canvas.width');rect=page.locator('#sprite').bounding_box()
 page.mouse.click(rect['x']+(target%width+.5)*6,rect['y']+(target//width+.5)*6)
 assert page.evaluate('Object.keys(edits).length')==1
 with page.expect_download() as d:page.locator('#patch').click()
 patch=Path(d.value.path()).read_bytes();data=bytearray(rom.read_bytes());cursor=5
 while patch[cursor:cursor+3]!=b'EOF':
  offset=int.from_bytes(patch[cursor:cursor+3],'big');length=int.from_bytes(patch[cursor+3:cursor+5],'big');cursor+=5
  assert length>0;data[offset:offset+length]=patch[cursor:cursor+length];cursor+=length
 from decode_sprite_tile import decode_sprite_tile
 from inspect_rom import tile
 edited=page.evaluate('edits');sources=page.evaluate('M.sources')
 for key,pixels_ in edited.items():
  source=sources[key];decoded=decode_sprite_tile(data,source['offset'])[0] if source['compressed'] else data[source['offset']:source['offset']+32]
  assert tile(decoded,0,4)==pixels_
 args.output.parent.mkdir(parents=True,exist_ok=True)
 (args.output.parent/'editor-test.sfc').write_bytes(data)
 assert (sum(data[:0x200000])+2*sum(data[0x200000:]))&65535==int.from_bytes(data[0xffde:0xffe0],'little')
 with page.expect_download() as d:page.locator('#save').click()
 project=Path(d.value.path()).read_bytes()
 page.locator('#undo').click();assert page.evaluate('Object.keys(edits).length')==0
 page.locator('#project').set_input_files({'name':'project.json','mimeType':'application/json','buffer':project})
 page.wait_for_function("document.getElementById('status').textContent.startsWith('Project loaded')")
 assert page.evaluate('edits')==edited
 # Failed oversized sparse packets must be blocked rather than corrupt neighbors.
 page.evaluate("const key=Object.keys(M.sources).find(k=>M.sources[k].compressed && M.sources[k].length<36); edits[key]=Array(64).fill(15)")
 assert page.evaluate("(()=>{try{patch();return false}catch(e){return e.message.includes('more space')}})()")
 page.locator('#reset').click()
 args.output.parent.mkdir(parents=True,exist_ok=True)
 page.screenshot(path=str(args.output),full_page=True)
 assert not errors,errors
 browser.close()
 print('Paint, IPS tile roundtrip/checksum, undo, project reload and overflow refusal passed')

server.shutdown()
