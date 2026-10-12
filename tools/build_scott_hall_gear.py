"""Patch Scott's native sprites with black/red reference gear and isolated detail tiles.

Uses the user's latest ROM; does not replace the native body artwork. Individual
private descriptors/tiles prevent changes to other wrestlers' shared graphics.
"""
import argparse,hashlib,json
from pathlib import Path
from collections import Counter
from scott_frame_catalog import catalog,raster
from build_bret_gear import planar
from decode_sprite_tile import encode_sprite_tile,decode_sprite_tile
from build_shawn_kick_prototype import Program
PALETTE=0x2cc57a
FRAMES=0x420100;FRAME_END=0x440000
PACKETS=0x440000;PACKET_END=0x4b0000
POINTERS=0x4b0000;POINTER_END=0x4bc000
PRIMARY=0x4bc000;SECONDARY=0x4bd000
PROGRAM=0x4be000;SIGNATURE=0x4bf000
MAGIC=b'SCOTT-HALL-GEAR3'

def components(points,colors):
 remaining={p for p,c in points.items()if c in colors};out=[]
 while remaining:
  seed=remaining.pop();group={seed};pending=[seed]
  while pending:
   x,y=pending.pop()
   for dx in[-1,0,1]:
    for dy in[-1,0,1]:
     q=x+dx,y+dy
     if q in remaining:remaining.remove(q);group.add(q);pending.append(q)
  out.append(group)
 return out

def decorate(frame):
 points,mapping=raster(frame);changes={}
 def put(q,value):
  if q not in mapping:return
  ref,k=mapping[q];changes.setdefault(ref['field'],ref['pixels'].copy())[k]=value
 # Remove the old yellow chain/wrist jewellery in upper-body pieces, retaining
 # garment decoration. Choose an adjacent native skin shade, never paint air.
 if frame['kind']=='primary':
  for q,c in points.items():
   if c not in[6,8]:continue
   x,y=q
   if any(points.get((x+dx,y+dy))in[4,5]for dx in range(-2,3)for dy in range(-2,3)):continue
   skin=[points.get((x+dx,y+dy))for dx in range(-2,3)for dy in range(-2,3)if points.get((x+dx,y+dy))in[7,9,10,11,12,15]]
   if skin:put(q,7 if c==6 else 11)
 # Every mark is clipped to a native garment component. Narrow/edge-on pieces
 # retain their red trim instead of inventing floating lettering.
 gold={q for q,c in points.items()if c in[6,8]}
 for group in components(points,{4,5,6,8}):
  garment={q for q in group if points[q]in[4,5]}
  if not garment:continue
  trunk=any(points[q]in[6,8]for q in group)or any((x+dx,y+dy)in gold for x,y in group for dx in range(-2,3)for dy in range(-2,3))
  if not trunk:
   for q in garment:put(q,2 if points[q]==4 else 3)
   continue
  if len(garment)<5:continue
  l=min(x for x,y in garment);r=max(x for x,y in garment);t=min(y for x,y in garment);b=max(y for x,y in garment);width=r-l+1;height=b-t+1
  if width>27 or height>17:continue
  if width>=7 and height>=4:
   pattern=['11001010010','10101010101','10101110101','10101010010']
   rotate=height>width+3
   pw,ph=(4,11)if rotate else(11,4)
   if width<pw or height<ph:continue
   ox=l+(width-pw)//2;oy=t+(height-ph)//2
   # Remove the old gold Razor glyph in this cloth island before the new mark.
   for q in group:
    if points[q]in[6,8]:put(q,5)
   for yy,row in enumerate(pattern):
    for xx,v in enumerate(row):
     if v!='1':continue
     q=(ox+3-yy,oy+xx)if rotate else(ox+xx,oy+yy)
     if q in group:put(q,8)
 # Native red pad components are short; tall/long boot components retain red.
 if frame['kind']=='secondary':
  for group in components(points,{2,3}):
   l=min(x for x,y in group);r=max(x for x,y in group);t=min(y for x,y in group);b=max(y for x,y in group);width=r-l+1;height=b-t+1
   skin={7,9,10,11,12,15}
   top=sum(points.get((x,t-1))in skin for x in range(l,r+1));bottom=sum(points.get((x,b+1))in skin for x in range(l,r+1));left=sum(points.get((l-1,y))in skin for y in range(t,b+1));right=sum(points.get((r+1,y))in skin for y in range(t,b+1))
   if 5<=len(group)<=110 and 3<=width<=16 and 3<=height<=12 :
    for x,y in group:
     # Red fringe and top trim remain attached to the native pad silhouette.
     if y==t or (y==t+1 and (x-l)%3==0):continue
     put((x,y),1 if points[x,y]==2 else 5)
 # The Edge uses full-body common frames whose trunks use red slots 2/3,
 # unlike the normal Scott cloth in slots 4/5. Keep their native gold-mark
 # garment boundaries, then recolor the cloth rather than the whole palette.
 if frame.get('common'):
  for group in components(points,{2,3,6,8}):
   cloth={q for q in group if points[q]in[2,3]}
   if not cloth:continue
   has_mark=any(points[q]in[6,8]for q in group)
   for q in cloth:put(q,4 if points[q]==2 else 5)
   if has_mark:
    for q in group:
     if points[q]in[6,8]:put(q,8)
 from scott_trunk_art import finish_trunks
 return finish_trunks(frame,changes)

def lookup_program():
 p=Program();p.emit('48 a5 82 29 ff 00 c9 42 00');p.branch('f0','private');p.emit('c9 43 00');p.branch('d0','fallback');p.label('private');p.emit('68 48 c9 00 c0');p.branch('90','fallback')
 p.emit('68 29 ff 3f da 48 0a 18 63 01 aa 68 bf 00 00 4b 85 db e2 20 bf 02 00 4b 85 dd c2 20 fa a9 00 00 6b')
 p.label('fallback');p.emit('68 cf 48 0f 00 5c e8 f6 ac');return p.finish()

def part_program(secondary=False):
 p=Program();p.emit('08 48 da a6 36 bd 74 0b c9 0a 00');p.branch('d0','fallback');p.emit('fa 68 c9 '+('76 08'if secondary else'b2 0b'));p.branch('b0','original');p.emit('48 da aa bf '+('00 d0 4b'if secondary else'00 c0 4b'));p.branch('f0','unmapped');p.emit('85 80 bf '+('02 d0 4b'if secondary else'02 c0 4b')+' 29 ff 00 85 82 fa 68 28 a5 80')
 if secondary:p.emit('99 50 05 a5 82 99 52 05 5c 38 ed 80')
 else:p.emit('99 4e 05 a5 82 99 50 05 c8 c8 5c e2 ec 80')
 p.label('unmapped');p.emit('fa 68');p.branch('80','original');p.label('fallback');p.emit('fa 68');p.label('original');p.emit('28 '+('7f 47 d5 ad 5c 1d ed 80'if secondary else'7f 13 d5 ad 5c c5 ec 80'));return p.finish()

def build(rom,wram,details=True):
 if len(rom)!=0x400000:raise ValueError('Use the latest 4 MiB edited ROM as the base.')
 if sum(rom)&65535!=int.from_bytes(rom[0xffde:0xffe0],'little'):raise ValueError('Invalid source checksum.')
 for address,expect in [(0x2cf6e4,bytes.fromhex('cf480f00')),(0xecc1,bytes.fromhex('7f13d5ad')),(0xed19,bytes.fromhex('7f47d5ad'))]:
  if rom[address:address+4]!=expect:raise ValueError('This ROM already has an unsupported sprite hook.')
 
 frames=catalog(rom,wram);out=bytearray(rom)+bytearray(b'\xff'*(0x600000-len(rom)));cursor=FRAMES;packet_cursor=PACKETS;tiles={};descriptors={};modified=[];tile_sources=[]
 out[PRIMARY:PRIMARY+998*3]=bytes(998*3);out[SECONDARY:SECONDARY+722*3]=bytes(722*3)
 for f in frames:
  changed=decorate(f)if details else{}
  if not changed:continue
  variants=[];data=bytearray(rom[f['offset']:f['offset']+f['length']])
  for part in f['parts']:
   for ref in part['refs']:
    pixels=changed.get(ref['field']);
    if pixels is None or pixels==ref['pixels']:continue
    if any((p==0)!=(q==0)for p,q in zip(pixels,ref['pixels'])):raise ValueError('Detail changes native transparency.')
    raw=planar(pixels)
    if raw not in tiles:
     idx=len(tiles);packet=raw
     if (packet_cursor&65535)+36>65536:packet_cursor=(packet_cursor+65535)&~65535
     if idx>=16384 or POINTERS+idx*3+3>POINTER_END or packet_cursor+36>PACKET_END:raise ValueError(('Scott detail tiles exceed their private space',idx,packet_cursor-PACKETS,cursor-FRAMES,f['kind'],f['index']))
     tiles[raw]=idx;tile_sources.append({'offset':packet_cursor,'original_offset':ref['source'],'original_compressed':ref['compressed'],'original_length':ref['length'],'length':36,'compressed':False});out[packet_cursor:packet_cursor+len(packet)]=packet;assert out[packet_cursor:packet_cursor+32]==raw
     address=packet_cursor;out[POINTERS+idx*3:POINTERS+idx*3+3]=address.to_bytes(3,'little');packet_cursor+=36
    idx=tiles[raw];data[ref['relative']:ref['relative']+2]=(0xc000|idx).to_bytes(2,'little');variants.append(ref['field'])
  if not variants:continue
  key=bytes(data)
  if key not in descriptors:
   if (cursor&65535)+len(data)>65536:cursor=(cursor+65535)&~65535
   if (cursor&65535)==0:cursor+=256
   if cursor+len(data)>FRAME_END:raise ValueError('Scott descriptors exceed their private bank.')
   descriptors[key]=cursor;out[cursor:cursor+len(data)]=data;cursor+=len(data)
  address=descriptors[key];table=(PRIMARY if f['kind']=='primary'else SECONDARY)+f['index']*3;out[table:table+3]=address.to_bytes(3,'little');modified.append({'kind':f['kind'],'index':f['index'],'original':f['pointer'],'private':address,'edited_tiles':len(variants)})
 color=lambda r,g,b:r|g<<5|b<<10
 colors={2:color(17,0,1),3:color(27,2,3),4:color(1,1,1),5:color(5,5,5),6:color(16,0,0),8:color(29,1,2),13:color(5,5,5),14:color(26,26,26)}
 for i,c in colors.items():out[PALETTE+i*2:PALETTE+i*2+2]=c.to_bytes(2,'little')
 programs=[(PROGRAM,lookup_program(),0x2cf6e4),(PROGRAM+0x100,part_program(False),0xecc1),(PROGRAM+0x200,part_program(True),0xed19)]
 for addr,code,hook in programs:out[addr:addr+len(code)]=code;out[hook:hook+4]=bytes([0x5c,addr&255,addr>>8&255,addr>>16])
 out[SIGNATURE:SIGNATURE+len(MAGIC)]=MAGIC
 out[0xffd5]=0x25;out[0xffd7]=13;out[0x400000:0x410000]=out[:0x10000]
 for offset in[0xffdc,0x40ffdc]:out[offset:offset+4]=bytes.fromhex('ffff0000')
 checksum=(sum(out[:0x400000])+2*sum(out[0x400000:]))&65535
 for offset in[0xffdc,0x40ffdc]:out[offset:offset+4]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
 assert (sum(out[:0x400000])+2*sum(out[0x400000:]))&65535==checksum
 patch=bytearray(b'PATCH');baseline=rom+b'\xff'*(len(out)-len(rom));i=0
 while i<len(out):
  if out[i]==baseline[i]:i+=1;continue
  start=i
  while i<len(out)and out[i]!=baseline[i]and i-start<65535:i+=1
  data=out[start:i];patch+=start.to_bytes(3,'big')+len(data).to_bytes(2,'big')+data
 patch+=b'EOF'
 report={'base_sha256':hashlib.sha256(rom).hexdigest(),'patched_sha256':hashlib.sha256(out).hexdigest(),'known_directory_entries':len(frames),'wrestler_specific_entries':953,'common_fallback_entries':767,'modified_descriptors':len(descriptors),'modified_directory_entries':len(modified),'private_detail_tiles':len(tiles),'private_packet_bytes':packet_cursor-PACKETS,'private_descriptor_bytes':cursor-FRAMES,'original_silhouettes_retained':True,'other_wrestler_palettes_and_shared_tiles_unchanged':True,'other_user_edits_preserved':True,'stubble_and_chest_hair':'Not added to unverified anatomical regions','complete_live_animation_coverage':False,'frames':modified,'tile_sources':tile_sources}
 return bytes(out),bytes(patch),report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True);out,patch,report=build(args.rom.read_bytes(),args.wram.read_bytes());(args.output/'WWF-Raw-Scott-Hall.sfc').write_bytes(out);(args.output/'scott-hall-gear.ips').write_bytes(patch);(args.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items()if k not in['frames','tile_sources']},indent=2))
