"""Private slot-15 experiment layered over Hogan; not editor/release compatible.

Never run a gear rebuild on this immutable test: banks 5D/5E/6D belong to the
existing maximum gear reservations. The builder refuses occupied banks.
"""
import argparse,json,hashlib
from pathlib import Path
from PIL import Image
import rage_cage_boss_source as cd
import build_hogan_motion_probe as motion
from build_hogan_slot_probe import worker_hook,lookup_hook,palette_hook,ordinary_move_hook
from build_shawn_kick_prototype import Program
from build_nwo_gear import emit_address,checksum
from build_bret_gear import planar
from decode_sprite_tile import encode_sprite_tile
from hogan_profile_probe_assets import configure

ROOTS={0x4596:0,0x45b2:1,0x45c0:2,0x45ce:3,0x45dc:4,0x45ea:5,0x45f8:6,
       0x48d2:68,0x48e0:69,0x48ee:70,0x49e2:100,0x49fe:102,0x4a0c:103,
       0x4a36:112,0x4a44:113,0x4a60:115,
       0x4606:7,0x4614:8,0x4622:9,0x4630:10,0x463e:11,
       0x4692:0,0x46ae:18,0x46bc:19,0x46ca:20,0x46d8:21,0x46e6:22,0x46f4:23,
       0x4702:24,0x4710:25,0x471e:26,0x472c:27,0x473a:28}

def root_hook():
 p=Program();p.emit('85 7c 86 7e 08 48 da a6 36 bd 74 0b c9 1c 00');p.branch('d0','old')
 p.emit('bd 26 05 c9 04 00');p.branch('b0','old');p.emit('a3 01 c9 c8 00');p.branch('d0','old')
 p.emit('a2 00 00');p.label('next');p.emit('a3 03');emit_address(p,'df',0x5d7000);p.branch('f0','found')
 p.emit('e8 e8 e8 e8 e0 '+(len(ROOTS)*4).to_bytes(2,'little').hex(' '));p.branch('90','next');p.emit('a9 00 c0');p.branch('80','set')
 p.label('found');emit_address(p,'bf',0x5d7002);p.label('set');p.emit('85 7c a9 5d 00 85 7e fa 68 28 5c ec f0 80')
 p.label('old');p.emit('fa 68 28');emit_address(p,'5c',0x4af300);return p.finish()

def build(base,stock,chr_path,tab_path,portrait,cram):
 if len(base)!=0x800000 or base[0x19d43f]!=14 or base[0x4aef00:0x4aef0d]!=b'HOGAN14-PROBE':raise ValueError('Requires slot-14 Hogan prototype')
 for bank in (0x5d,0x5e,0x6d):
  if base[bank*65536:(bank+1)*65536]!=b'\xff'*65536:raise ValueError(f'Bank {bank:02x} occupied')
 out=bytearray(base);cd.load_source(chr_path,tab_path)
 record=0x708000+14*45
 if out[record:record+45]!=b'\xff'*45:raise ValueError('Slot 15 profile occupied')
 out[record:record+45]=base[0x708000+13*45:0x708000+14*45]
 configure(out,stock,portrait,slot=14,asset_bank=0x5d,hud_bank=0x6d,name='BIG BOSS MAN',hometown='COBB GA',height='6\'6"',weight='337',special='BOSS SLAM',previous_rows=base[0x4a9000:0x4a9000+14*8])
 # Capture-core CRAM is packed RGB9, host little endian, not bus RGB9.
 colors=[]
 for i in range(16):
  v=int.from_bytes(cram[64+i*2:66+i*2],'little');r,g,b=[round((v>>s&7)*31/7)for s in (0,3,6)];colors.append(r|g<<5|b<<10)
 out[0x5d6a00:0x5d6a20]=b''.join(v.to_bytes(2,'little')for v in colors)
 tiles={};packet=0x6d0000;desc=0x5e0000;reports=[]
 for i,(root,pose)in enumerate(ROOTS.items()):
  image=cd.pose(pose);chunks=motion.pack_objects(image);drawing=bytearray([len(chunks),sum(s==16 for x,y,s in chunks)])
  for x,y,s in chunks:
   dx=x-96;dy=y-129
   if not -64<=dx<64 or not -105<=dy<23:raise ValueError('Unrepresentable pose anchor')
   drawing+=bytes([0,dx&127,(dy+105)&127])
   for ty in range(s//8):
    for tx in range(s//8):
     raw=planar([image.getpixel((x+tx*8+px,y+ty*8+py))for py in range(8)for px in range(8)])
     if raw not in tiles:
      ident=len(tiles);encoded=encode_sprite_tile(raw)
      if packet<0x6d8000 and packet+len(encoded)>0x6d8000:packet=0x6db000
      if packet+len(encoded)>0x6e0000:raise ValueError('Tile pool exhausted')
      at=0x5e8000+ident*3
      if at+3>0x5f0000:raise ValueError('Tile directory exhausted')
      out[at:at+3]=packet.to_bytes(3,'little');out[packet:packet+len(encoded)]=encoded;packet+=len(encoded);tiles[raw]=ident
     drawing+=(0xc000|tiles[raw]).to_bytes(2,'little')
  if desc+len(drawing)>0x5e8000:raise ValueError('Descriptor pool exhausted')
  out[desc:desc+len(drawing)]=drawing;at=0x5db000+i*3;out[at:at+3]=desc.to_bytes(3,'little');desc+=len(drawing)
  profile=0x5dc000+i*10;out[profile:profile+10]=(6000+i*3).to_bytes(2,'little')+bytes.fromhex('00 00 09 80 00 ff ff ff')
  at=0x5d7000+i*4;out[at:at+4]=root.to_bytes(2,'little')+(profile&65535).to_bytes(2,'little')
  reports.append({'raw_root':root,'source_pose':pose,'objects':len(chunks),'tiles':sum((s//8)**2 for x,y,s in chunks)})
 # Extend menu/stat capacity without changing existing 14 records.
 out[0x19d43f]=15
 at=out.find(bytes.fromhex('a9 0d 00'),0x19d420,0x19d440)
 if at<0:raise ValueError('Unsupported menu wrap')
 out[at+1]=14
 at=out.find(bytes.fromhex('c0 1c 00'),0x4afa00,0x4afb00)
 if at<0:raise ValueError('Unsupported relocated initializer')
 out[at+1]=30
 for n in range(6):out[0x708600+n*32+28:0x708600+n*32+30]=b'\xff\xff'
 for at in (0x4a8b00,0x4a8b40):out[at+28:at+30]=base[at+26:at+28]
 out[0x5d8c60:0x5d8c6a]=b''.join(v.to_bytes(2,'little')for v in (234,242,174,190,226))
 # Existing hook code remains in place and receives all non-Boss actors.
 old=motion.ROOTS.copy()
 try:
  motion.ROOTS.clear();motion.ROOTS.update(ROOTS);primary=motion.descriptor_hook()
 finally:motion.ROOTS.clear();motion.ROOTS.update(old)
 primary=primary.replace(bytes.fromhex('c9 1a 00'),bytes.fromhex('c9 1c 00')).replace(bytes.fromhex('00 b0 4a'),bytes.fromhex('00 b0 5d')).replace(bytes.fromhex('02 b0 4a'),bytes.fromhex('02 b0 5d')).replace(bytes.fromhex('5c 00 f0 70'),bytes.fromhex('5c 00 f0 4a'))
 secondary=worker_hook(True).replace(bytes.fromhex('c9 1a 00'),bytes.fromhex('c9 1c 00')).replace(bytes.fromhex('c9 24 00'),bytes.fromhex('c9 09 00')).replace(bytes.fromhex('ff 45'),bytes.fromhex('9b 45')).replace(bytes.fromhex('5c 00 f1 70'),bytes.fromhex('5c 00 f1 4a'))
 pal=palette_hook().replace(bytes.fromhex('c9 1a 00'),bytes.fromhex('c9 1c 00')).replace(bytes.fromhex('80 f2 4a'),bytes.fromhex('80 f2 5d')).replace(bytes.fromhex('00 f8 4a'),bytes.fromhex('00 f2 4a'))
 lookup=lookup_hook().replace(bytes.fromhex('c9 54 00'),bytes.fromhex('c9 5e 00')).replace(bytes.fromhex('00 88 4a'),bytes.fromhex('00 80 5e')).replace(bytes.fromhex('02 88 4a'),bytes.fromhex('02 80 5e')).replace(bytes.fromhex('5c 00 f2 70'),bytes.fromhex('5c 00 f4 4a'))
 ordinary=ordinary_move_hook().replace(bytes.fromhex('c9 1a 00'),bytes.fromhex('c9 1c 00')).replace(bytes.fromhex('a9 4a 00'),bytes.fromhex('a9 5d 00')).replace(bytes.fromhex('bf 59 d8 ad 5c 2f f8 80'),bytes.fromhex('5c 00 f7 4a'))
 guard=Program();guard.emit('08 48 a5 7e c9 5d 00');guard.branch('d0','done');guard.emit('a9 c4 00 85 7e');guard.label('done');guard.emit('68 28');emit_address(guard,'5c',0x4af600)
 out[0x5df280:0x5df28b]=bytes.fromhex('8b da a2 00 6a 68 54 00 5d ab 6b')
 for address,code,hook in [(0x5df000,primary,0xecc1),(0x5df100,secondary,0xed19),(0x5df200,pal,0x2cf201),(0x5df300,root_hook(),0xf0e8),(0x5df400,lookup,0x2cf6e4),(0x5df500,guard.finish(),0xf073),(0x5df700,ordinary,0xf82b)]:
  if len(code)>256:raise ValueError('Hook exceeds page')
  out[address:address+len(code)]=code;out[hook:hook+4]=b'\x5c'+address.to_bytes(3,'little')
 out[0x5def00:0x5def0f]=b'BOSSMAN15-PROBE'
 checksum(out);out[0x400000:0x410000]=out[:65536]
 assert out[0x708000:0x708000+14*45]==base[0x708000:0x708000+14*45]
 return out,{'base_sha256':hashlib.sha256(base).hexdigest(),'source_chr_sha256':hashlib.sha256(Path(chr_path).read_bytes()).hexdigest(),'source_tab_sha256':hashlib.sha256(Path(tab_path).read_bytes()).hexdigest(),'development_only':True,'slot':14,'selector':28,'poses':reports,'private_tiles':len(tiles),'packet_end':packet,'finisher_implemented':False,'editor_compatible':False,'existing_14_profiles_preserved':True,'warning':'Immutable native test only; gear reservations must be relocated/coordinated before editor integration.'}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('base','stock','chr','tab','portrait','cram'):p.add_argument(name,type=Path)
 p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 out,report=build(a.base.read_bytes(),a.stock.read_bytes(),a.chr,a.tab,Image.open(a.portrait),a.cram.read_bytes());a.output.write_bytes(out);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
