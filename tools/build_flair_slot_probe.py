"""Private slot-16 Flair preview layered over Hogan/Boss Man; requires editor-v01.

The builder reserves physical banks 34/35/3B and refuses occupied banks.
Use the protected editor-v01 exporter; legacy gear rebuilds overlap these assets.
"""
import argparse,json,hashlib
from pathlib import Path
from PIL import Image
import flair_royal_source as source
import royal_rumble_sprites as royal
import build_hogan_motion_probe as motion
from build_hogan_slot_probe import worker_hook,lookup_hook,palette_hook,ordinary_move_hook
from build_shawn_kick_prototype import Program
from build_nwo_gear import emit_address,checksum
from build_bret_gear import planar
from decode_sprite_tile import encode_sprite_tile
from hogan_profile_probe_assets import configure

ROOTS={0x4596:0,0x45b2:1,0x45c0:2,0x45ce:3,0x45dc:4,0x45ea:5,0x45f8:6,
       0x48d2:65,0x48e0:66,0x48ee:67,
       0x49e2:89,0x49f0:90,0x49fe:91,0x4a0c:92,
       0x4a36:96,0x4a44:97,0x4a52:98,0x4a60:99,
       0x4606:7,0x4614:8,0x4622:9,0x4630:10,0x463e:11,
       0x4692:0,0x46ae:18,0x46bc:19,0x46ca:20,0x46d8:21,0x46e6:22,0x46f4:23,
       0x4702:24,0x4710:25,0x471e:26,0x472c:27,0x473a:28}

def rom_offset(address):return address&0x3fffff if address>>16>=0xc0 else address

def root_hook():
 p=Program();p.emit('85 7c 86 7e 08 48 da a6 36 bd 74 0b c9 1e 00');p.branch('d0','old')
 p.emit('bd 26 05 c9 04 00');p.branch('b0','old');p.emit('a3 01 c9 c8 00');p.branch('d0','old')
 p.emit('a2 00 00');p.label('next');p.emit('a3 03');emit_address(p,'df',0xf47000);p.branch('f0','found')
 p.emit('e8 e8 e8 e8 e0 '+(len(ROOTS)*4).to_bytes(2,'little').hex(' '));p.branch('90','next');p.emit('a9 00 c0');p.branch('80','set')
 p.label('found');emit_address(p,'bf',0xf47002);p.label('set');p.emit('85 7c a9 f4 00 85 7e fa 68 28 5c ec f0 80')
 p.label('old');p.emit('fa 68 28');emit_address(p,'5c',0x5df300);return p.finish()

def build(base,stock,chr_path,tab_path,portrait,cram):
 if len(base)!=0x800000 or base[0x19d43f]!=15 or base[0x5def00:0x5def0e]!=b'BOSSMAN15-PROB':raise ValueError('Requires the slot-15 Hogan/Boss Man prototype')
 for bank in (0xf4,0xf5,0xfb):
  if base[rom_offset(bank*65536):rom_offset(bank*65536)+65536]!=b'\xff'*65536:raise ValueError(f'Bank {bank:02x} occupied')
 out=bytearray(base);royal_rom=Path(chr_path).read_bytes();royal_wram=Path(tab_path).read_bytes()
 frames=royal.catalog(royal_rom,royal_wram,6)
 # All original profile access was relocated by the thirteen-slot importer.
 # Reclaim one obsolete legacy record solely for slot-16 bio strings.
 out[rom_offset(0x2efaf5):rom_offset(0x2efb22)]=b'\xff'*45
 record=0x708000+15*45
 if out[rom_offset(record):rom_offset(record+45)]!=b'\xff'*45:raise ValueError('Slot 16 profile occupied')
 out[rom_offset(record):rom_offset(record+45)]=base[0x708000+14*45:0x708000+15*45]
 configure(out,stock,portrait,slot=15,asset_bank=0x34,hud_bank=0x3b,name='RIC FLAIR',hometown='CHARLOTTE',height='6\'1"',weight='243',special='FIGURE FOUR',previous_rows=base[0x5d9000:0x5d9000+15*8],text_region=(0x2efaf5,0x2efb22))
 out[rom_offset(0x346a00):rom_offset(0x346a20)]=royal_rom[0x17ce6:0x17d06]
 tiles={};packet=0xfb0000;desc=0xf50000;reports=[]
 for i,(root,pose)in enumerate(ROOTS.items()):
  image=source.render_pose(royal_rom,frames,pose);chunks=motion.pack_objects(image);drawing=bytearray([len(chunks),sum(s==16 for x,y,s in chunks)])
  for x,y,s in chunks:
   dx=x-96;dy=y-129
   if not -64<=dx<64 or not -105<=dy<23:raise ValueError('Unrepresentable pose anchor')
   drawing+=bytes([0,dx&127,(dy+105)&127])
   for ty in range(s//8):
    for tx in range(s//8):
     raw=planar([image.getpixel((x+tx*8+px,y+ty*8+py))for py in range(8)for px in range(8)])
     if raw not in tiles:
      ident=len(tiles);encoded=encode_sprite_tile(raw)
      if packet<0xfb8000 and packet+len(encoded)>0xfb8000:packet=0xfbb000
      if packet+len(encoded)>0xfc0000:raise ValueError('Tile pool exhausted')
      at=0xf58000+ident*3
      if at+3>0xf60000:raise ValueError('Tile directory exhausted')
      out[rom_offset(at):rom_offset(at+3)]=packet.to_bytes(3,'little');out[rom_offset(packet):rom_offset(packet+len(encoded))]=encoded;packet+=len(encoded);tiles[raw]=ident
     drawing+=(0xc000|tiles[raw]).to_bytes(2,'little')
  if desc+len(drawing)>0xf58000:raise ValueError('Descriptor pool exhausted')
  out[rom_offset(desc):rom_offset(desc+len(drawing))]=drawing;at=0xf4b000+i*3;out[rom_offset(at):rom_offset(at+3)]=desc.to_bytes(3,'little');desc+=len(drawing)
  profile=0xf4c000+i*10;out[rom_offset(profile):rom_offset(profile+10)]=(6000+i*3).to_bytes(2,'little')+bytes.fromhex('00 00 09 80 00 ff ff ff')
  at=0xf47000+i*4;out[rom_offset(at):rom_offset(at+4)]=root.to_bytes(2,'little')+(profile&65535).to_bytes(2,'little')
  reports.append({'raw_root':root,'source_pose':pose,'objects':len(chunks),'tiles':sum((s//8)**2 for x,y,s in chunks)})
 # Extend menu/stat capacity without changing existing 14 records.
 out[rom_offset(0x19d43f)]=16
 at=out.find(bytes.fromhex('a9 0e 00'),0x19d420,0x19d440)
 if at<0:raise ValueError('Unsupported menu wrap')
 out[rom_offset(at+1)]=15
 at=out.find(bytes.fromhex('c0 1e 00'),0x4afa00,0x4afb00)
 if at<0:raise ValueError('Unsupported relocated initializer')
 out[rom_offset(at+1)]=32
 tail=out.find(bytes.fromhex('a9 f8 ff 99 00 e0'),0x4afa00,0x4afb00)
 if tail<0:raise ValueError('Unsupported legacy stat tail')
 out[rom_offset(tail):rom_offset(tail+24)]=bytes.fromhex('ab 6b')+b'\xea'*22
 for n in range(6):out[rom_offset(0x708600+n*32+30):rom_offset(0x708600+n*32+32)]=b'\xff\xff'
 for at in (0x4a8b00,0x4a8b40):out[rom_offset(at+30):rom_offset(at+32)]=base[at+28:at+30]
 out[rom_offset(0xf48c60):rom_offset(0xf48c6a)]=b''.join(v.to_bytes(2,'little')for v in (234,242,174,190,226))
 # Existing hook code remains in place and receives all non-Boss actors.
 old=motion.ROOTS.copy()
 try:
  motion.ROOTS.clear();motion.ROOTS.update(ROOTS);primary=motion.descriptor_hook()
 finally:motion.ROOTS.clear();motion.ROOTS.update(old)
 primary=primary.replace(bytes.fromhex('c9 1a 00'),bytes.fromhex('c9 1e 00')).replace(bytes.fromhex('00 b0 4a'),bytes.fromhex('00 b0 f4')).replace(bytes.fromhex('02 b0 4a'),bytes.fromhex('02 b0 f4')).replace(bytes.fromhex('5c 00 f0 70'),bytes.fromhex('5c 00 f0 5d'))
 secondary=worker_hook(True).replace(bytes.fromhex('c9 1a 00'),bytes.fromhex('c9 1e 00')).replace(bytes.fromhex('c9 24 00'),bytes.fromhex('c9 09 00')).replace(bytes.fromhex('ff 45'),bytes.fromhex('9b 45')).replace(bytes.fromhex('5c 00 f1 70'),bytes.fromhex('5c 00 f1 5d'))
 pal=palette_hook().replace(bytes.fromhex('c9 1a 00'),bytes.fromhex('c9 1e 00')).replace(bytes.fromhex('80 f2 4a'),bytes.fromhex('80 f2 f4')).replace(bytes.fromhex('00 f8 4a'),bytes.fromhex('00 f2 5d'))
 lookup=lookup_hook().replace(bytes.fromhex('c9 54 00'),bytes.fromhex('c9 f5 00')).replace(bytes.fromhex('00 88 4a'),bytes.fromhex('00 80 f5')).replace(bytes.fromhex('02 88 4a'),bytes.fromhex('02 80 f5')).replace(bytes.fromhex('5c 00 f2 70'),bytes.fromhex('5c 00 f4 5d'))
 ordinary=ordinary_move_hook().replace(bytes.fromhex('c9 1a 00'),bytes.fromhex('c9 1e 00')).replace(bytes.fromhex('a9 4a 00'),bytes.fromhex('a9 f4 00')).replace(bytes.fromhex('bf 59 d8 ad 5c 2f f8 80'),bytes.fromhex('5c 00 f7 5d'))
 guard=Program();guard.emit('08 48 a5 7e c9 f4 00');guard.branch('d0','done');guard.emit('a9 c4 00 85 7e');guard.label('done');guard.emit('68 28');emit_address(guard,'5c',0x5df500)
 out[rom_offset(0xf4f280):rom_offset(0xf4f28b)]=bytes.fromhex('8b da a2 00 6a 68 54 00 f4 ab 6b')
 for address,code,hook in [(0xf4f000,primary,0xecc1),(0xf4f100,secondary,0xed19),(0xf4f200,pal,0x2cf201),(0xf4f300,root_hook(),0xf0e8),(0xf4f400,lookup,0x2cf6e4),(0xf4f500,guard.finish(),0xf073),(0xf4f700,ordinary,0xf82b)]:
  if len(code)>256:raise ValueError('Hook exceeds page')
  out[rom_offset(address):rom_offset(address+len(code))]=code;out[rom_offset(hook):rom_offset(hook+4)]=b'\x5c'+address.to_bytes(3,'little')
 out[rom_offset(0xf4ef00):rom_offset(0xf4ef0f)]=b'FLAIR16-PROBE1'.ljust(15,b'\0')
 checksum(out);out[rom_offset(0x400000):rom_offset(0x410000)]=out[0:rom_offset(65536)]
 assert out[rom_offset(0x708000):rom_offset(0x708000+15*45)]==base[0x708000:0x708000+15*45]
 return out,{'base_sha256':hashlib.sha256(base).hexdigest(),'source_chr_sha256':hashlib.sha256(Path(chr_path).read_bytes()).hexdigest(),'source_tab_sha256':hashlib.sha256(Path(tab_path).read_bytes()).hexdigest(),'development_only':True,'slot':15,'selector':30,'poses':reports,'private_tiles':len(tiles),'packet_end':packet,'finisher_implemented':False,'requires_roster16_editor':True,'existing_15_profiles_preserved':True,'warning':'Use editor-v01 for protected editing; full move coverage and Figure Four remain unfinished.'}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('base','stock','chr','tab','portrait','cram'):p.add_argument(name,type=Path)
 p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 out,report=build(a.base.read_bytes(),a.stock.read_bytes(),a.chr,a.tab,Image.open(a.portrait),a.cram.read_bytes());a.output.write_bytes(out);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
