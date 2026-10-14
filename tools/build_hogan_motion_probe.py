"""Development-only Hogan basic-motion adapter; no finisher/editor support yet.

Uses native Raw timing and geometry candidate maps for the traced basic actions.
Unmapped actions deliberately retain the standing probe, and are reported as gaps.
"""
import argparse,json
from pathlib import Path
from PIL import Image
from build_hogan_slot_probe import build,lookup_hook
from build_shawn_kick_prototype import Program
from build_nwo_gear import emit_address,checksum
from build_bret_gear import planar
from decode_sprite_tile import encode_sprite_tile
from genesis_royal_sprites import render_pose
from genesis_royal_graphics import color_lookup

# Verified controller trace roots; shared Bret geometry establishes source poses.
ROOTS={0x4596:0,0x45b2:1,0x45c0:2,0x45ce:3,
       0x45dc:4,0x45ea:5,0x45f8:6,
       0x48d2:66,0x48e0:67,0x48ee:68,
       0x49e2:99,0x49f0:100,0x49fe:101,0x4a0c:102,
       0x4a36:106,0x4a44:107,0x4a52:108,0x4a60:109,
       0x4606:7,0x4614:8,0x4622:9,0x4630:10,0x463e:11}


def pack_objects(image):
    l,t,r,b=image.getbbox();options=[]
    # Source pixels stay exact. Choose 16px blocks or isolated 8px tiles to fit
    # the native 17-object/64-tile budget, reserving two objects for the shadow.
    for ox in range(l-15,l+1):
        for oy in range(t-15,t+1):
            chunks=[]
            for y in range(oy,b,16):
                for x in range(ox,r,16):
                    cells=[(x+tx,y+ty)for ty in (0,8)for tx in (0,8)
                           if image.crop((x+tx,y+ty,x+tx+8,y+ty+8)).getbbox()]
                    if len(cells)>1:chunks.append((x,y,16))
                    elif cells:chunks.append((*cells[0],8))
            if len(chunks)<=15 and sum((s//8)**2 for x,y,s in chunks)<=62:
                options.append(chunks)
    if not options:raise ValueError('Pose exceeds native object/tile budget')
    return sorted(min(options,key=lambda c:(len(c),sum(s*s for x,y,s in c))),key=lambda c:-c[2])


def descriptor_hook():
    p=Program();p.emit('08 48 da a6 36 bd 74 0b c9 1a 00');p.branch('d0','old')
    p.emit('bd 26 05 c9 04 00');p.branch('b0','old')
    p.emit('a3 03 c9 70 17');p.branch('90','old')
    p.emit('c9 '+(6000+len(ROOTS)*3).to_bytes(2,'little').hex(' '));p.branch('b0','old')
    p.emit('38 e9 70 17 aa');emit_address(p,'bf',0x4ab000);p.emit('85 80')
    emit_address(p,'bf',0x4ab002);p.emit('29 ff 00 85 82 fa 68 28')
    p.emit('a5 80 99 4e 05 a5 82 99 50 05 c8 c8 5c e2 ec 80')
    p.label('old');p.emit('fa 68 28');emit_address(p,'5c',0x70f000)
    return p.finish()


def root_hook():
    p=Program();p.emit('85 7c 86 7e 08 48 da a6 36 bd 74 0b c9 1a 00');p.branch('d0','done')
    p.emit('bd 26 05 c9 04 00');p.branch('b0','done')
    p.emit('a3 01 c9 c8 00');p.branch('d0','done')
    p.emit('a2 00 00');p.label('next');p.emit('a3 03');emit_address(p,'df',0x4a7000)
    p.branch('f0','found');p.emit('e8 e8 e8 e8 e0 '+(len(ROOTS)*4).to_bytes(2,'little').hex(' '))
    p.branch('90','next');p.emit('a9 00 c0');p.branch('80','set')
    p.label('found');emit_address(p,'bf',0x4a7002)
    p.label('set');p.emit('85 7c a9 4a 00 85 7e')
    p.label('done');p.emit('fa 68 28 5c ec f0 80');return p.finish()


def compile_motion(out,genesis):
    out=bytearray(out);tiles={};packet=0x550000;desc=0x540000;reports=[]
    from decode_graphics import decode_block
    hud_pointer=int.from_bytes(out[0x19ee4c:0x19ee4e],'little')|out[0x19ee49]<<16
    _,hud=decode_block(out,hud_pointer)
    if hud_pointer!=0x558000 or hud_pointer+hud['compressed_size']>0x55b000:
        raise ValueError('HUD atlas exceeds the protected graphics gap')
    out[0x540000:0x550000]=b'\xff'*65536
    out[0x550000:0x558000]=b'\xff'*32768
    out[0x55b000:0x560000]=b'\xff'*20480
    for i,(root,pose)in enumerate(ROOTS.items()):
        image,_=render_pose(genesis,6,pose,color_lookup(genesis));chunks=pack_objects(image)
        record=bytearray([len(chunks),sum(s==16 for x,y,s in chunks)])
        for x,y,s in chunks:
            dx=x-96;dy=y-128-1
            if not -64<=dx<64 or not -105<=dy<23:raise ValueError('Pose anchor unrepresentable')
            record+=bytes([0,dx&127,(dy+105)&127])
            for ty in range(s//8):
                for tx in range(s//8):
                    pixels=[image.getpixel((x+tx*8+px,y+ty*8+py))for py in range(8)for px in range(8)]
                    raw=planar(pixels)
                    if raw not in tiles:
                        tiles[raw]=len(tiles);encoded=encode_sprite_tile(raw)
                        if packet<0x558000 and packet+len(encoded)>0x558000:packet=0x55b000
                        if packet+len(encoded)>0x560000:raise ValueError('Private packet pools exhausted')
                        at=0x548000+tiles[raw]*3
                        if at+3>0x550000:raise ValueError('Tile pointer table overflow')
                        out[at:at+3]=packet.to_bytes(3,'little');out[packet:packet+len(encoded)]=encoded;packet+=len(encoded)
                    record+=(0xc000|tiles[raw]).to_bytes(2,'little')
        if desc+len(record)>0x548000:raise ValueError('Descriptor pool overflow')
        out[desc:desc+len(record)]=record;at=0x4ab000+i*3;out[at:at+3]=desc.to_bytes(3,'little');desc+=len(record)
        profile=0x4ac000+i*10
        out[profile:profile+10]=(6000+i*3).to_bytes(2,'little')+bytes.fromhex('00 00 09 80 00 ff ff ff')
        at=0x4a7000+i*4;out[at:at+4]=root.to_bytes(2,'little')+(profile&65535).to_bytes(2,'little')
        reports.append(dict(raw_root=root,source_pose=pose,body_objects=len(chunks),body_tiles=sum((s//8)**2 for x,y,s in chunks)))
    # Secondary standard shadow is native index 3, rather than standing index 12.
    from build_hogan_slot_probe import worker_hook
    secondary=worker_hook(True).replace(bytes.fromhex('c9 24 00'),bytes.fromhex('c9 09 00')).replace(bytes.fromhex('ff 45'),bytes.fromhex('9b 45'))
    for at,code in ((0x4af000,descriptor_hook()),(0x4af100,secondary),(0x4af300,root_hook())):
        if len(code)>256:raise ValueError('Hook overflow')
        out[at:at+256]=b'\xff'*256;out[at:at+len(code)]=code
    code=lookup_hook().replace(bytes.fromhex('00 88 4a'),bytes.fromhex('00 80 54')).replace(bytes.fromhex('02 88 4a'),bytes.fromhex('02 80 54'))
    out[0x4af400:0x4af400+len(code)]=code
    checksum(out);out[0x400000:0x410000]=out[:65536]
    return out,dict(development_only=True,finisher_disabled=True,editor_compatible=False,
                    private_tiles=len(tiles),packet_end=packet,poses=reports,
                    fallback='Unmapped actions intentionally show standing art; not a release')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','genesis','stock','portrait'):p.add_argument(name,type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    genesis=a.genesis.read_bytes()
    probe,_=build(a.base.read_bytes(),genesis,a.stock.read_bytes(),Image.open(a.portrait))
    out,report=compile_motion(probe,genesis);a.output.write_bytes(out)
    a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
