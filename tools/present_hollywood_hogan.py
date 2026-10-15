"""Apply Hollywood presentation through the existing protected roster-16 editor.

Private ROM/image inputs only. Quantizes the portrait to native 64 colors and
creates monitor/name art in the supported existing systems; no engine patches.
"""
import argparse,json,threading,hashlib
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
from build_nwo_gear import checksum

FONT={'H':['101','101','111','101','101'],'O':['111','101','101','101','111'],'L':['100','100','100','100','111'],'Y':['101','101','010','010','010'],'W':['101','101','101','111','101'],'D':['110','101','101','101','110'],'G':['111','100','101','101','111'],'A':['010','101','111','101','101'],'N':['101','111','111','111','101']}

def bios(r):
 out=[]
 for i in range(16):
  rec=0x708000+i*45;fields={}
  for name,delta in [('name',28),('from',30),('height',36),('special',38)]:
   at=0x2e0000+int.from_bytes(r[rec+delta:rec+delta+2],'little');end=r.index(0,at);fields[name]=r[at:end].decode('ascii')
  out.append(fields)
 return out

def rename(r):
 original=bios(r);values=[dict(v)for v in original];values[13]['name']='HOLLYWOOD HOGAN';out=bytearray(r);regions=[[0x2efaf5,0x2efd11],[0x2eff49,0x2f0000]];strings={}
 for i,fields in enumerate(values):
  for name,delta in [('name',28),('from',30),('height',36),('special',38)]:
   value=fields[name]
   if value not in strings:
    data=value.encode('ascii')+b'\0';region=next(q for q in regions if q[1]-q[0]>=len(data));at=region[0];region[0]+=len(data);out[at:at+len(data)]=data;strings[value]=at
   out[0x708000+i*45+delta:0x708002+i*45+delta]=(strings[value]&65535).to_bytes(2,'little')
 checksum(out);out[0x400000:0x410000]=out[:65536];assert bios(out)==values;return out

class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('portrait',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);named=a.output/'Hollywood-Hogan-named.sfc';named.write_bytes(rename(a.rom.read_bytes()));root=Path(__file__).resolve().parents[1]
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root)));threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/editor-v01/gear-workshop.html');page.locator('#rom').set_input_files(str(named.resolve()));page.wait_for_function('rom!==null');page.locator('#wrestler').select_option('13');page.locator('#tab-profile').click();page.locator('#portrait-import').set_input_files(str(a.portrait.resolve()));page.wait_for_function("Boolean(selectionEdits['13']?.portrait)");page.locator('#monitor-copy').click()
  # The stock HUD is only 64x8. Authored 3x5 letters fit the supported short
  # alias exactly, keeping all words readable without a runtime font change.
  text='HOLLYWOOD HOGAN';pixels=[0]*512;left=(64-(len(text)*4-1))//2
  for n,c in enumerate(text):
   if c==' ':continue
   for y,row in enumerate(FONT[c]):
    for x,v in enumerate(row):
     if v=='1':pixels[(y+2)*64+left+n*4+x]=9
  page.evaluate('''pixels=>{const edit=selectionEdits['13'];edit.hud={pixels};delete edit.hudName;
   // Fifteen native 16px letters/spaces fit 240px. Compose two existing
   // font renders instead of truncating the 14-character UI generator.
   const upper=generateNameLogo('HOLLYWOOD','13'),lower=generateNameLogo('HOGAN AAA','13');
   const image=Array(256*224).fill(0);for(let y=0;y<16;y++){
    for(let x=0;x<144;x++)image[(24+y)*256+8+x]=upper.pixels[(24+y)*256+56+x];
    for(let x=0;x<80;x++)image[(24+y)*256+168+x]=lower.pixels[(24+y)*256+56+x];}
   edit.logo={pixels:image,colors:upper.colors};delete edit.logoName;validateSelection(selectionEdits);render();}''',pixels)
  page.locator('#tab-export').click()
  with page.expect_download() as d:page.locator('#rom-export').click()
  target=a.output/'WWF-Raw-Hollywood-Hogan.sfc';d.value.save_as(target)
  page.locator('#rom').set_input_files(str(target.resolve()));page.wait_for_function('rom!==null');page.locator('#wrestler').select_option('13');assert page.evaluate("selectionState('13').bio.name")=='HOLLYWOOD HOGAN';assert page.evaluate("matchState('13')")==pixels
  result=page.evaluate("({characters:C.characters.length,poses:M.poses.length,bio:selectionState('13').bio,portrait:selectionState('13').portrait,monitor:originalProfileAssets('13').monitor})")
  # Save only native, quantized presentation previews, no raw decoded art in Git.
  from PIL import Image
  for key,size in [('portrait',(128,120)),('monitor',(48,48))]:
   asset=result.pop(key);colors=[tuple((c>>s&31)*255//31 for s in(0,5,10))for c in asset['colors']];im=Image.new('RGB',size);im.putdata([colors[v]for v in asset['pixels']]);im.save(a.output/f'final-{key}.png')
  page.locator('#tab-sprite').click();page.screenshot(path=str(a.output/'editor-hollywood.png'));assert not errors,errors;result.update(page_errors=errors,portrait_export_reopened=True,monitor_export_reopened=True,name_export_reopened=True,hud_export_reopened=True,output_sha256=hashlib.sha256(target.read_bytes()).hexdigest());(a.output/'presentation-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));b.close()
 server.shutdown()
if __name__=='__main__':main()
