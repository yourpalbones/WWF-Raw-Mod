"""Check native SPC sequence execution, untouched samples, and captured audio."""
import argparse,json,struct,wave
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('original',type=Path);parser.add_argument('probe',type=Path);parser.add_argument('capture',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
meta=json.loads((args.probe/'patch.json').read_text());original=args.original.read_bytes();edited=(args.probe/'theme-melody-probe.sfc').read_bytes();allowed=bytearray(len(original));allowed[0xffdc:0xffe0]=b'\x01'*4
for r in meta['changes']:allowed[r['source']:r['source']+r['length']]=b'\x01'*r['length']
assert all(a==b or allowed[i] for i,(a,b) in enumerate(zip(original,edited))),'Unexpected changes outside sequence blocks and checksum'
spc=(args.capture/'frame-001400-spc-ram.bin').read_bytes()
for r in meta['changes']:assert spc[r['destination']:r['destination']+r['length']]==edited[r['source']:r['source']+r['length']]
events=[]
for line in (args.capture/'score-reads.txt').read_text().splitlines():
 values=line.split()
 if values[1]=='1a4d':events.append({'frame':int(values[0]),'address':int(values[2],16),'value':int(values[3],16)})
r=meta['changes'][0];played=[next(e for e in events if e['address']==r['destination']+4+i*2) for i in range(8)];assert [e['value']-0x60 for e in played]==meta['note_indices'];assert all(played[i]['frame']<played[i+1]['frame'] for i in range(7));assert any(e['address']==r['destination']+20 and e['value']==0xf0 for e in events)
with wave.open(str(args.capture/'audio.wav')) as sound:
 rate=sound.getframerate();samples=sound.readframes(sound.getnframes());start=int(40/60.0988*rate);end=int(270/60.0988*rate);clip=samples[start*4:end*4]
values=struct.unpack('<'+'h'*(len(clip)//2),clip);peak=max(map(abs,values));assert peak>100 and sum(v!=0 for v in values)>rate
args.output.mkdir(parents=True,exist_ok=True)
with wave.open(str(args.output/'custom-melody.wav'),'wb') as sound:sound.setnchannels(2);sound.setsampwidth(2);sound.setframerate(rate);sound.writeframes(clip)
result={'native_spc_streams_verified':8,'new_notes_played':meta['note_indices'],'note_frames':[e['frame'] for e in played],'native_end_command_executed':True,'only_sequence_blocks_and_checksum_changed':True,'sample_and_instrument_data_preserved':True,'audio_sample_rate':rate,'audio_peak':peak,'scope':'Original test melody in Razor theme slot, not arbitrary audio import'}
(args.output/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS: eight new notes executed by the native audio driver; all samples preserved; non-silent audio captured')
