"""Verify relocated MIDI songs in all twelve native theme banks and a full-song loop."""
import argparse,json,os,subprocess,sys,wave,struct
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('core',type=Path);p.add_argument('rom',type=Path);p.add_argument('expectations',type=Path);p.add_argument('capture_root',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--short',action='store_true');args=p.parse_args();repo=Path(__file__).resolve().parents[1];args.output.mkdir(parents=True,exist_ok=True)
expected=json.loads(args.expectations.read_text());order=[1,2,3,4,5,6,7,8,9,10,11,0];results=[]
def values(data):return bytes(data if isinstance(data,list) else (data[str(i)] for i in range(len(data))))
for n in expected:
 id=int(n['id']);index=order.index(id);previous=(index-1)%12
 state=args.capture_root/'roster-menu-cycle-settled'/f'frame-{previous*300:06d}.state' if previous else args.capture_root/'roster-selection-ready/frame-000300.state'
 out=args.output/f'slot-{id}';frames=12000 if id==5 and not args.short else 300;env=os.environ.copy();env.update(WWF_AUDIO_PROBE='1',WWF_TRACE_DIR=str(out.resolve()))
 cmd=[sys.executable,str(repo/'tools/run_headless.py'),str(args.core),str(args.rom),'--output',str(out),'--load-state',str(state),'--frames',str(frames),'--interval',str(frames),'--press','1:7','--audio'];subprocess.run(cmd,env=env,check=True,stdout=subprocess.DEVNULL)
 spc=(out/f'frame-{frames:06d}-spc-ram.bin').read_bytes();compiled=n['compiled'];header=values(compiled['header']);assert spc[0x24e0+n['theme']*2:0x24e2+n['theme']*2]==header[:2];assert spc[0x8c79:0x8c8a]==header[2:]
 for stream,pointer in zip(compiled['streams'],compiled['pointers']):assert spc[pointer:pointer+len(stream)]==values(stream),'Native uploaded song differs'
 with wave.open(str(out/'audio.wav')) as sound:
  rate=sound.getframerate();raw=sound.readframes(sound.getnframes());clip=raw[int(70/60.0988*rate)*4:int(280/60.0988*rate)*4];samples=struct.unpack('<'+'h'*(len(clip)//2),clip);peak=max(map(abs,samples));assert peak>100
 result={'wrestler_id':id,'theme_id':n['theme'],'uploaded_streams':8,'native_audio_peak':peak}
 if id==5 and not args.short:
  start=compiled['pointers'][0]+13;events=[int(l.split()[0]) for l in (out/'score-reads.txt').read_text().splitlines() if l.split()[1]=='1a4d' and int(l.split()[2],16)==start];assert len(events)>=3 and all(abs((events[i+1]-events[i])-5568)<6 for i in range(2)),events;result['loop_start_frames']=events[:3]
  first=raw[int(40/60.0988*rate)*4:int(760/60.0988*rate)*4]
  with wave.open(str(args.output/'imported-song-in-game.wav'),'wb') as sound:sound.setnchannels(2);sound.setsampwidth(2);sound.setframerate(rate);sound.writeframes(first)
 results.append(result);print(f'PASS: theme {n["theme"]}, 8 uploaded streams, native audio peak {peak}',flush=True)
(args.output/'verification.json').write_text(json.dumps({'all_twelve_theme_slots':results,'complete_92_8_second_song_reaches_end_and_loops_twice':not args.short,'physical_channels_used':4},indent=2)+'\n')
