"""Check Scott's local gear recipe, native previews, source isolation and exports."""
import argparse,hashlib,json,threading
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from PIL import Image
from playwright.sync_api import sync_playwright
from extract_oam import objects
from decode_sprite_tile import decode_sprite_tile
p=argparse.ArgumentParser(description=__doc__);p.add_argument('base',type=Path);p.add_argument('patched',type=Path);p.add_argument('captures',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True);a=p.parse_args();repo=Path(__file__).resolve().parents[1];a.output.mkdir(parents=True,exist_ok=True);base=a.base.read_bytes();patched=a.patched.read_bytes();allowed=set()
for offset,length in[(0xffd5,1),(0xffd7,1),(0xffdc,4),(0x2cf6e4,4),(0xecc1,4),(0xed19,4),(0x2cc57a,32)]:allowed.update(range(offset,offset+length))
assert all(old==patched[i]or i in allowed for i,old in enumerate(base)),'Unrelated input bytes changed'
assert patched[0x400000:0x410000]==patched[:0x10000]
folders={f.name:f for root in a.captures for f in root.iterdir()if f.is_dir()};events=private_events=0
for folder in folders.values():
 if not (folder/'tiles.jsonl').exists():continue
 for line in(folder/'tile_calls.jsonl').read_text().splitlines():
  e=json.loads(line)
  if e['source']<0x800000:assert e['actor_slot']==0,('Private Scott tile used by another actor',e)
 for line in (folder/'tiles.jsonl').read_text().splitlines():
  e=json.loads(line);address=e['source'];offset=address&0x3fffff if address>=0x800000 else address;data,_=decode_sprite_tile(patched,offset);actual=(folder/'assets'/f"tile-{e['event']:06d}-{address:06x}.bin").read_bytes();assert data==actual,(folder.name,e);events+=1;private_events+=address<0x800000
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)));threading.Thread(target=server.serve_forever,daemon=True).start();errors=[]
with sync_playwright()as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html');page.locator('#rom').set_input_files(str(a.base));page.wait_for_function('rom!==null');page.locator('#wrestler').select_option('5');page.locator('#scott-reference-apply').click();page.wait_for_function('rom?.length===0x600000',timeout=90000);assert bytes(page.evaluate('Array.from(playableROM())'))==patched
 poses=page.evaluate('SCOTT.poses');count=0
 for index,pose in enumerate(poses):
  if pose['category']!='captured':continue
  folder,stem=pose['capture'].split('/');prefix=folders[folder]/stem;read=lambda kind:Path(str(prefix)+'-'+kind+'.bin').read_bytes();parts=[(r,im)for r,im in objects(read('vram'),read('oam'),read('cgram'),read('registers')[0x2101])if r['palette']==0 and 0<=r['y']<190 and -20<=r['x']<256 and im.getbbox()];left=min(r['x']for r,im in parts);top=min(r['y']for r,im in parts);expected=Image.new('RGBA',(pose['width'],pose['height']))
  for record,im in reversed(parts):expected.alpha_composite(im,(record['x']-left,record['y']-top))
  actual=bytes(page.evaluate('i=>{$("pose").value=i;render();return Array.from(ctx.getImageData(0,0,canvas.width,canvas.height).data)}',index));assert actual==expected.tobytes(),('Native preview differs',pose['capture']);count+=1
  if count%40==0:print('Native previews compared',count,flush=True)
 assert count>100
 # Edit one private packet, export/reopen/project/undo; full 36-byte allocation
 # must support changed opacity-preserving pixels without compressed growth loss.
 page.evaluate('''()=>{const key=Object.keys(M.sources).find(k=>C.sources[k].offset>=0x440000&&C.sources[k].offset<0x4b0000),next=originals[key].map(v=>v?15:0);remember();edits[key]=next;render();}''');edited=bytes(page.evaluate('Array.from(playableROM())'));assert len(edited)==0x600000;assert edited!=patched;assert edited[0x400000:0x410000]==edited[:0x10000];page.evaluate('validateLoadedMod(playableROM())');project=page.evaluate('JSON.stringify({version:9,original_sha256:C.original_sha256,base_sha256:baseDigest,edits,palettes,selection_edits:selectionEdits})');page.locator('#undo').click();assert bytes(page.evaluate('Array.from(playableROM())'))==patched;page.locator('#project').set_input_files({'name':'Scott.json','mimeType':'application/json','buffer':project.encode()});page.wait_for_function('Object.keys(edits).length===1');assert bytes(page.evaluate('Array.from(playableROM())'))==edited
 page.locator('#rom').set_input_files({'name':'Scott.sfc','mimeType':'application/octet-stream','buffer':edited});page.wait_for_function('rom?.length===0x600000 && Object.keys(edits).length===0');assert bytes(page.evaluate('Array.from(playableROM())'))==edited
 page.locator('#tab-profile').click();page.locator('#bio-name').fill('SCOTT HALL');page.locator('#bio-apply').click();page.evaluate('validateLoadedMod(playableROM())');assert page.evaluate('playableROM().length')==0x600000;assert not errors,errors;b.close()
server.shutdown();report={'base_sha256':hashlib.sha256(base).hexdigest(),'patched_sha256':hashlib.sha256(patched).hexdigest(),'unrelated_input_bytes_preserved':True,'browser_recipe_matches_native_builder':True,'native_tile_decodes_compared':events,'private_tile_decodes_compared':private_events,'native_full_body_previews_pixel_exact':count,'known_frame_pieces':len(poses)-count,'private_packet_edit_undo_project_reopen':True,'bio_export_preserves_6mib_layout':True,'live_coverage_exhaustive':False};(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
