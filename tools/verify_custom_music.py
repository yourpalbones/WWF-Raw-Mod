"""Exercise full MIDI import, native relocation, undo/projects and edited ROM reload."""
import argparse,json,threading,struct
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright

def vlq(n):
 out=[n&127];n>>=7
 while n:out.insert(0,(n&127)|128);n>>=7
 return bytes(out)
def midi(tracks):
 return b'MThd'+struct.pack('>IHHH',6,1,len(tracks),480)+b''.join(b'MTrk'+struct.pack('>I',len(t))+t for t in tracks)
def fixture():
 tempo=b'\0\xff\x51\x03\x07\xa1\x20'+vlq(480*32)+b'\xff\x51\x03\x09\x27\xc0'+vlq(480*128)+b'\xff\x2f\x00'
 tracks=[tempo]
 for ch in range(4):
  t=bytearray()
  for i in range(160):
   pitch=[48,55,60,64][ch]+[0,2,4,7][i%4];t+=b'\0'+bytes([0x90+ch,pitch,70+ch*12])+vlq(360)+bytes([0x80+ch,pitch,0])+vlq(120)+bytes([0xb0+ch,1,0])
  t+=b'\0\xff\x2f\0';tracks.append(bytes(t))
 return midi(tracks)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();repo=Path(__file__).resolve().parents[1];args.output.mkdir(parents=True,exist_ok=True);song=fixture();(args.output/'original-theme.mid').write_bytes(song)
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)));threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=browser.new_page(viewport={'width':1300,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html');page.locator('#rom').set_input_files(str(args.rom));page.wait_for_function('rom!==null');page.locator('#tab-profile').click();page.locator('#wrestler').select_option('5');page.locator('#song-import').set_input_files(str(args.output/'original-theme.mid'));page.wait_for_function('selectionEdits["5"]?.song!==undefined');result=page.evaluate('({song:selectionEdits["5"].song,compiled:compileSong(selectionEdits["5"].song)})');print('Imported',len(result['song']['notes']),result['compiled']['voices'],result['song']['duration']);assert len(result['song']['notes'])==640 and result['compiled']['voices']==4 and result['song']['duration']==4640
  # Running status, velocity-zero release, and sustain pedal.
  sustained=midi([b'\0\xb0\x40\x7f\0\x90\x3c\x64'+vlq(240)+b'\x3c\0'+vlq(240)+b'\xb0\x40\0\0\xff\x2f\0'])
  parsed=page.evaluate('b=>readMIDI(new Uint8Array(b))',list(sustained));assert parsed['notes']==[{'start':0,'end':25,'pitch':60,'velocity':100}]
  # Layered MIDI duplicates are redundant when using one native instrument.
  duplicated=midi([b'\0\x90\x3c\x64\0\x91\x3c\x70'+vlq(480)+b'\x80\x3c\0\0\x81\x3c\0\0\xff\x2f\0'])
  merged=page.evaluate('b=>readMIDI(new Uint8Array(b))',list(duplicated));assert merged['mergedNotes']==1 and merged['notes']==[{'start':0,'end':25,'pitch':60,'velocity':112}]
  saved=page.evaluate('JSON.stringify(selectionEdits)')
  for bad in [b'not midi',song[:-10],midi([b'\0\x99\x24\x64'+vlq(480)+b'\x89\x24\0\0\xff\x2f\0']),midi([b'\0\x90\x7f\x64'+vlq(480)+b'\x80\x7f\0\0\xff\x2f\0'])]:
   page.locator('#song-import').set_input_files({'name':'bad.mid','mimeType':'audio/midi','buffer':bad});page.wait_for_function("document.getElementById('song-import').value===''");assert page.evaluate('JSON.stringify(selectionEdits)')==saved;assert page.locator('#song-status').get_attribute('data-error')=='true';assert page.locator('#song-status').inner_text().startswith('Import failed:')
  assert page.evaluate("(()=>{const s=structuredClone(selectionEdits['5'].song);s.notes=Array.from({length:9},(_,i)=>({start:0,end:20,pitch:40+i,velocity:100}));try{compileSong(s);return false}catch(e){return e.message.includes('eight')}})()")
  page.locator('#song-restore').click();assert page.evaluate('!selectionEdits["5"].song');page.locator('#undo').click();assert page.evaluate('JSON.stringify(selectionEdits)')==saved
  with page.expect_download() as d:page.locator('#save').click()
  project=Path(d.value.path()).read_bytes();assert json.loads(project)['version']==8;page.locator('#reset').click();page.locator('#project').set_input_files({'name':'song-project.json','mimeType':'application/json','buffer':project});page.wait_for_function('selectionEdits["5"]?.song!==undefined');assert page.evaluate('JSON.stringify(selectionEdits)')==saved
  legacy=json.loads(project);legacy['version']=7;legacy['selection_edits']['5']['song']['instrument']=112
  page.locator('#project').set_input_files({'name':'legacy-effect-project.json','mimeType':'application/json','buffer':json.dumps(legacy).encode()});page.wait_for_function('selectionEdits["5"].song.instrument===113');assert page.evaluate('JSON.stringify(selectionEdits)')==saved
  # All twelve upload directories fit without sharing relocated song storage.
  page.evaluate("()=>{const song=selectionEdits['5'].song;for(const id of Object.keys(S.characters))selectionEdits[id]={song:structuredClone(song),theme:S.characters[id].theme};render();}")
  exported=bytes(page.evaluate('Array.from(playableROM())'));(args.output/'all-12-custom.sfc').write_bytes(exported);original=args.rom.read_bytes();allow=bytearray(len(original));allow[0xffdc:0xffe0]=b'\1'*4
  for offset,size in page.evaluate('customMusicRecords().records.map(([o,b])=>[o,b.length])'):
   if offset<len(original):allow[offset:offset+size]=b'\1'*size
  for c in page.evaluate('Object.values(S.characters)'):allow[c['theme_offset']]=1
  assert all(a==b or allow[i] for i,(a,b) in enumerate(zip(original,exported))),'Changed original samples, instruments or unrelated data'
  assert sum(exported)&65535==int.from_bytes(exported[0xffde:0xffe0],'little')
  native=[]
  for id,meta in page.evaluate('Object.entries(S.characters)'):
   native.append({'id':id,'theme':meta['theme'],'bank':original[0x11936+meta['theme']],'compiled':result['compiled']})
  (args.output/'native-expectations.json').write_text(json.dumps(native,indent=2))
  page.screenshot(path=str(args.output/'workshop.png'),full_page=True)
  page.locator('#rom').set_input_files({'name':'custom-edited.sfc','mimeType':'application/octet-stream','buffer':exported});page.wait_for_function('rom!==null&&rom.length===0x400000');assert bytes(page.evaluate('Array.from(playableROM())'))==exported
  # A further import must preserve the other eleven custom-bank pointers.
  page.locator('#wrestler').select_option('5');page.locator('#song-loop').uncheck();page.locator('#song-import').set_input_files(str(args.output/'original-theme.mid'));page.wait_for_function('selectionEdits["5"]?.song?.loop===false');edited=bytes(page.evaluate('Array.from(playableROM())'))
  for n in native:
   if n['id']!='5':at=0x11903+n['bank']*3;assert edited[at:at+3]==exported[at:at+3]
  assert not errors,errors;browser.close()
 server.shutdown();report={'full_midi_notes':640,'duration_seconds':92.8,'tempo_changes':True,'polyphonic_voices':4,'sustain_and_running_status':True,'malformed_and_unsupported_imports_atomic':True,'polyphony_overflow_refused':True,'undo_and_project8_reload':True,'twelve_independent_theme_slots':True,'stock_samples_and_instruments_preserved':True,'edited_rom_reload_byte_exact':True};(args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS: full 92.8-second four-voice MIDI, tempo/sustain/running status, import refusal, undo/projects, 12 independent songs and edited-ROM reload')
if __name__=='__main__':main()
