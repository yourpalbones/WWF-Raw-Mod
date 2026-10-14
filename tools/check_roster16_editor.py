"""Exercise the new editor with a private 16-slot ROM; write no ROMs to Git."""
import argparse,json,threading
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright

class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--midi',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);root=Path(__file__).resolve().parents[1]
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root)));threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/editor-v01/gear-workshop.html')
  def load(path):
   page.locator('#rom').set_input_files(str(path.resolve()));page.wait_for_function('rom!==null');assert page.evaluate('C.characters.length')==16
  def save(name):
   page.locator('#tab-export').click()
   with page.expect_download() as info:page.locator('#rom-export').click()
   target=a.output/name;info.value.save_as(target);return target
  def hashes():return page.evaluate('''async()=>{const out={};for(const c of C.characters.filter(c=>c.v01)){const b=new Uint8Array(Object.keys(c.sources).sort().flatMap(k=>originals[k]));out[c.id]=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),n=>n.toString(16).padStart(2,'0')).join('');}return out;}''')
  load(a.rom);before=hashes();characters=page.evaluate('C.characters.map(c=>({id:c.id,name:c.character,poses:c.poses.length}))');noedit=save('unchanged.sfc');load(noedit);assert hashes()==before
  page.locator('#wrestler').select_option('15');page.locator('#tab-sprite').click();page.locator('#sprite').scroll_into_view_if_needed()
  pixel=page.evaluate('''()=>{const i=cells.findIndex(Boolean),c=cells[i],r=canvas.getBoundingClientRect(),old=pixels(c.key)[c.index];return {key:c.key,index:c.index,color:old===1?2:1,x:r.x+(i%canvas.width+.5)*r.width/canvas.width,y:r.y+(Math.floor(i/canvas.width)+.5)*r.height/canvas.height};}''')
  page.locator('.swatch').nth(pixel['color']-1).click();page.mouse.click(pixel['x'],pixel['y']);assert page.evaluate('Object.keys(edits).length')==1
  page.locator('.swatch').nth(13).click();page.locator('#palette-color').fill('#f8d830');page.locator('#palette-apply').click();expected_palette=page.evaluate('paletteValue(14)')
  page.locator('#tab-profile').click();page.locator('#bio-name').fill('NATURE BOY');page.locator('#bio-apply').click();assert 'saved' in page.locator('#status').text_content().lower()
  page.locator('#monitor-copy').click();expected_monitor=page.evaluate("selectionEdits['15'].monitor.pixels");edited=save('flair-edited.sfc');load(edited);after=hashes();assert before['13']==after['13'] and before['14']==after['14'] and before['15']!=after['15'];page.locator('#wrestler').select_option('15');assert page.evaluate("selectionState('15').bio.name")=='NATURE BOY';assert page.evaluate("vword(rom,C.characters.find(c=>c.id==='15').palette_offset+28)")==expected_palette;assert page.evaluate("originalProfileAssets('15').monitor.pixels")==expected_monitor;page.screenshot(path=str(a.output/'editor-flair.png'))
  if a.midi:
   page.locator('#tab-profile').click();page.locator('#song-import').set_input_files(str(a.midi.resolve()));page.wait_for_timeout(400);assert page.locator('#song-status').get_attribute('data-error') is None,page.locator('#song-status').text_content();music=save('flair-midi.sfc');load(music);assert page.evaluate("romPointer(rom,MUSIC.bankDirectory+rom[0x11936+S.characters['15'].theme]*3)")==0x3bb000
  assert not errors,errors
  report={'characters':characters,'no_edit_sprite_hashes_preserved':True,'flair_edit_changes_only_flair_among_added_workers':True,'flair_name_saved_and_reopened':True,'flair_palette_saved_and_reopened':True,'monitor_copy_exported':True,'midi_exported_and_reopened':bool(a.midi),'page_errors':errors,'before':before,'after':after};(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));browser.close()
 server.shutdown()
if __name__=='__main__':main()
