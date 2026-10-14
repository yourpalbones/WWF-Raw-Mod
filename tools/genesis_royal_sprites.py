"""Genesis Royal sprite-piece directory and common composite pose reader.

Derives the shape-group packets from the native renderer at $0088FE/$008904.
Source indices identify ROM art only; imported Raw actions require separate maps.
"""
from pathlib import Path
from PIL import Image
from genesis_royal_graphics import decode_tile,u16,u32

COMPONENT_COUNT=835
POSE_COUNT=647


def component(rom,worker,index):
    if not 0 <= worker < 12 or not 0 <= index < COMPONENT_COUNT:
        raise ValueError('Unknown Genesis worker/component')
    directory=0xb694a+u16(rom,0xfe6+worker*2)
    ref=u16(rom,directory+index*2)
    source=0x67402+int.from_bytes(rom[0xb1942+ref:0xb1945+ref],'big')
    cursor=source
    shapes=u16(rom,cursor);cursor+=2
    shape=-1;objects=[]
    while len(objects)<=18:
        coord=u16(rom,cursor);cursor+=2
        if coord&0x8000:
            if not shapes:
                return dict(worker=worker,index=index,reference=ref,source=source,
                            length=cursor-source,objects=objects)
            while True:
                shape+=1;selected=shapes&1;shapes>>=1
                if selected:break
        if not 0 <= shape < 16:
            raise ValueError('Object before valid shape group')
        w,h=1+(shape>>2),1+(shape&3)
        refs=[u16(rom,cursor+i*2)for i in range(w*h)];cursor+=w*h*2
        objects.append(dict(x=coord>>8&127,y=coord&127,width=w*8,height=h*8,tiles=refs))
    raise ValueError('Source component exceeds native object count')


def pose(rom,index):
    if not 0 <= index < POSE_COUNT:raise ValueError('Unknown Genesis pose')
    source=0x65000+u16(rom,0x65000+index*2);cursor=source;parts=[]
    while len(parts)<20:
        ident=u16(rom,cursor);cursor+=2
        if ident==0xffff:return dict(index=index,source=source,parts=parts)
        if ident==0x8000:
            parts.append(dict(shadow=True));continue
        if ident&0x8000:raise ValueError('Unexpected composite terminator')
        dx,dy=rom[cursor:cursor+2];cursor+=2
        parts.append(dict(component=ident//2,dx=dx-256 if dx&128 else dx,dy=dy-256 if dy&128 else dy))
    raise ValueError('Composite pose exceeds parser bounds')


def tile_pixels(raw):
    return [n for b in raw for n in (b>>4,b&15)]


def render_component(rom,worker,index,lookup):
    record=component(rom,worker,index)
    image=Image.new('P',(128,128))
    for obj in reversed(record['objects']):
        for x in range(obj['width']//8):
            for y in range(obj['height']//8):
                pixels=tile_pixels(decode_tile(rom,obj['tiles'][x*(obj['height']//8)+y],lookup)[0])
                for py in range(8):
                    for px in range(8):
                        value=pixels[py*8+px];ix=obj['x']+x*8+px;iy=obj['y']+y*8+py
                        if value and 0<=ix<128 and 0<=iy<128:image.putpixel((ix,iy),value)
    return image,record


def render_pose(rom,worker,index,lookup):
    record=pose(rom,index);image=Image.new('P',(192,192))
    for part in reversed(record['parts']):
        if part.get('shadow'):continue
        pixels,_=render_component(rom,worker,part['component'],lookup)
        mask=Image.frombytes('L',pixels.size,bytes(255 if v else 0 for v in pixels.getdata()))
        image.paste(pixels,(96+part['dx'],128+part['dy']),mask)
    return image,record
