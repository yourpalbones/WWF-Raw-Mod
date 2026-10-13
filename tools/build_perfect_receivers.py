"""Private paired-animation build for Raw workers with direct Royal counterparts.

Uses an independent receiving tile namespace. Raw-only and customized receiving
art still needs authoring; this is not an all-wrestler completed release.
"""
import argparse,json
from pathlib import Path
from PIL import Image
from royal_rumble_sprites import decode_tile
from inspect_rom import tile
from build_bret_gear import planar
from decode_sprite_tile import encode_sprite_tile
from build_nwo_gear import checksum,emit_address
from build_shawn_kick_prototype import Program

RAW_ROYAL={1:3,2:2,3:9,5:8,6:10,8:7,12:1}


def worker_hook():
    p=Program();p.emit('08 48 da 5a a6 36 bd ec 0b c9 51 50');p.branch('f0','receiver')
    p.emit('c9 52 50');p.branch('d0','original')
    p.label('receiver');p.emit('bd 74 0b c9 1a 00');p.branch('b0','original')
    p.emit('85 90 4a 18 65 90 aa');emit_address(p,'bf',0x71d000);p.branch('f0','original')
    p.emit('85 84 a9 71 00 85 86 a3 05 c9 10 0e');p.branch('90','original')
    p.emit('c9 34 0e');p.branch('b0','original')
    p.emit('38 e9 10 0e a8 b7 84 85 80 c8 c8 b7 84 29 ff 00 85 82')
    p.emit('7a fa 68 28 a5 80 99 4e 05 a5 82 99 50 05 c8 c8 5c e2 ec 80')
    p.label('original');p.emit('7a fa 68 28');emit_address(p,'5c',0x71e800)
    return p.finish()


def lookup_hook():
    p=Program();p.emit('48 a5 82 29 ff 00 c9 6d 00');p.branch('d0','original')
    p.emit('68 c9 00 c0');p.branch('90','stock')
    p.emit('29 ff 3f da 48 0a 18 63 01 aa 68')
    emit_address(p,'bf',0x5e0000);p.emit('85 db e2 20');emit_address(p,'bf',0x5e0002)
    p.emit('85 dd c2 20 fa a9 01 00 6b')
    p.label('original');p.emit('68')
    p.label('stock');emit_address(p,'5c',0x71e900)
    return p.finish()


def sequence_hook():
    p=Program();p.emit('08 48 da a6 36 bd ec 0b c9 51 50');p.branch('f0','receiver')
    p.emit('c9 52 50');p.branch('d0','original')
    p.label('receiver');p.emit('bd b4 06 c9 1c 02');p.branch('d0','original')
    p.emit('bd 74 0b c9 1a 00');p.branch('b0','original')
    p.emit('85 90 4a 18 65 90 aa');emit_address(p,'bf',0x71d040);p.branch('f0','original')
    p.emit('85 92 a6 36 a5 48 c9 3f 00');p.branch('90','ready')
    p.emit('bd ec 0b c9 51 50');p.branch('d0','ready')
    p.emit('a9 01 00 9d d8 0a a9 52 50 9d ec 0b')
    p.label('ready');p.emit('fa 68 28 a9 71 00 85 7e a5 48 18 65 92 85 7c 5c 80 f0 80')
    p.label('original');p.emit('fa 68 28');emit_address(p,'5c',0x71ea00)
    return p.finish()


def build(base,royal,recipes):
    out=bytearray(base)
    for start,end in((0x5d0000,0x5f0000),(0x6d0000,0x6e0000),(0x71d000,0x720000)):
        if any(v!=255 for v in out[start:end]):raise ValueError(f'Receiving allocation occupied at {start:06x}')
    out[0x71d000:0x71d027]=bytes(39);out[0x71d040:0x71d067]=bytes(39)
    palette_base=0x700000+int.from_bytes(base[0x2cf212:0x2cf214],'little')
    word=lambda data,at:int.from_bytes(data[at:at+2],'little')
    rgb=lambda color:[color>>s&31 for s in(0,5,10)]
    pools=[(0x5d0000,0x5e0000),(0x5ec000,0x5f0000),(0x6d8000,0x6e0000)]
    pool=0;packet=pools[0][0];descriptor=0x6d0000;count=0;cache={};report=[]
    for slot,selector in RAW_ROYAL.items():
        worker=recipes['workers'][selector];private={}
        colors=[word(royal,0x17c26+selector*32+i*2)for i in range(16)]
        target=[word(base,palette_base+64+slot*32+i*2)for i in range(16)]
        mapping=[0]+[min(range(1,16),key=lambda j:sum((a-b)**2 for a,b in zip(rgb(c),rgb(target[j]))))for c in colors[1:]]
        table=0x71d100+slot*36;profiles=0x71d400+slot*168;sequence=0x71e000+slot*141
        out[0x71d000+slot*3:0x71d003+slot*3]=table.to_bytes(3,'little')
        out[0x71d040+slot*3:0x71d043+slot*3]=sequence.to_bytes(3,'little')
        for i,row in enumerate(worker['poses']):
            image=Image.new('P',(144,144))
            for part in reversed(row['parts']):
                size=part['size']
                for y in range(size):
                    for x in range(size):
                        sx=size-1-x if part['hflip']else x;sy=size-1-y if part['vflip']else y
                        ref=part['refs'][(sy//8)*(size//8)+sx//8];key=tuple(ref)
                        if key not in cache:cache[key]=tile(decode_tile(royal,ref[0],bool(ref[1]))[0],0,4)
                        value=cache[key][sy%8*8+sx%8]
                        if value:image.putpixel((part['x']+x+73,part['y']+y+105),mapping[value])
            chunks=row['chunks'];record=bytearray([len(chunks),sum(c[2]==16 for c in chunks)])
            for x,y,size in chunks:
                record+=bytes([0,x&127,(y+105)&127])
                for ty in range(size//8):
                    for tx in range(size//8):
                        pixels=[image.getpixel((x+64+tx*8+xx,y+105+ty*8+yy))for yy in range(8)for xx in range(8)]
                        raw=planar(pixels)
                        if raw not in private:
                            encoded=encode_sprite_tile(raw)
                            if packet+len(encoded)>pools[pool][1]:
                                pool+=1
                                if pool>=len(pools):raise ValueError('Receiving packet space exhausted')
                                packet=pools[pool][0]
                            if count>=16384:raise ValueError('Receiving tile namespace exhausted')
                            private[raw]=count;out[packet:packet+len(encoded)]=encoded
                            out[0x5e0000+count*3:0x5e0003+count*3]=packet.to_bytes(3,'little')
                            packet+=len(encoded);count+=1
                        record+=(0xc000|private[raw]).to_bytes(2,'little')
            if descriptor+len(record)>0x6d8000:raise ValueError('Receiving descriptor space exhausted')
            out[descriptor:descriptor+len(record)]=record;out[table+i*3:table+i*3+3]=descriptor.to_bytes(3,'little');descriptor+=len(record)
            profile=profiles+i*14
            out[profile:profile+10]=((1200+i)*3).to_bytes(2,'little')+bytes([32,0,36,128,0,255,255,255])
        for i in range(20):
            profile=profiles+min(i,11)*14
            out[sequence+i*7:sequence+i*7+7]=bytes([113])+(profile&65535).to_bytes(2,'little')+bytes(4)
        out[sequence+140]=255
        report.append({'raw_slot':slot,'royal_selector':selector,'receiving_drawings':12,'private_tiles':len(private)})
    # Existing dispatcher code stays intact and remains the fallback for all actors.
    for original,copy in((0x70f000,0x71e800),(0x70f200,0x71e900),(0x70f400,0x71ea00)):
        out[copy:copy+256]=base[original:original+256]
    for original,address,code in((0x70f000,0x71eb00,worker_hook()),(0x70f200,0x71ec00,lookup_hook()),(0x70f400,0x71ed00,sequence_hook())):
        if len(code)>256:raise ValueError('Receiving hook exceeds its allocation')
        out[address:address+len(code)]=code;out[original:original+4]=b'\x5c'+address.to_bytes(3,'little')
    out[0x70fe40:0x70fe49]=b'ROYAL-RX1'
    checksum(out)
    return out,{'receivers':report,'tile_namespace_count':count,'descriptor_end':descriptor,'last_packet':packet,'raw_only_receiving_art_complete':False,'custom_gear_receiving_art_complete':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path);parser.add_argument('royal',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    result,report=build(args.raw.read_bytes(),args.royal.read_bytes(),json.loads((root/'data/perfect-receivers.json').read_text()))
    args.output.write_bytes(result);args.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
