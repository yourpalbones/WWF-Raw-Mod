"""Compare all editor-visible workers and constrain actual ROM writes."""
import argparse,json,threading,hashlib
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
from present_hollywood_hogan import bios
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
p=argparse.ArgumentParser(description=__doc__);p.add_argument('before',type=Path);p.add_argument('after',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();before=a.before.read_bytes();after=a.after.read_bytes();root=Path(__file__).resolve().parents[1]
# Explicit permissible allocations from the inspected roster-16 implementation.
allowed=[(0xffdc,0xffe0),(0x40ffdc,0x40ffe0),(0x2efaf5,0x2efd11),(0x2eff49,0x2f0000),(0x34d100,0x34ef00),(0x3b8000,0x3bb000),(0x4a0000,0x4a5000),(0x4a6a00,0x4a6a20),(0x540000,0x548000),(0x548000,0x54a000),(0x54a000,0x550000),(0x550000,0x558000),(0x55b000,0x560000),(0x349000,0x349080),(0x708000,0x708000+16*45)]
changes=[i for i,(x,y)in enumerate(zip(before,after))if x!=y];unexpected=[i for i in changes if not any(l<=i<r for l,r in allowed)];assert not unexpected,[hex(i)for i in unexpected[:20]]
# Ensure all constructor/AI/collision/action/dispatch code stays byte-identical.
assert before[0x70f000:]==after[0x70f000:]
for start,end in [(0x4a7000,0x4b0000),(0x34ef00,0x350000),(0x5d5000,0x5e0000),(0x708600,0x7086c0)]:assert before[start:end]==after[start:end]
for i in range(16):
 record=0x708000+i*45
 assert before[record+32:record+36]==after[record+32:record+36]
 assert before[record+40:record+45]==after[record+40:record+45]
expected=bios(before);expected[13]['name']='HOLLYWOOD HOGAN';assert bios(after)==expected
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root)));threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/editor-v01/gear-workshop.html')
 def signature(path):
  page.locator('#rom').set_input_files(str(path.resolve()));page.wait_for_function('rom!==null')
  return page.evaluate('''async()=>{const signatures={};const hash=async data=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)),v=>v.toString(16).padStart(2,'0')).join('');for(const c of C.characters){const keys=Object.keys(c.sources).sort(),data=new Uint8Array(keys.length*64+32);for(let i=0;i<keys.length;i++)data.set(pixels(keys[i]),i*64);data.set(rom.slice(c.palette_offset,c.palette_offset+32),keys.length*64);const profile=selectionState(c.id),assets=originalProfileAssets(c.id);signatures[c.id]={name:profile.bio.name,sprite:await hash(data),presentation:await hash(new TextEncoder().encode(JSON.stringify({profile,assets,hud:originalHUD(c.id)}))),poses:c.poses.length};}return signatures;}''')
 old=signature(a.before);new=signature(a.after);other=[i for i in old if i!='13'];assert all(old[i]==new[i]for i in other),[i for i in other if old[i]!=new[i]];assert old['13']['sprite']!=new['13']['sprite'];assert not errors;result={'all_other_wrestlers_unchanged':len(other),'all_other_editor_sprite_palette_and_presentation_hashes_equal':True,'gameplay_code_and_move_tables_unchanged':True,'bio_values_unchanged_except_hogan_name':True,'writes_within_inspected_allocations':True,'changed_bytes':len(changes),'page_errors':errors,'before':old,'after':new};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('before','after')},indent=2));b.close()
server.shutdown()
