"""Replace Razor's eight sequence streams with a short original melody and silence.

Research proof only: keeps existing instruments, samples, pointers and lengths.
It does not import arbitrary audio or implement a full sequencer.
"""
import argparse,hashlib,json
from pathlib import Path
from build_bret_gear import ORIGINAL_HASH
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
original=args.rom.read_bytes();assert hashlib.sha256(original).hexdigest()==ORIGINAL_HASH;b=bytearray(original)
bank_pointer=int.from_bytes(b[0x11903+6*3:0x11906+6*3],'little')&0x3fffff;count=int.from_bytes(b[bank_pointer:bank_pointer+2],'little');records=[]
for i in range(count):
 at=bank_pointer+2+i*7;record=b[at:at+7];records.append({'record':at,'length':int.from_bytes(record[:2],'little'),'source':int.from_bytes(record[2:5],'little')&0x3fffff,'destination':int.from_bytes(record[5:],'little')})
header_record=next(r for r in records if r['destination']==0x24e0+10*2);header_pointer=int.from_bytes(b[header_record['source']:header_record['source']+2],'little');header=next(r for r in records if r['destination']==header_pointer);assert b[header['source']]==8
channels=[int.from_bytes(b[header['source']+1+i*2:header['source']+3+i*2],'little') for i in range(8)];notes=[60,64,67,72,67,64,62,60];sequence=bytes([0xf2,63,0xf5,0x70]+[v for note in notes for v in [note+0x60,20]]+[0xf0]);changes=[]
for i,pointer in enumerate(channels):
 record=next(r for r in records if r['destination']==pointer);packet=sequence if i==0 else b'\xf0';assert len(packet)<=record['length'];b[record['source']:record['source']+record['length']]=packet+b'\xff'*(record['length']-len(packet));changes.append({'channel':i,**record,'new_sequence_length':len(packet)})
checksum=(sum(b[:0x200000])+sum(b[0x200000:])*2)&65535;b[0xffdc:0xffe0]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little');(args.output/'theme-melody-probe.sfc').write_bytes(b);(args.output/'patch.json').write_text(json.dumps({'theme_id':10,'bank_id':6,'scope':'short original monophonic sequence using stock instruments; other voices stopped','note_indices':notes,'duration_ticks':20,'instrument':112,'changes':changes},indent=2)+'\n');print('Built local custom melody proof for theme 10; existing instruments and samples retained')
