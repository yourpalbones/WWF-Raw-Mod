"""Verify the preview uses the native melodic BRR sample, and native notes are pitched."""
import argparse,json,threading,math,struct,wave
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('native_capture',type=Path);p.add_argument('nwo_capture',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args();repo=Path(__file__).resolve().parents[1];args.output.mkdir(parents=True,exist_ok=True)
spc=(args.native_capture/'frame-000090-spc-ram.bin').read_bytes();dsp=(args.native_capture/'frame-000090-dsp-registers.bin').read_bytes();start=int.from_bytes(spc[0x200:0x202],'little');loop=int.from_bytes(spc[0x202:0x204],'little');assert dsp[0x5d]==2 and spc[0x200:0x204]==spc[0x1fb8:0x1fbc];assert start==0x44ca and loop==0x44dc
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repo)));threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html');page.locator('#rom').set_input_files(str(args.rom));page.wait_for_function('rom!==null');assert page.locator('#song-instrument').input_value()=='113';sample=page.evaluate('Array.from(decodeMusicSample(113).pcm)');assert len(sample)==3424
 # Reference the emulator BRR arithmetic against the actual uploaded bytes.
 expected=[];older=previous=0;pos=start
 while True:
  header=spc[pos];shift=header>>4;filter=header&12
  for i in range(16):
   n=(spc[pos+1+i//2]>>(0 if i%2 else 4))&15;n=n-16 if n&8 else n;s=(n<<shift)>>1 if shift<=12 else n&~2047;p1=previous;p2=older>>1
   if filter>=8:
    s+=p1-p2;s+=(p2>>4)+((p1*-3)>>6) if filter==8 else ((p1*-13)>>7)+((p2*3)>>4)
   elif filter:s+=(p1>>1)+((-p1)>>5)
   s=max(-32768,min(32767,s));s=(s*2+32768)%65536-32768;older=previous;previous=s;expected.append(s/32768)
  pos+=9
  if header&1:break
 assert expected==sample,'Browser preview sample differs from native BRR arithmetic'
 page.evaluate("()=>{selectionEdits[M.id]={song:{version:1,name:'pitch-test',instrument:113,loop:false,duration:100,notes:[{start:0,end:40,pitch:60,velocity:100},{start:50,end:90,pitch:72,velocity:100}]}};render();const create=AudioContext.prototype.createBufferSource;window.previewSources=[];AudioContext.prototype.createBufferSource=function(){const node=create.call(this);previewSources.push(node);return node};AudioContext.prototype.createOscillator=function(){throw Error('Generic oscillator must not be used')}}")
 page.locator('#tab-profile').click();page.locator('#song-preview').click();page.wait_for_function('window.previewSources?.length===2');assert page.evaluate('previewSources.every(s=>s.loop&&s.buffer.length===3424)');rates=page.evaluate('previewSources.map(s=>s.playbackRate.value)');assert abs(rates[1]/rates[0]-2)<1e-6;assert abs(rates[0]*4096-int.from_bytes(dsp[2:4],'little'))<=2;page.locator('#song-stop').click();assert not errors,errors;b.close()
server.shutdown()
# Verify the real NWO playback points active voices at sample 46, never Razor's sample 50.
frame=15384;ns=(args.nwo_capture/f'frame-{frame:06d}-spc-ram.bin').read_bytes();nd=(args.nwo_capture/f'frame-{frame:06d}-dsp-registers.bin').read_bytes();active=[]
for i in range(8):
 if nd[i*16+8]:
  entry=nd[0x5d]*256+nd[i*16+4]*4;assert ns[entry:entry+4]==ns[0x1fb8:0x1fbc];active.append(i)
assert active
import numpy as np
with wave.open(str(args.native_capture/'audio.wav')) as f:r=f.getframerate();pcm=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').reshape(-1,2).mean(axis=1)
frequencies=[]
for a in [1.05,3.35]:
 data=pcm[int(a*r):int((a+.18)*r)];power=abs(np.fft.rfft((data-data.mean())*np.hanning(len(data))));frequencies.append(float(np.argmax(power)*r/len(data)))
assert abs(frequencies[0]-261.6256)<4 and abs(frequencies[1]-523.2511)<4
report={'default_native_instrument':113,'native_sample_index':46,'razor_intro_sample_index_excluded':50,'native_test_frequencies_hz':frequencies,'browser_preview_matches_native_brr_decode':True,'preview_uses_game_sample_not_triangle_oscillator':True,'preview_reference_dsp_pitch':661,'native_reference_dsp_pitch':int.from_bytes(dsp[2:4],'little'),'nwo_active_voices_point_to_melodic_sample':active,'scope':'Matching sample and pitch; browser envelopes/effects remain approximate'};(args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
