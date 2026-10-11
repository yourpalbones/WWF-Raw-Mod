"""Exercise the browser app's pose imports and local ROM download."""
import argparse,io,json,threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom',type=Path);args=parser.parse_args()
repo=Path(__file__).resolve().parents[1];out=repo/'outputs/app-proof';out.mkdir(parents=True,exist_ok=True)
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1280,'height':950});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html')
 assert not page.evaluate("document.body.classList.contains('has-rom')")
 page.locator('#rom').set_input_files(str(args.rom));page.wait_for_function('rom!==null')
 for id in page.evaluate('C.characters.map(c=>c.id)'):
  page.locator('#wrestler').select_option(id)
  page.evaluate('importPosePixels(ctx.getImageData(0,0,canvas.width,canvas.height).data,canvas.width,canvas.height)')
  assert page.evaluate('Object.keys(edits).length')==0
 page.locator('#wrestler').select_option('1')
 fixture=page.evaluate('''(()=>{const rgba=ctx.getImageData(0,0,canvas.width,canvas.height).data;const target=cells.find(c=>c&&!C.sources[c.key].compressed);const color=palette().findIndex((v,i)=>i>0&&v.some((x,j)=>x!==palette()[pixels(target.key)[target.index]][j]));cells.forEach((c,i)=>{if(c&&c.key===target.key&&c.index===target.index)rgba.set([...palette()[color],255],i*4);});return {width:canvas.width,height:canvas.height,rgba:Array.from(rgba)};})()''')
 image=Image.frombytes('RGBA',(fixture['width'],fixture['height']),bytes(fixture['rgba']));buffer=io.BytesIO();image.save(buffer,format='PNG')
 page.locator('#sprite-import').set_input_files({'name':'pose.png','mimeType':'image/png','buffer':buffer.getvalue()})
 page.wait_for_function("document.getElementById('status').textContent.startsWith('Pose image imported')")
 assert page.evaluate('Object.keys(edits).length')==1
 saved=page.evaluate('edits')
 for failure in ['size','outline']:
  message=page.evaluate('''kind=>{const rgba=ctx.getImageData(0,0,canvas.width,canvas.height).data;if(kind==='outline')rgba[cells.findIndex(c=>!c)*4+3]=255;try{importPosePixels(rgba,canvas.width+(kind==='size'?1:0),canvas.height);return '';}catch(e){return e.message;}}''',failure)
  assert message and page.evaluate('edits')==saved
 page.screenshot(path=str(out/'sprites.png'),full_page=True)
 for tab in ['profile','export','sprite']:
  page.locator('#tab-'+tab).click();assert page.locator('#'+tab+'-panel').is_visible()
  assert page.evaluate('edits')==saved
 page.locator('#tab-export').click()
 with page.expect_download() as d:page.locator('#rom-export').click()
 result=Path(d.value.path()).read_bytes();assert len(result)==len(args.rom.read_bytes());assert result!=args.rom.read_bytes()
 assert (sum(result[:0x200000])+2*sum(result[0x200000:]))&65535==int.from_bytes(result[0xffde:0xffe0],'little')
 page.locator('#tab-profile').click();page.screenshot(path=str(out/'profile.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors,errors
 (out/'verification.json').write_text(json.dumps({'unchanged_pose_imports':12,'edited_png_upload':True,'invalid_imports_atomic':True,'tabs_preserve_edits':True,'playable_rom_download_checksum':True,'mobile_no_horizontal_overflow':True},indent=2)+'\n')
 browser.close()
server.shutdown();print('App workflow, all 12 pose import roundtrips, PNG edit, import refusal, ROM download and mobile layout passed')
