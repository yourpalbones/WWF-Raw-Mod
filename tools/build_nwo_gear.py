"""Build isolated Nash/Syxx native gear packs and the shared sprite dispatcher."""
import json,hashlib,argparse
from pathlib import Path
from scott_frame_catalog import catalog,raster
from build_scott_hall_gear import components
from build_bret_gear import planar
from build_shawn_kick_prototype import Program
from decode_sprite_tile import encode_sprite_tile,decode_sprite_tile
CONFIGS={10:dict(name='Kevin Nash',frames_start=0x4c0100,frames_end=0x4e0000,packets_start=0x4e0000,packets_end=0x560000,pointers=0x5f0000,pointer_end=0x5fa000,primary_table=0x410000,secondary_table=0x411000,program=0x412000,signature_offset=0x416000,signature='NASH-NATIVE-GEAR2'),9:dict(name='Syxx',frames_start=0x560100,frames_end=0x580000,packets_start=0x580000,packets_end=0x5f0000,pointers=0x5fa000,pointer_end=0x600000,primary_table=0x413000,secondary_table=0x414000,program=0x415000,signature_offset=0x417000,signature='SYXX-NATIVE-GEAR3'),5:dict(name='Scott Hall',frames_start=0x420100,frames_end=0x440000,packets_start=0x440000,packets_end=0x4b0000,pointers=0x4b0000,pointer_end=0x4bc000,primary_table=0x4bc000,secondary_table=0x4bd000,program=0x4be000,signature_offset=0x4bf000,signature='SCOTT-HALL-GEAR3')}
def emit_address(p,opcode,address):p.emit(opcode+' '+address.to_bytes(3,'little').hex(' '))
def dispatcher(secondary=None):
 p=Program()
 if secondary is None:
  p.emit('48 a5 82 29 ff 00')
  for slot,c in CONFIGS.items():
   for bank in[c['frames_start']>>16,(c['frames_end']>>16)-1]:
    label=f'next{slot}_{bank}';p.emit('c9 '+bank.to_bytes(2,'little').hex(' '));p.branch('d0',label);emit_address(p,'5c',c['program']+0x500);p.label(label)
  p.emit('68 cf 48 0f 00 5c e8 f6 ac')
 else:
  p.emit('08 48 da a6 36 bd 74 0b')
  for slot,c in CONFIGS.items():
   label=f'next{slot}';p.emit('c9 '+(slot*2).to_bytes(2,'little').hex(' '));p.branch('d0',label);emit_address(p,'af',c['signature_offset']);p.emit('c9 '+c['signature'][:2].encode().hex(' '));p.branch('d0','fallback');emit_address(p,'5c',c['program']+(0x400 if secondary else 0x300));p.label(label)
  p.label('fallback');p.emit('fa 68 28 '+('7f 47 d5 ad 5c 1d ed 80'if secondary else'7f 13 d5 ad 5c c5 ec 80'))
 return p.finish()
def worker(c,secondary=False):
 p=Program();p.emit('fa 68 c9 '+('76 08'if secondary else'b2 0b'));p.branch('b0','original');p.emit('48 da aa');table=c['secondary_table']if secondary else c['primary_table'];emit_address(p,'bf',table);p.branch('f0','unmapped');p.emit('85 80');emit_address(p,'bf',table+2);p.emit('29 ff 00 85 82 fa 68 28 a5 80');p.emit('99 50 05 a5 82 99 52 05 5c 38 ed 80'if secondary else'99 4e 05 a5 82 99 50 05 c8 c8 5c e2 ec 80');p.label('unmapped');p.emit('fa 68');p.label('original');p.emit('28 '+('7f 47 d5 ad 5c 1d ed 80'if secondary else'7f 13 d5 ad 5c c5 ec 80'));return p.finish()
def lookup(c):
 p=Program();p.emit('68 48 c9 00 c0');p.branch('90','fallback');p.emit('68 29 ff 3f da 48 0a 18 63 01 aa 68');emit_address(p,'bf',c['pointers']);p.emit('85 db e2 20');emit_address(p,'bf',c['pointers']+2);p.emit('85 dd c2 20 fa')
 if c['name']=='Scott Hall':
  emit_address(p,'af',c['signature_offset']+15);p.emit('29 ff 00 c9 31 00');p.branch('d0','raw');p.emit('a9 01 00 6b');p.label('raw')
 p.emit('a9 00 00 6b');p.label('fallback');p.emit('68 cf 48 0f 00 5c e8 f6 ac');return p.finish()
def programs():
 result=[]
 for offset,code,hook,expected in[(0x4be000,dispatcher(),0x2cf6e4,'cf480f00'),(0x4be100,dispatcher(False),0xecc1,'7f13d5ad'),(0x4be200,dispatcher(True),0xed19,'7f47d5ad')]:result.append(dict(offset=offset,code=list(code),hook=hook,expected=list(bytes.fromhex(expected))))
 for c in CONFIGS.values():
  for delta,code in[(0x300,worker(c)),(0x400,worker(c,True)),(0x500,lookup(c))]:result.append(dict(offset=c['program']+delta,code=list(code)))
 return result

def head_part(part):
 size=part['size'];head={}
 for y in range(size):
  for x in range(size):
   ref=part['refs'][(y//8)*(size//8)+x//8];v=ref['pixels'][y%8*8+x%8]
   if v:head[x,y]=v
 def world(q):
  x,y=q;return part['x']+(size-1-x if part['hflip']else x),part['y']+(size-1-y if part['vflip']else y)
 return head,world

def decorate(frame,slot):
 from native_gear_art import decorate as author
 return author(frame,slot)

def checksum(out):
 out[0xffd5]=0x25;out[0xffd7]=13;out[0x400000:0x410000]=out[:65536]
 for o in[0xffdc,0x40ffdc]:out[o:o+4]=bytes.fromhex('ffff0000')
 s=(sum(out[:0x400000])+2*sum(out[0x400000:]))&65535
 for o in[0xffdc,0x40ffdc]:out[o:o+4]=(s^65535).to_bytes(2,'little')+s.to_bytes(2,'little')
def build(base,wram,slot):
 c=CONFIGS[slot];frames=catalog(base,wram,slot);known=json.loads((Path(__file__).resolve().parents[1]/'data/nwo-common-frame-ids.json').read_text())[str(slot)];frames.sort(key=lambda f:bool(f.get('common')and f['index']not in known[f['kind']]));out=bytearray(base)+bytearray(b'\xff'*(0x600000-len(base)));
 for start,end in[(c['frames_start'],c['frames_end']),(c['packets_start'],c['packets_end']),(c['pointers'],c['pointer_end'])]:out[start:end]=b'\xff'*(end-start)
 out[c['primary_table']:c['primary_table']+998*3]=bytes(998*3);out[c['secondary_table']:c['secondary_table']+722*3]=bytes(722*3);fc=c['frames_start'];pc=c['packets_start'];tiles={};descs={};rows=[];fingerprint=hashlib.sha256();metadata=[]
 for f in frames:
  changes=decorate(f,slot);fields=[];descriptor=bytearray(base[f['offset']:f['offset']+f['length']])
  for part in f['parts']:
   for ref in part['refs']:
    pixels=changes.get(ref['field'])
    if pixels is None or pixels==ref['pixels']:continue
    assert all((p==0)==(q==0)for p,q in zip(pixels,ref['pixels']))
    raw=planar(pixels);fingerprint.update(planar(ref['pixels']));fields.append(dict(relative=ref['relative'],source=ref['source'],compressed=ref['compressed'],length=ref['length'],edits=[[i,v]for i,v in enumerate(pixels)if v!=ref['pixels'][i]]))
    if raw not in tiles:
     idx=len(tiles);assert idx<16384 and c['pointers']+idx*3+3<=c['pointer_end']
     if(pc&65535)+36>65536:pc=(pc+65535)&~65535
     assert pc+36<=c['packets_end'],(slot,idx,hex(pc));tiles[raw]=idx;packet=raw;out[pc:pc+len(packet)]=packet;out[c['pointers']+idx*3:c['pointers']+idx*3+3]=pc.to_bytes(3,'little');metadata.append(dict(offset=pc,original_offset=ref['source'],original_compressed=ref['compressed'],original_length=ref['length'],length=36,compressed=False));pc+=36
    descriptor[ref['relative']:ref['relative']+2]=(0xc000|tiles[raw]).to_bytes(2,'little')
  if not fields:continue
  fingerprint.update(base[f['offset']:f['offset']+f['length']]);rows.append(dict(kind=f['kind'],index=f['index'],offset=f['offset'],length=f['length'],tiles=fields));key=bytes(descriptor)
  if key not in descs:
   if(fc&65535)+len(key)>65536:fc=(fc+65535)&~65535
   if(fc&65535)==0:fc+=256
   assert fc+len(key)<=c['frames_end'];descs[key]=fc;out[fc:fc+len(key)]=key;fc+=len(key)
  table=(c['primary_table']if f['kind']=='primary'else c['secondary_table'])+f['index']*3;out[table:table+3]=descs[key].to_bytes(3,'little')
 rgb=lambda r,g,b:r|g<<5|b<<10
 palette={2:rgb(1,1,1),3:rgb(5,5,5),6:rgb(18,0,1),8:rgb(29,3,3),13:rgb(2,1,0),14:rgb(7,4,2)}if slot==10 else{2:rgb(29,2,2),3:rgb(16,0,0),4:rgb(1,1,1),5:rgb(29,29,29),6:rgb(2,1,1),8:rgb(6,6,6)}
 offset=0x2cc4da+slot*32
 for i,v in palette.items():out[offset+i*2:offset+i*2+2]=v.to_bytes(2,'little')
 out[c['signature_offset']:c['signature_offset']+len(c['signature'])]=c['signature'].encode()
 for p in programs():
  out[p['offset']:p['offset']+256]=b'\xff'*256;out[p['offset']:p['offset']+len(p['code'])]=bytes(p['code'])
  if 'hook'in p:out[p['hook']:p['hook']+4]=bytes([0x5c,p['offset']&255,p['offset']>>8&255,p['offset']>>16])
 checksum(out)
 recipe={**c,'private_compressed':False,'version':2,'selector':str(slot),'source_fingerprint':fingerprint.hexdigest(),'palette_offset':offset,'palette':palette,'frames':rows,'programs':programs()};report=dict(selector=slot,known_entries=len(frames),modified_entries=len(rows),private_tiles=len(tiles),tile_sources=metadata,patched_sha256=hashlib.sha256(out).hexdigest());return bytes(out),recipe,report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('selector',type=int,choices=[9,10]);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);out,recipe,report=build(a.rom.read_bytes(),a.wram.read_bytes(),a.selector);(a.output/'gear.sfc').write_bytes(out);(a.output/'recipe.json').write_text(json.dumps(recipe,separators=(',',':')));(a.output/'report.json').write_text(json.dumps(report));print({k:v for k,v in report.items()if k!='tile_sources'})
