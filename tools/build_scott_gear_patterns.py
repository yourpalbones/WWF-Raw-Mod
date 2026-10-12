"""Publish authored pixel-edit instructions and hashes, not source game graphics."""
import argparse,hashlib,json
from pathlib import Path
from scott_frame_catalog import catalog
from build_scott_hall_gear import decorate,lookup_program,part_program,FRAMES,FRAME_END,PACKETS,PACKET_END,POINTERS,POINTER_END,PRIMARY,SECONDARY,PROGRAM,SIGNATURE,MAGIC,PALETTE
from build_bret_gear import planar
p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('patched',type=Path);args=p.parse_args();rom=args.rom.read_bytes();patched=args.patched.read_bytes();frames=catalog(rom,args.wram.read_bytes());rows=[];fingerprint=hashlib.sha256()
for f in frames:
 changes=decorate(f);tiles=[]
 for part in f['parts']:
  for ref in part['refs']:
   new=changes.get(ref['field']);
   if new is None or new==ref['pixels']:continue
   edits=[[i,value]for i,value in enumerate(new)if value!=ref['pixels'][i]];tiles.append({'relative':ref['relative'],'source':ref['source'],'compressed':ref['compressed'],'length':ref['length'],'edits':edits});fingerprint.update(planar(ref['pixels']))
 if not tiles:continue
 fingerprint.update(rom[f['offset']:f['offset']+f['length']]);rows.append({'kind':f['kind'],'index':f['index'],'offset':f['offset'],'length':f['length'],'tiles':tiles})
meta={'version':1,'source_fingerprint':fingerprint.hexdigest(),'frames_start':FRAMES,'frames_end':FRAME_END,'packets_start':PACKETS,'packets_end':PACKET_END,'pointers':POINTERS,'pointer_end':POINTER_END,'primary_table':PRIMARY,'secondary_table':SECONDARY,'signature_offset':SIGNATURE,'signature':MAGIC.decode(),'palette_offset':PALETTE,'palette':{str(i):int.from_bytes(patched[PALETTE+i*2:PALETTE+i*2+2],'little')for i in[2,3,4,5,6,8,13,14]},'frames':rows,'programs':[{'offset':PROGRAM,'hook':0x2cf6e4,'expected':[0xcf,0x48,0x0f,0],'code':list(lookup_program())},{'offset':PROGRAM+0x100,'hook':0xecc1,'expected':[0x7f,0x13,0xd5,0xad],'code':list(part_program(False))},{'offset':PROGRAM+0x200,'hook':0xed19,'expected':[0x7f,0x47,0xd5,0xad],'code':list(part_program(True))}]}
(Path(__file__).resolve().parents[1]/'editor/scott-gear-patterns.js').write_text('window.RAW_SCOTT_GEAR_PATTERNS = '+json.dumps(meta,separators=(',',':'))+';\n');print('Published',len(rows),'frame recipes and authored per-pixel garment edits')
