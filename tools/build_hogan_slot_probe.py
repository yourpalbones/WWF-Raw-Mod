"""Private fourteenth-slot bookkeeping/art probe. NOT a completed Hogan import.

Uses real converted Hogan standing art, but deliberately displays that one pose
for all actions. This isolates roster/NPC/palette/table expansion before motion
mapping. No editor upgrade or playable-release claim is made by this tool.
"""
import argparse,json,hashlib
from pathlib import Path
from PIL import Image
from genesis_royal_sprites import render_pose
from genesis_royal_graphics import color_lookup,snes_palette,SOURCE_SHA256
from build_bret_gear import planar
from decode_sprite_tile import encode_sprite_tile
from build_nwo_gear import checksum,emit_address
from build_shawn_kick_prototype import Program
from hogan_profile_probe_assets import configure


def worker_hook(secondary=False):
    p=Program();p.emit('08 48 da a6 36 bd 74 0b c9 1a 00');p.branch('d0','old')
    p.emit('bd 26 05 c9 04 00');p.branch('b0','old')
    p.emit('a3 03 c9 '+('24 00'if secondary else'70 17'));p.branch('d0','old')
    p.emit('fa 68 28')
    descriptor=0xda45ff if secondary else 0x54d000
    p.emit('a9 '+(descriptor&65535).to_bytes(2,'little').hex(' ')+' 85 80 a9 '+(descriptor>>16).to_bytes(2,'little').hex(' ')+' 85 82')
    p.emit('a5 80 99 50 05 a5 82 99 52 05 5c 38 ed 80'if secondary else'a5 80 99 4e 05 a5 82 99 50 05 c8 c8 5c e2 ec 80')
    p.label('old');p.emit('fa 68 28');emit_address(p,'5c',0x70f100 if secondary else 0x70f000)
    return p.finish()


def palette_hook():
    p=Program();p.emit('08 48 da 29 ff 07 c9 1a 00');p.branch('d0','old')
    p.emit('98 c9 20 16');p.branch('90','old');p.emit('c9 e0 16');p.branch('b0','old')
    p.emit('38 e9 20 16 4a 4a 4a 4a aa bd 26 05 c9 04 00');p.branch('b0','old')
    p.emit('fa 68 28 a9 22 00');emit_address(p,'5c',0x4af800)
    p.label('old');p.emit('fa 68 28');emit_address(p,'5c',0x4af800)
    return p.finish()


def profile_hook():
    p=Program();p.emit('85 7c 86 7e 08 48 da a6 36 bd 74 0b c9 1a 00');p.branch('d0','done')
    p.emit('bd 26 05 c9 04 00');p.branch('b0','done')
    p.emit('a3 01 c9 c8 00');p.branch('d0','done')
    p.emit('a9 00 c0 85 7c a9 4a 00 85 7e')
    p.label('done');p.emit('fa 68 28 5c ec f0 80')
    return p.finish()


def lookup_hook():
    p=Program();p.emit('48 a5 82 29 ff 00 c9 54 00');p.branch('d0','old')
    p.emit('68 c9 00 c0');p.branch('90','stock')
    p.emit('29 ff 3f da 48 0a 18 63 01 aa 68');emit_address(p,'bf',0x4a8800)
    p.emit('85 db e2 20');emit_address(p,'bf',0x4a8802)
    p.emit('85 dd c2 20 fa a9 01 00 6b')
    p.label('old');p.emit('68');p.label('stock');emit_address(p,'5c',0x70f200)
    return p.finish()


def sequence_bank_guard():
    # A private profile's bank must not leak into the next native sequence lookup.
    p=Program();p.emit('08 48 a5 7e c9 4a 00');p.branch('d0','done')
    p.emit('a9 c4 00 85 7e');p.label('done');p.emit('68 28')
    emit_address(p,'5c',0x70f400)
    return p.finish()


def build(base,genesis,stock,portrait):
    if hashlib.sha256(genesis).hexdigest()!=SOURCE_SHA256:
        raise ValueError("Unsupported Genesis source revision; verify directories before importing")
    if base[0x70ea60:0x70ea80]!=b"\xff"*32:
        raise ValueError("Hogan palette allocation is occupied")
    if len(base)!=0x800000 or base[0x70fe40:0x70fe49]!=b'ROYAL-RX2':
        raise ValueError('Requires Claude corrected thirteen-slot export, not an older mod')
    for a in (0x4a0000,0x540000,0x550000):
        if base[a:a+65536]!=b'\xff'*65536:raise ValueError(f'Probe bank occupied: {a:06x}')
    out=bytearray(base);image,_=render_pose(genesis,6,0,color_lookup(genesis))
    if base[0x1a45ff:0x1a4601]!=b'\x04\x00':raise ValueError('Unsupported stock shadow descriptor')
    # A complete 16x16 grid covering the cropped source picture preserves pixels.
    l,t,r,b=image.getbbox();l=l//8*8;t=t//8*8
    chunks=[]
    for y in range(t,b,16):
        for x in range(l,r,16):
            crop=image.crop((x,y,x+16,y+16))
            if crop.getbbox():chunks.append((x,y))
    if len(chunks)+4>17 or len(chunks)*4+4>64:raise ValueError('Standing plus shadow exceeds renderer budget')
    record=bytearray([len(chunks),len(chunks)]);cursor=0x550000;tiles={}
    for x,y in chunks:
        if not -64<=x-96<64 or not -105<=y-128<23:raise ValueError('Unrepresentable standing anchor')
        record+=bytes([0,(x-96)&127,(y-128+105)&127])
        for ty in range(2):
            for tx in range(2):
                pixels=[image.getpixel((x+tx*8+px,y+ty*8+py))for py in range(8)for px in range(8)]
                raw=planar(pixels)
                if raw not in tiles:
                    tiles[raw]=len(tiles);packet=encode_sprite_tile(raw)
                    at=0x4a8800+tiles[raw]*3;out[at:at+3]=cursor.to_bytes(3,'little')
                    out[cursor:cursor+len(packet)]=packet;cursor+=len(packet)
                record+=(0xc000|tiles[raw]).to_bytes(2,'little')
    out[0x54d000:0x54d000+len(record)]=record
    out[0x4ac000:0x4ac00a]=(6000).to_bytes(2,'little')+bytes.fromhex('00 00 24 80 00 ff ff ff')
    out[0x70ea60:0x70ea80]=snes_palette(genesis)
    start=0x708000+13*45
    if out[start:start+45]!=b'\xff'*45:raise ValueError('Fourteenth profile space occupied')
    out[start:start+45]=base[0x708000+6*45:0x708000+7*45]
    configure(out,stock,portrait)
    # $14xx is the palette cache, not free RAM. Probe stats use $7E:E000 with
    # explicit DB for the short-access routines and long-bank operands elsewhere.
    stats=[(0xe36,0xe000),(0xe50,0xe020),(0xe6a,0xe040),(0xe84,0xe060)]
    for old,new in stats:
        for opcode,region in ((0xbf,(0xd410,0xd43b)),(0xbf,(0x19f3f9,0x19f419))):
            pattern=bytes([opcode])+old.to_bytes(2,'little');at=region[0];found=0
            while True:
                at=base.find(pattern,at,region[1])
                if at<0:break
                out[at+1:at+4]=(0x7e0000+new).to_bytes(3,'little');found+=1;at+=4
            if not found:raise ValueError(f'Missing stat reference {old:04x}/{opcode:02x}')
    at=base.find(bytes.fromhex('c0 18 00'),0x2afebc,0x2aff20)
    if at<0:raise ValueError('Unknown initializer count')
    # Clone the constructor and attribute editor into an explicit WRAM DB scope.
    for begin,end,target,short in ((0x2afebb,0x2aff1d,0x4afa00,False),
                                   (0x19d27f,0x19d2c9,0x4afb00,True),
                                   (0x19d2c9,0x19d2f5,0x4afc00,True)):
        code=bytearray(base[begin:end])
        expected=bytes.fromhex('ad d6 05 0a aa')if short else bytes.fromhex('a2 00 00 a0 00 00')
        if not code.startswith(expected):raise ValueError('Unexpected stat entry instruction boundary')
        for old,new in stats:
            for opcode in (0xbd,0x9d,0x99):
                code=code.replace(bytes([opcode])+old.to_bytes(2,'little'),bytes([opcode])+new.to_bytes(2,'little'))
        if not short:code=code.replace(bytes.fromhex('c0 18 00'),bytes.fromhex('c0 1c 00'))
        if code[-1]not in(0x60,0x6b):raise ValueError('Unexpected stat routine boundary')
        code=bytes.fromhex('8b e2 20 a9 7e 48 ab c2 20')+code[:-1]+bytes.fromhex('ab 6b')
        out[target:target+len(code)]=code
        out[begin:begin+4]=bytes([0x22 if short else 0x5c])+target.to_bytes(3,'little')
        if short:out[begin+4]=0x60
    out[0x19d43f]=14
    back=base.find(bytes.fromhex('a9 0c 00'),0x19d420,0x19d440)
    if back<0:raise ValueError('Unknown selection wrap')
    out[back+1]=13
    for n in range(6):out[0x708600+n*32+26:0x708600+n*32+28]=b'\xff\xff'
    for old,new in ((0x2dd9d9,0x4a8b00),(0x2dd9f3,0x4a8b40)):
        out[new:new+26]=base[old:old+26];out[new+26:new+28]=base[old+12:old+14]
        needle=(old|0x800000).to_bytes(3,'little');at=0
        while True:
            at=base.find(needle,at,0x300000)
            if at<0:break
            if base[at-1]in(0xbf,0x7f,0xff):out[at:at+3]=new.to_bytes(3,'little')
            at+=3
    # Layer over existing dispatchers; NPC selector 26 is distinguished by role.
    out[0x4af800:0x4af81d]=base[0x2cf201:0x2cf21e]
    for address,code,hook in ((0x4af000,worker_hook(),0xecc1),(0x4af100,worker_hook(True),0xed19),
                              (0x4af200,palette_hook(),0x2cf201),(0x4af300,profile_hook(),0xf0e8),
                              (0x4af400,lookup_hook(),0x2cf6e4),(0x4af500,sequence_bank_guard(),0xf073)):
        if len(code)>256:raise ValueError('Probe hook overflow')
        out[address:address+len(code)]=code;out[hook:hook+4]=b'\x5c'+address.to_bytes(3,'little')
    out[0x4aef00:0x4aef0e]=b'HOGAN14-PROBE1'
    checksum(out);out[0x400000:0x410000]=out[:65536]
    return out,dict(development_only=True,slot=13,native_selector=26,source_worker=6,
                    standing_objects=len(chunks),private_tiles=len(tiles),packet_end=cursor,
                    animation_complete=False,finisher_disabled=True,editor_compatible=False,
                    warning='Standing artwork intentionally used for every action; bookkeeping probe only.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','genesis','stock','portrait'):p.add_argument(name,type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out,report=build(a.base.read_bytes(),a.genesis.read_bytes(),a.stock.read_bytes(),Image.open(a.portrait))
    a.output.write_bytes(out);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
