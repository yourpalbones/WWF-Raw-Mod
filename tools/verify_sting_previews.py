"""Compare every published Sting full-body preview to native OAM/VRAM pixels."""
import argparse,json,threading
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
from PIL import Image
from extract_oam import objects
p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('captures',type=Path);p.add_argument('grapples',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();repo=Path(__file__).resolve().parents[1]
folders={f.name:f for root in [a.captures/'actions',a.captures/'specials',a.grapples]for f in root.iterdir()if f.is_dir()}
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)));threading.Thread(target=server.serve_forever,daemon=True).start();count=0
with sync_playwright()as pw:
    b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html');page.context.set_offline(True)
    page.locator('#rom').set_input_files(str(a.rom));page.wait_for_function('rom!==null');page.locator('#wrestler').select_option('7');poses=page.evaluate('RAW_STING_MANIFEST.poses')
    for i,pose in enumerate(poses):
        if pose['category']!='captured':continue
        folder,stem=pose['capture'].split('/');prefix=folders[folder]/stem;read=lambda n:Path(str(prefix)+'-'+n+'.bin').read_bytes()
        parts=[(r,im)for r,im in objects(read('vram'),read('oam'),read('cgram'),read('registers')[0x2101])if r['palette']==0 and 0<=r['y']<190 and -20<=r['x']<256 and im.getbbox()]
        l=min(r['x']for r,im in parts);t=min(r['y']for r,im in parts);expected=Image.new('RGBA',(pose['width'],pose['height']))
        for r,im in reversed(parts):expected.alpha_composite(im,(r['x']-l,r['y']-t))
        actual=bytes(page.evaluate('i=>{$("pose").value=i;render();return Array.from(ctx.getImageData(0,0,canvas.width,canvas.height).data)}',i))
        assert expected.tobytes()==actual,pose['capture'];count+=1
    assert count>0;b.close()
server.shutdown();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'captured_previews_pixel_exact':count,'known_directory_pieces':1720,'complete_live_coverage':False},indent=2)+'\n');print(count,'Sting previews pixel-exact against native PPU snapshots')
