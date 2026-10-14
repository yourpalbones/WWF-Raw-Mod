"""Native/editor pixel comparison using private ROM and emulator fixtures."""
import sys,json,threading,hashlib,struct,argparse
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
ap=argparse.ArgumentParser(description='Compare native body OBJ pixels against the actual roster-16 editor canvas.')
ap.add_argument('rom',type=Path);ap.add_argument('captures',type=Path);ap.add_argument('--slot',default='15',choices=('13','14','15'));ap.add_argument('--actor',type=int,choices=(0,1),default=0);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
from extract_oam import objects
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);p=b.new_page();p.goto(f'http://127.0.0.1:{server.server_port}/editor-v01/gear-workshop.html');p.locator('#rom').set_input_files(str(args.rom.resolve()));p.wait_for_function('rom!==null');p.locator('#wrestler').select_option(args.slot)
 expected=p.evaluate('''()=>M.poses.map((pose,i)=>{$('pose').value=i;render();return {pose:i,root:pose.v01Root,width:canvas.width,height:canvas.height,rgba:Array.from(ctx.getImageData(0,0,canvas.width,canvas.height).data)};})''');b.close()
server.shutdown()
def digest(points,flip=False):
 if not points:return None
 if flip:points={(-x,y):v for (x,y),v in points.items()}
 l=min(x for x,y in points);t=min(y for x,y in points);r=max(x for x,y in points)+1;b=max(y for x,y in points)+1;data=bytearray((r-l)*(b-t)*4)
 for (x,y),rgb in points.items():a=((y-t)*(r-l)+x-l)*4;data[a:a+4]=bytes((*rgb,255))
 return hashlib.sha256(struct.pack('<HH',r-l,b-t)+data).hexdigest()
lookup={}
for e in expected:
 points={(i%e['width'],i//e['width']):tuple(e['rgba'][i*4:i*4+3])for i in range(e['width']*e['height'])if e['rgba'][i*4+3]}
 for flip in [False,True]:lookup.setdefault(digest(points,flip),[]).append(e['root'])
rows=[]
for path in sorted(args.captures.glob('*-oam.bin')):
 prefix=str(path)[:-8];read=lambda x:Path(prefix+'-'+x+'.bin').read_bytes();cg=read('cgram');points={}
 for o,im in reversed(objects(read('vram'),read('oam'),cg,read('registers')[0x2101])):
  if o['palette']!=args.actor or not args.actor*64<=o['tile']<(args.actor+1)*64 or o['y']>=224:continue
  for y in range(im.height):
   for x in range(im.width):
    q=im.getpixel((x,y))
    if q[3]:points[(o['x']+x,o['y']+y)]=q[:3]
 rows.append({'frame':Path(prefix).name,'matched_editor_roots':lookup.get(digest(points),[])})
r={'frames':len(rows),'exact_editor_pixel_matches':sum(bool(x['matched_editor_roots'])for x in rows),'roots_observed':sorted({i for x in rows for i in x['matched_editor_roots']}),'scope':'Active selected-player body OBJ pixels; includes sprite/palette edits; excludes native standard shadow and background; checks shapes and colors rather than timing','rows':rows};args.output.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items()if k!='rows'}));assert r['frames']==r['exact_editor_pixel_matches']
