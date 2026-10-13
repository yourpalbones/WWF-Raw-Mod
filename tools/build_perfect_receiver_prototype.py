"""Private test build: actual Royal Undertaker receiving art in Raw's own slot.

This does not claim receiver coverage for the other Raw wrestlers. It is a
paired-placement test before the full receiver importer and editor integration.
"""
import argparse,json
from pathlib import Path
from PIL import Image
from royal_rumble_sprites import decode_tile
from inspect_rom import tile
from build_bret_gear import planar
from decode_sprite_tile import encode_sprite_tile
from build_nwo_gear import checksum,emit_address
from build_perfect_slot import hook_worker
from build_shawn_kick_prototype import Program

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('raw',type=Path);parser.add_argument('royal',type=Path)
parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
out=bytearray(args.raw.read_bytes());source=args.royal.read_bytes()
rows=json.loads((root/'data/perfect-receivers.json').read_text())['workers'][2]['poses']
palette=lambda data,at:[int.from_bytes(data[at+i*2:at+i*2+2],'little')for i in range(16)]
colors=palette(source,0x17c66);palette_at=0x700000+int.from_bytes(out[0x2cf212:0x2cf214],'little')+128
target=palette(out,palette_at)
rgb=lambda c:[c>>s&31 for s in(0,5,10)]
mapping=[0]+[min(range(1,16),key=lambda j:sum((a-b)**2 for a,b in zip(rgb(c),rgb(target[j]))))for c in colors[1:]]
packet=0x712000;descriptor=0x736000
count=next(i for i in range(16384)if out[0x7d0000+i*3:0x7d0003+i*3]==b'\xff'*3)
cache={};tiles={}
for i,row in enumerate(rows):
    image=Image.new('P',(144,144))
    for part in reversed(row['parts']):
        size=part['size']
        for y in range(size):
            for x in range(size):
                sx=size-1-x if part['hflip']else x;sy=size-1-y if part['vflip']else y
                ref=part['refs'][(sy//8)*(size//8)+sx//8];key=tuple(ref)
                if key not in cache:cache[key]=tile(decode_tile(source,ref[0],bool(ref[1]))[0],0,4)
                value=cache[key][sy%8*8+sx%8]
                if value:image.putpixel((part['x']+x+73,part['y']+y+105),mapping[value])
    chunks=row['chunks'];record=bytearray([len(chunks),sum(c[2]==16 for c in chunks)])
    for x,y,size in chunks:
        record+=bytes([0,x&127,(y+105)&127])
        for ty in range(size//8):
            for tx in range(size//8):
                pixels=[image.getpixel((x+64+tx*8+xx,y+105+ty*8+yy))for yy in range(8)for xx in range(8)]
                raw=planar(pixels)
                if raw not in tiles:
                    encoded=encode_sprite_tile(raw)
                    if count>=16384 or packet+len(encoded)>0x71c000:raise ValueError('Receiver staging space exhausted')
                    if any(v!=255 for v in out[packet:packet+len(encoded)]):raise ValueError('Receiver staging area occupied')
                    tiles[raw]=count;out[packet:packet+len(encoded)]=encoded
                    out[0x7d0000+count*3:0x7d0003+count*3]=packet.to_bytes(3,'little');packet+=len(encoded);count+=1
                record+=(0xc000|tiles[raw]).to_bytes(2,'little')
    if descriptor+len(record)>0x738000:raise ValueError('Receiver descriptor space exhausted')
    out[descriptor:descriptor+len(record)]=record
    out[0x710000+(1200+i)*3:0x710003+(1200+i)*3]=descriptor.to_bytes(3,'little');descriptor+=len(record)
for i in range(20):
    profile=0x735100+i*32
    out[profile:profile+32]=b'\xff'*32
    out[profile:profile+10]=((1200+min(i,11))*3).to_bytes(2,'little')+bytes([32,0,36,128,0,255,255,255])

# Intercept only Undertaker receiving this move; every other actor chains intact.
old=hook_worker(False,True).replace(bytes.fromhex('c9 b2 0b'),bytes.fromhex('c9 dc 0b'))
out[0x70ed00:0x70ed00+len(old)]=old
p=Program();p.emit('08 48 da a6 36 bd 74 0b c9 04 00');p.branch('d0','original')
p.emit('bd ec 0b c9 51 50');p.branch('f0','receiver');p.emit('c9 52 50');p.branch('d0','original')
p.label('receiver');p.emit('fa 68 c9 10 0e');p.branch('90','restore');p.emit('c9 34 0e');p.branch('b0','restore')
p.emit('48 da aa');emit_address(p,'bf',0x710000);p.emit('85 80');emit_address(p,'bf',0x710002)
p.emit('29 ff 00 85 82 fa 68 28 a5 80 99 4e 05 a5 82 99 50 05 c8 c8 5c e2 ec 80')
p.label('restore');p.emit('28');emit_address(p,'5c',0x70ed00)
p.label('original');p.emit('fa 68 28');emit_address(p,'5c',0x70ed00)
code=p.finish();out[0x70eb00:0x70eb00+len(code)]=code
out[0x70f000:0x70f004]=b'\x5c'+(0x70eb00).to_bytes(3,'little')
checksum(out);args.output.write_bytes(out)
print('Staged twelve actual Undertaker receiving drawings;',len(tiles),'private tiles;',packet-0x712000,'packet bytes')
