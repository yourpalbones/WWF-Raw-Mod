"""Decode Royal Rumble's forward byte/interleaved graphics stream.

Derived from the native routine at 81:8813; bounded, read-only ROM access.
"""
from pathlib import Path


def decode_block(rom, offset):
    if offset < 0 or offset+5>len(rom):raise ValueError('Royal graphics header outside ROM')
    length=(int.from_bytes(rom[offset+2:offset+4],'little')+1)&0xfffe
    mode=rom[offset+4]
    if not length or mode not in (0,1,2):raise ValueError('Unsupported Royal graphics header')
    output=bytearray(length);written=set();cursor=offset+5;pos=0
    def read():
        nonlocal cursor
        if cursor>=len(rom):raise ValueError('Truncated Royal graphics stream')
        value=rom[cursor];cursor+=1;return value
    def put(value):
        nonlocal pos
        if not 0<=pos<length or pos in written:raise ValueError('Royal graphics output overflow')
        output[pos]=value;written.add(pos);pos+=2 if mode==2 else 1
        if mode==2 and pos>=length:pos=1
    for _ in range(length*2+1024):
        mask=read()
        for bit in range(8):
            if mask>>bit&1:put(read());continue
            low,high=read(),read()
            if high&128:
                count=(high&63)+1
                for i in range(count):put((low+i if high&64 else low)&255)
            else:
                distance=(high>>4)*256+low
                if not distance:
                    if len(written)!=length:raise ValueError('Incomplete Royal graphics output')
                    return bytes(output),{'offset':offset,'mode':mode,'decoded_size':length,'compressed_size':cursor-offset}
                count=(high&15)+3;step=2 if mode==2 else 1
                for _ in range(count):
                    source=pos-distance*step
                    if mode==2 and source<0:source+=length-1
                    if source not in written:raise ValueError('Invalid Royal graphics backreference')
                    put(output[source])
    raise ValueError('Royal graphics command limit exceeded')


def portrait(rom, selector=1, dim=False, native_rgb565=False):
    """Render the source photo locally from ROM graphics, tile map and colors."""
    from PIL import Image
    from inspect_rom import tile
    from royal_rumble_sprites import lorom_offset
    if not 0<=selector<12:raise ValueError('Royal roster selector outside twelve slots')
    def source(words,banks):
        low=int.from_bytes(rom[words+selector*2:words+selector*2+2],'little')
        bank=int.from_bytes(rom[banks+selector*2:banks+selector*2+2],'little')
        return lorom_offset(bank<<16|low)
    graphics,_=decode_block(rom,source(0x734,0x71c))
    mapping,_=decode_block(rom,source(0x764,0x74c))
    low=int.from_bytes(rom[0x77c+selector*2:0x77e+selector*2],'little')
    palette=lorom_offset(0x890000|low)
    colors=[int.from_bytes(rom[palette+i*2:palette+i*2+2],'little')for i in range(96)]
    result=Image.new('RGB',(128,120))
    for i,ident in enumerate(mapping[:240]):
        pixels=tile(graphics,ident*64,8)
        for k,value in enumerate(pixels):
            if value>=len(colors):raise ValueError('Royal portrait color outside its palette')
            levels=[max(0,(colors[value]>>s&31)-(1 if dim else 0))for s in (0,5,10)]
            rgb=tuple(((v<<1)|(v>>4) if native_rgb565 and i==1 else v)*255//(63 if native_rgb565 and i==1 else 31)for i,v in enumerate(levels))
            result.putpixel((i%16*8+k%8,i//16*8+k//8),rgb)
    return result
