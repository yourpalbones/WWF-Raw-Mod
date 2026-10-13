"""Stage Royal Rumble's captured native Perfect-Plex in the private Raw slot.

Uses native OAM/VRAM pixels, not screenshots redrawn as replacement sprites.
Raw's existing suplex pair setup is retained while the attacker gets this new
sequence. Victim timing and automatic bridge/pin behavior require verification.
"""
import argparse
import json
from pathlib import Path
from PIL import Image
from inspect_rom import tile
from build_bret_gear import planar
from decode_sprite_tile import encode_sprite_tile
from build_nwo_gear import checksum,emit_address
from build_shawn_kick_prototype import Program
from build_shawn_superkick_animation import pack
from extract_oam import objects


def actor_pixels(prefix,palette):
    def read(name):return Path(str(prefix)+'-'+name+'.bin').read_bytes()
    vram,oam,cgram,regs=(read(n)for n in ['vram','oam','cgram','registers'])
    obsel=regs[0x2101];records=objects(vram,oam,cgram,obsel);result={}
    base=(obsel&3)<<14;name_select=((obsel>>3)&3)<<13
    for rec,_ in reversed(records):
        if rec['palette']!=palette:continue
        size=rec['size'];n=rec['tile']&255;attr=oam[rec['index']*4+3]
        for y in range(size):
            for x in range(size):
                sx=size-1-x if rec['hflip']else x;sy=size-1-y if rec['vflip']else y
                number=((n&0xf0)+(sy//8)*16+((n+sx//8)&15))&255
                address=(base+(name_select+8192 if attr&1 else 0)+number*32)&65535
                value=tile(vram,address,4)[(sy%8)*8+sx%8]
                if value:result[rec['x']+x,rec['y']+y]=value
    return result


def init_hook():
    p=Program();p.emit('22 dd ee ac 08 48 da a6 36 bd 74 0b c9 18 00')
    p.branch('d0','done');p.emit('a5 b9 c9 58 02');p.branch('d0','done')
    # Keep the paired grapple within Raw's native ring bounds before playback.
    p.emit('a6 56 bd f0 05 bc 00 06 22 e1 fd 83 38 fd f0 05 48 18 7d f0 05 9d f0 05 a6 36 68 18 7d f0 05 9d f0 05')
    p.emit('a9 50 50 9d ec 0b a6 56 a9 51 50 9d ec 0b')
    p.label('done');p.emit('fa 68 28 5c b4 ec ac');return p.finish()


def sequence_hook():
    p=Program();p.emit('08 48 da a6 36 bd ec 0b c9 51 50')
    p.branch('f0','victim');p.emit('c9 52 50');p.branch('f0','victim')
    p.emit('bd 74 0b c9 18 00');p.branch('d0','fallback')
    p.emit('bd ec 0b c9 50 50');p.branch('d0','fallback')
    p.emit('bd b4 06 c9 58 02');p.branch('f0','sequence')
    p.emit('9e ec 0b');p.branch('80','fallback')
    p.label('victim');p.emit('bd b4 06 c9 1c 02');p.branch('d0','clear')
    # Trigger Raw's own deferred damage calculation once at the landing.
    p.emit('a5 48 c9 3f 00');p.branch('90','victim_sequence')
    p.emit('bd ec 0b c9 51 50');p.branch('d0','victim_sequence')
    p.emit('a9 01 00 9d d8 0a a9 52 50 9d ec 0b')
    p.label('victim_sequence');p.emit('fa 68 28 a9 73 00 85 7e a5 48 18 69 00 50 85 7c 5c 80 f0 80')
    p.label('clear');p.emit('9e ec 0b');p.branch('80','fallback')
    p.label('sequence');p.emit('fa 68 28 a9 73 00 85 7e a5 48 85 7c 5c 80 f0 80')
    p.label('fallback');p.emit('fa 68 28 85 7c 48 a5 7e c9 73 00')
    p.branch('d0','bank_done');p.emit('a9 c4 00 85 7e')
    p.label('bank_done');p.emit('68 a7 7c 5c 77 f0 80')
    return p.finish()


def build(base,conversion,captures):
    out=bytearray(base);rows=[];tiles=conversion['private_tiles']['primary'];packet=conversion['packet_end']
    descriptor=0x730100
    for i,frame in enumerate(range(56,145,8)):
        pts=actor_pixels(captures/f'frame-{frame:06d}',2)
        image=Image.new('P',(112,112))
        for (x,y),value in pts.items():
            px,py=145-x+56,y-162+100
            if not 0<=px<112 or not 0<=py<112:raise ValueError(f'Capture outside fixed actor canvas: {frame} {x},{y}')
            image.putpixel((px,py),value)
        options=[o for o in pack(image,112) if o[0][0]+2<=17 and o[0][1]+4<=64]
        if not options:raise ValueError(f'No legal OBJ packing for source frame {frame}')
        (count,cost),chunks=min(options,key=lambda item:(item[0][1],item[0][0]))
        if count+2>17 or cost+4>64:raise ValueError('Combined actor and shadow budget exceeded')
        chunks=sorted(chunks,key=lambda c:-c[2]);data=bytearray([count,sum(c[2]==16 for c in chunks)])
        for x,y,size,pixels in chunks:
            dx,dy=x-56,y-100
            if not -64<=dx<64 or not -105<=dy<23:raise ValueError('Raw descriptor coordinate overflow')
            data+=bytes([0,dx&127,(dy+105)&127])
            for ty in range(size//8):
                for tx in range(size//8):
                    raw=planar([pixels[(ty*8+yy)*size+tx*8+xx]for yy in range(8)for xx in range(8)])
                    payload=encode_sprite_tile(raw)
                    if (packet&65535)+len(payload)>65536:packet=(packet+65535)&~65535
                    if packet+len(payload)>0x7d0000 or tiles>=16384:raise ValueError('Private finisher storage exhausted')
                    out[packet:packet+len(payload)]=payload
                    out[0x7d0000+tiles*3:0x7d0003+tiles*3]=packet.to_bytes(3,'little')
                    data+=(0xc000|tiles).to_bytes(2,'little');tiles+=1;packet+=len(payload)
        if descriptor+len(data)>0x734000:raise ValueError('Finisher descriptors overlap profiles')
        out[descriptor:descriptor+len(data)]=data
        ident=1000+i;out[0x710000+ident*3:0x710003+ident*3]=descriptor.to_bytes(3,'little')
        descriptor+=len(data)
        profile=0x734000+i*14
        # Full-body descriptor and native shadow; an extra blank lower OBJ
        # would exceed the 17-object allocation on several lift frames.
        out[profile:profile+14]=(ident*3).to_bytes(2,'little')+bytes(2)+bytes.fromhex('24 80 00 ff ff ff')+bytes([255])*4
        out[0x730000+i*7:0x730007+i*7]=bytes([0x73])+(profile&65535).to_bytes(2,'little')+bytes(4)
        rows.append({'source_frame':frame,'royal_poses':[783+i*2,784+i*2],'raw_primary_index':ident,
                     'objects_including_shadow':count+2,'tiles_including_shadow':cost+4})
    # Repeat the bridge pose so the lift does not return to standing immediately.
    for i in range(12,20):out[0x730000+i*7:0x730007+i*7]=out[0x730000+11*7:0x730007+11*7]
    out[0x730000+20*7]=255
    # A separate opponent stream keeps the receiving wrestler's own Raw parts.
    layout=json.loads((Path(__file__).resolve().parents[1]/'data/perfect-victim-layouts.json').read_text())['rows']
    for i in range(20):
        row=layout[min(i,11)];source=row['profile'];record=bytearray()
        for part in range(8):
            chunk=base[source+part*4:source+part*4+4]
            if chunk[:2]==b'\xff\xff':record+=b'\xff\xff';break
            dx=int.from_bytes(chunk[2:3],'little',signed=True)+row['translate'][0]
            dy=int.from_bytes(chunk[3:4],'little',signed=True)+row['translate'][1]
            if not -128<=dx<128 or not -128<=dy<128:raise ValueError('Victim anchor overflow')
            record+=chunk[:2]+bytes([dx&255,dy&255])
        profile=0x735100+i*32
        out[profile:profile+len(record)]=record
        out[0x735000+i*7:0x735007+i*7]=bytes([0x73])+(profile&65535).to_bytes(2,'little')+bytes(4)
    out[0x735000+20*7]=255
    # Keep secondary pointers out of CPU banks 7E/7F (work RAM).
    secondary_count=conversion['private_tiles']['secondary']
    relocated=0x749800
    out[relocated:relocated+secondary_count*3]=out[0x7dc000:0x7dc000+secondary_count*3]
    for operand in (0x7dc000,0x7dc002):
        old=operand.to_bytes(3,'little');new=(relocated+operand-0x7dc000).to_bytes(3,'little')
        pos=out.index(old,0x70f200,0x70f300);out[pos:pos+3]=new
    payload=encode_sprite_tile(bytes(32))
    out[packet:packet+len(payload)]=payload
    out[relocated+secondary_count*3:relocated+secondary_count*3+3]=packet.to_bytes(3,'little')
    packet+=len(payload)
    out[0x740080:0x740087]=bytes([1,0,0,0,105])+(0xc000|secondary_count).to_bytes(2,'little')
    out[0x711000+724*3:0x711003+724*3]=(0x740080).to_bytes(3,'little')
    # Expand the private graphics worker's limits to include these new indices.
    for at,old,new in [(0x70f000,bytes.fromhex('c9 b2 0b'),bytes.fromhex('c9 dc 0b')),
                       (0x70f100,bytes.fromhex('c9 76 08'),bytes.fromhex('c9 7f 08'))]:
        pos=out.index(old,at,at+256);out[pos:pos+len(new)]=new
    # Use the standing grapple special gate, with native suplex pair actions.
    for n,value in enumerate([1,600,540,266,65535,65535]):out[0x708600+n*32+24:0x708600+n*32+26]=value.to_bytes(2,'little')
    for address,code,hook,expected in [(0x70f300,init_hook(),0x2cecb0,bytes.fromhex('22 dd ee ac')),
                                       (0x70f400,sequence_hook(),0xf073,bytes.fromhex('85 7c a7 7c'))]:
        if out[hook:hook+4]!=expected:raise ValueError(f'Unexpected finisher hook {hook:06x}')
        out[address:address+len(code)]=code;out[hook:hook+4]=bytes([0x5c])+address.to_bytes(3,'little')
    checksum(out)
    return out,{'source':'Royal Rumble native Perfect-Plex, R at low opponent health',
                'source_camera_constant':{'x':177,'y':56},'poses':rows,
                'attacker_animation_staged':True,'victim_and_pin_verified':False,
                'packet_end':packet,'primary_tile_count':tiles}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['base','conversion','captures']:p.add_argument(name,type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out,report=build(a.base.read_bytes(),json.loads(a.conversion.read_text()),a.captures)
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'perfect-plex-prototype.sfc').write_bytes(out)
    (a.output/'plex-report.json').write_text(json.dumps(report,indent=2)+'\n')
