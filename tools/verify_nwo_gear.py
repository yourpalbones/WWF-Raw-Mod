"""Verify native nWo gear, legacy upgrade, previews, isolation and editor exports."""
import argparse,hashlib,json,threading
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
from PIL import Image
from extract_oam import objects
p=argparse.ArgumentParser(description=__doc__);p.add_argument('base',type=Path);p.add_argument('patched',type=Path);p.add_argument('--capture-root',type=Path,required=True);p.add_argument('--legacy',type=Path);p.add_argument('--previous',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();repo=Path(__file__).resolve().parents[1];a.output.mkdir(parents=True,exist_ok=True);base=a.base.read_bytes();patched=a.patched.read_bytes();allowed=set()
for address,length in[(0xffd5,1),(0xffd7,1),(0xffdc,4),(0x2cf6e4,4),(0xecc1,4),(0xed19,4),*[(0x2cc4da+s*32,32)for s in[5,9,10]]]:allowed.update(range(address,address+length))
assert all(x==patched[i]or i in allowed for i,x in enumerate(base));assert len(patched)==0x600000;assert patched[0x400000:0x410000]==patched[:65536];expected=hashlib.sha256(patched).hexdigest();private_calls=0
for log in a.capture_root.glob('captures-*/**/tile_calls.jsonl'):
 for line in log.read_text().splitlines():
  e=json.loads(line)
  if e['source']<0x800000:assert e['descriptor']>>16 in[0x42,0x43,0x4c,0x4d,0x55,0x56,0x57];assert not e['compressed'];private_calls+=1
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)));threading.Thread(target=server.serve_forever,daemon=True).start();errors=[];counts={}
with sync_playwright()as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html')
 def load(path):page.locator('#rom').set_input_files(str(path));page.wait_for_function('rom!==null',timeout=90000)
 def digest():return page.evaluate('async()=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",playableROM())),v=>v.toString(16).padStart(2,"0")).join("")')
 def apply(id):page.locator('#wrestler').select_option(id);page.locator('#scott-reference-apply').click();page.wait_for_function('id=>hasNativeGear(rom,id)',arg=id,timeout=90000)
 load(a.base)
 for id in['5','10','9']:apply(id)
 if digest()!=expected:
  page.locator('#tab-export').click()
  with page.expect_download()as download:page.locator('#rom-export').click()
  (a.output/'browser.sfc').write_bytes(Path(download.value.path()).read_bytes())
 assert digest()==expected,('Browser/native mismatch',digest(),expected);print('All three browser recipes match native build',flush=True)
 for id,name,window in[('5','scott','RAW_SCOTT_MANIFEST'),('10','nash','RAW_NASH_MANIFEST'),('9','syxx','RAW_SYXX_MANIFEST')]:
  page.locator('#wrestler').select_option(id);poses=page.evaluate(f'window.{window}.poses');folders={f.name:f for root in[a.capture_root/f'captures-{name}/actions/{name}',a.capture_root/f'captures-{name}/specials/{name}',a.capture_root/'grapples'/name]for f in root.iterdir()if f.is_dir()};count=0
  for index,pose in enumerate(poses):
   if pose['category']!='captured':continue
   folder,stem=pose['capture'].split('/');prefix=folders[folder]/stem;read=lambda kind:Path(str(prefix)+'-'+kind+'.bin').read_bytes();parts=[(r,im)for r,im in objects(read('vram'),read('oam'),read('cgram'),read('registers')[0x2101])if r['palette']==0 and 0<=r['y']<190 and -20<=r['x']<256 and im.getbbox()];left=min(r['x']for r,im in parts);top=min(r['y']for r,im in parts);im=Image.new('RGBA',(pose['width'],pose['height']))
   for record,pic in reversed(parts):im.alpha_composite(pic,(record['x']-left,record['y']-top))
   actual=bytes(page.evaluate('i=>{$("pose").value=i;render();return Array.from(ctx.getImageData(0,0,canvas.width,canvas.height).data)}',index));assert actual==im.tobytes(),(name,pose['capture']);count+=1
  counts[name]=count;print(name,count,'native previews pixel-exact',flush=True)
 # Legacy Scott codec remains playable and can be upgraded without losing profiles.
 if a.legacy:
  load(a.legacy);assert digest()==hashlib.sha256(a.legacy.read_bytes()).hexdigest();assert page.evaluate('hasScottGear(rom)&&!hasNativeGear(rom,"5")')
  for id in['10','9','5']:apply(id)
  assert digest()==expected,('Legacy upgrade mismatch',digest(),expected);print('Legacy Scott upgrade byte-exact',flush=True)
 if a.previous:
  load(a.previous);assert digest()==hashlib.sha256(a.previous.read_bytes()).hexdigest()
  for id in['5','10','9']:
   page.locator('#wrestler').select_option(id);assert page.evaluate('M.poses.some(p=>p.category==="captured")');assert page.evaluate('nativeGearRevision(rom,M.id)>0&&!hasNativeGear(rom,M.id)');apply(id)
  assert digest()==expected,('v0.9 upgrade mismatch',digest(),expected);print('v0.9 previews and upgrade byte-exact',flush=True)
 # Expanded private sources support PNG import, project save/undo, and reopen.
 page.locator('#wrestler').select_option('9');page.evaluate('''()=>{const key=Object.keys(M.sources).find(k=>C.sources[k].offset>=0x570000&&C.sources[k].offset<0x5f0000);remember();edits[key]=originals[key].map(v=>v?6:0);render();importPosePixels(ctx.getImageData(0,0,canvas.width,canvas.height).data,canvas.width,canvas.height);}''');page.evaluate('validateLoadedMod(playableROM())');project=page.evaluate('JSON.stringify({version:9,original_sha256:C.original_sha256,base_sha256:baseDigest,edits,palettes,selection_edits:selectionEdits})');changed=digest();assert changed!=expected
 page.locator('#rom').set_input_files(str(a.patched));page.wait_for_function('rom!==null');page.locator('#project').set_input_files({'name':'gear.json','mimeType':'application/json','buffer':project.encode()});page.wait_for_function('Object.keys(edits).length>0');assert digest()==changed
 page.locator('#tab-profile').click();page.locator('#bio-apply').click();page.evaluate('validateLoadedMod(playableROM())');assert page.evaluate('playableROM().length')==0x600000;assert not errors,errors;b.close()
server.shutdown();report=dict(base_sha256=hashlib.sha256(base).hexdigest(),patched_sha256=expected,all_three_recipes_byte_exact=True,legacy_scott_upgrade_byte_exact=bool(a.legacy),previous_v09_upgrade_byte_exact=bool(a.previous),native_preview_counts=counts,private_raw_tile_calls=private_calls,original_opaque_masks_preserved=True,other_input_bytes_preserved=True,project_and_png_roundtrip=True,bio_export_6mib=True,complete_gameplay_coverage=False);(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
