"""Verify prepared themes upload, use the melodic sample and loop natively."""
import argparse,json,os,subprocess,sys,struct,wave
from pathlib import Path

def values(data):return bytes(data if isinstance(data,list)else(data[str(i)]for i in range(len(data))))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['core','rom','expectations','capture_root']:p.add_argument(name,type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();repo=Path(__file__).resolve().parents[1]
    a.output.mkdir(parents=True,exist_ok=True);order=[1,2,3,4,5,6,7,8,9,10,11,0];results=[]
    for entry in json.loads(a.expectations.read_text()):
        id=int(entry['id']);previous=(order.index(id)-1)%12
        state=a.capture_root/'roster-menu-cycle-settled'/f'frame-{previous*300:06d}.state'
        if not previous:state=a.capture_root/'roster-selection-ready/frame-000300.state'
        name='sting'if id==7 else'luger';folder=a.output/name;song=entry['song'];compiled=entry['compiled'];frames=round(song['duration']*1.2*2)+360
        env={**os.environ,'WWF_AUDIO_PROBE':'1','WWF_TRACE_DIR':str(folder.resolve())}
        cmd=[sys.executable,str(repo/'tools/run_headless.py'),str(a.core),str(a.rom),'--output',str(folder),'--load-state',str(state),'--frames',str(frames),'--interval',str(frames),'--press','1:7','--audio']
        for n in [90,180,300]:cmd+=['--snapshot-frame',str(n)]
        subprocess.run(cmd,env=env,check=True,stdout=subprocess.DEVNULL)
        spc=(folder/f'frame-{frames:06d}-spc-ram.bin').read_bytes();header=values(compiled['header']);theme=entry['theme']
        assert spc[0x24e0+theme*2:0x24e2+theme*2]==header[:2];assert spc[0x8c79:0x8c8a]==header[2:]
        for pointer,stream in zip(compiled['pointers'],compiled['streams']):assert spc[pointer:pointer+len(stream)]==values(stream)
        start=compiled['pointers'][0]+13
        loops=[int(line.split()[0])for line in(folder/'score-reads.txt').read_text().splitlines()if line.split()[1]=='1a4d'and int(line.split()[2],16)==start]
        assert len(loops)>=3 and all(abs((loops[i+1]-loops[i])-song['duration']*1.2)<10 for i in range(2)),loops
        active=[]
        for n in [90,180,300]:
            spc=(folder/f'frame-{n:06d}-spc-ram.bin').read_bytes();dsp=(folder/f'frame-{n:06d}-dsp-registers.bin').read_bytes()
            for voice in range(8):
                if not dsp[voice*16+8]:continue
                at=dsp[0x5d]*256+dsp[voice*16+4]*4
                assert spc[at:at+4]==spc[0x1fb8:0x1fbc],'Active voice is using an effect instead of melodic sample 46'
                active.append(voice)
        assert active,'No active melodic voices'
        with wave.open(str(folder/'audio.wav'))as sound:
            rate=sound.getframerate();raw=sound.readframes(sound.getnframes())
        clip=raw[int(1.25*rate)*4:int(16.25*rate)*4];peak=max(map(abs,struct.unpack('<'+'h'*(len(clip)//2),clip)));assert peak>100
        with wave.open(str(a.output/(name+'-in-game.wav')),'wb')as sound:
            sound.setnchannels(2);sound.setsampwidth(2);sound.setframerate(rate);sound.writeframes(clip)
        result={'file':song['name'],'wrestler_id':id,'duration_seconds':song['duration']/50,'native_voices':compiled['voices'],
                'all_eight_streams_uploaded_exactly':True,'loop_start_frames':loops[:3],
                'whole_song_loops_twice':True,'active_voices_checked':sorted(set(active)),
                'native_melodic_sample':46,'razor_intro_sample_excluded':50,'native_audio_peak':peak}
        results.append(result);print(json.dumps(result),flush=True)
    (a.output/'native-verification.json').write_text(json.dumps({'themes':results,'method':'Controller-generated selection states, then Right input; pinned Snes9x with read-only SPC/DSP probes.'},indent=2)+'\n')
