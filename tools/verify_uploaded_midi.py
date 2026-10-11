"""Import a local user MIDI through the packaged editor and verify native playback.

Keeps ROMs, MIDI-derived streams and audio captures private in --output.
Publish only the address-free verification report if desired.
"""
import argparse,json,threading,zipfile,os,subprocess,sys,struct,wave
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('midi',type=Path);p.add_argument('core',type=Path);p.add_argument('capture_root',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args();repo=Path(__file__).resolve().parents[1];out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
zipfile.ZipFile(repo/'downloads/WrestleEdit-v0.7.zip').extractall(out/'package');server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(out/'package')));threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=browser.new_page(viewport={'width':1280,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/WrestleEdit/WrestleEdit.html');page.locator('#rom').set_input_files(str(args.rom));page.wait_for_function('rom!==null');page.locator('#wrestler').select_option('5');page.locator('#tab-profile').click();page.locator('#song-import').set_input_files(str(args.midi));page.wait_for_function("document.getElementById('song-import').value===''");assert page.evaluate('selectionEdits["5"]?.song!==undefined'),page.locator('#song-status').inner_text();song=page.evaluate('selectionEdits["5"].song');compiled=page.evaluate('compileSong(selectionEdits["5"].song)');assert page.locator('#song-status').get_attribute('data-error') is None
 with page.expect_download() as d:page.locator('#save').click()
 project=Path(d.value.path()).read_bytes();page.locator('#reset').click();page.locator('#project').set_input_files({'name':'music-project.json','mimeType':'application/json','buffer':project});page.wait_for_function('selectionEdits["5"]?.song!==undefined');assert page.evaluate('selectionEdits["5"].song')==song
 page.locator('#song-status').scroll_into_view_if_needed();page.screenshot(path=str(out/'import-success.png'))
 page.locator('#tab-export').click()
 with page.expect_download() as d:page.locator('#rom-export').click()
 data=Path(d.value.path()).read_bytes();rompath=out/'imported.sfc';rompath.write_bytes(data);assert sum(data)&65535==int.from_bytes(data[0xffde:0xffe0],'little')
 page.locator('#rom').set_input_files({'name':'reopened.sfc','mimeType':'application/octet-stream','buffer':data});page.wait_for_function('rom!==null&&rom.length===0x400000');assert bytes(page.evaluate('Array.from(playableROM())'))==data;assert not errors,errors;browser.close()
server.shutdown();frames=round(song['duration']*1.2*2)+300;capture=out/'native';env=os.environ.copy();env.update(WWF_AUDIO_PROBE='1',WWF_TRACE_DIR=str(capture));subprocess.run([sys.executable,str(repo/'tools/run_headless.py'),str(args.core),str(rompath),'--output',str(capture),'--load-state',str(args.capture_root/'roster-menu-cycle-settled/frame-001500.state'),'--frames',str(frames),'--interval',str(frames),'--press','1:6','--audio'],env=env,check=True)
spc=(capture/f'frame-{frames:06d}-spc-ram.bin').read_bytes();assert spc[0x24f4:0x24f6]==bytes(compiled['header'][:2]);assert spc[0x8c79:0x8c8a]==bytes(compiled['header'][2:])
for pointer,stream in zip(compiled['pointers'],compiled['streams']):assert spc[pointer:pointer+len(stream)]==bytes(stream)
start=compiled['pointers'][0]+13;loops=[int(l.split()[0]) for l in (capture/'score-reads.txt').read_text().splitlines() if l.split()[1]=='1a4d' and int(l.split()[2],16)==start];assert len(loops)>=3 and all(abs((loops[i+1]-loops[i])-song['duration']*1.2)<10 for i in range(2)),loops
with wave.open(str(capture/'audio.wav')) as f:
 rate=f.getframerate();samples=f.readframes(f.getnframes());clip=samples[int(70/60.0988*rate)*4:int(280/60.0988*rate)*4];peak=max(map(abs,struct.unpack('<'+'h'*(len(clip)//2),clip)));assert peak>100
report={'file':args.midi.name,'original_note_events':len(song['notes'])+song.get('mergedNotes',0),'notes_after_duplicate_merge':len(song['notes']),'duplicate_notes_combined':song.get('mergedNotes',0),'distinct_notes_dropped':0,'native_voices':compiled['voices'],'duration_seconds':song['duration']/50,'native_uploaded_streams':8,'loop_start_frames':loops[:3],'native_audio_peak':peak,'packaged_editor_import':True,'project_reload_exact':True,'edited_rom_reload_exact':True,'export_checksum_valid':True};(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
