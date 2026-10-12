"""Decode Scott's known primary/secondary frame pieces and native object positions."""
from pathlib import Path
from inventory_bret_frames import parse_frame,lookup
from decode_sprite_tile import decode_sprite_tile
from inspect_rom import tile
from PIL import Image
SELECTOR=5
KINDS=[('primary',0x2dd513,0x2dd52d,527,0x4d55,0xc8,0x79e0,0),('secondary',0x2dd547,0x2dd561,426,0x1fff,0xdd,0xa880,0x27c)]
def catalog(rom,wram,selector=SELECTOR):
 result=[]
 for kind,table,banks,count,threshold,bank,base,directory in KINDS:
  directory_offset=(rom[banks+selector*2]<<16|int.from_bytes(rom[table+selector*2:table+selector*2+2],'little'))&0x3fffff
  common_offset=(rom[banks+16]<<16|int.from_bytes(rom[table+16:table+18],'little'))&0x3fffff
  limit=998 if kind=='primary'else 722
  for i in range(limit):
   entry=(directory_offset if i<count else common_offset)+i*3;pointer=rom[entry]<<16|int.from_bytes(rom[entry+1:entry+3],'little');f=parse_frame(rom,pointer);cursor=f['offset']+2;x,y=(0x70,0x4a)if kind=='primary'else(0x78,0x3a);x_table,y_table=(0xbf2e,0xbf4e)if kind=='primary'else(0xbf6e,0xbf8e);parts=[]
   for obj in range(f['objects']):
    control=rom[cursor];cursor+=1
    if not control:x,y=rom[cursor:cursor+2];cursor+=2
    else:
     dx,dy=control>>4,control&15
     if dx:x=(x+int.from_bytes(rom[x_table+dx*2:x_table+dx*2+2],'little'))&255
     else:x=rom[cursor];cursor+=1
     if dy:y=(y+int.from_bytes(rom[y_table+dy*2:y_table+dy*2+2],'little'))&255
     else:y=rom[cursor];cursor+=1
    size=16 if obj<f['large_objects']else 8;refs=[]
    for sub in range(4 if size==16 else 1):
     id=int.from_bytes(rom[cursor:cursor+2],'little');source,compressed=lookup(id,wram,threshold,bank,base,directory);source&=0x3fffff;data,length=decode_sprite_tile(rom,source)if compressed else(rom[source:source+32],32)
     refs.append({'field':cursor,'relative':cursor-f['offset'],'tile_id':id,'source':source,'compressed':compressed,'length':length,'pixels':tile(data,0,4)});cursor+=2
    px=x&127;px=px-128 if px&64 else px
    parts.append({'x':px,'y':(y&127)-105,'size':size,'hflip':bool(x&128),'vflip':bool(y&128),'refs':refs})
   assert cursor==f['offset']+f['length']
   result.append({**f,'kind':kind,'index':i,'entry':entry,'common':i>=count,'parts':parts})
 return result

def raster(frame):
 parts=frame['parts'];points={};mapping={}
 for part in reversed(parts):
  size=part['size']
  for y in range(size):
   for x in range(size):
    sx=size-1-x if part['hflip']else x;sy=size-1-y if part['vflip']else y;ref=part['refs'][(sy>>3)*(size>>3)+(sx>>3)];k=sy%8*8+sx%8;p=ref['pixels'][k]
    if p:points[(part['x']+x,part['y']+y)]=p;mapping[(part['x']+x,part['y']+y)]=(ref,k)
 return points,mapping

def image(frame,colors):
 points,_=raster(frame)
 if not points:return Image.new('RGBA',(1,1)),(0,0)
 l=min(x for x,y in points);t=min(y for x,y in points);r=max(x for x,y in points)+1;b=max(y for x,y in points)+1;im=Image.new('RGBA',(r-l,b-t))
 for (x,y),p in points.items():im.putpixel((x-l,y-t),tuple((colors[p]>>s&31)*255//31 for s in [0,5,10])+(255,))
 return im,(l,t)
if __name__=='__main__':
 import sys
 from PIL import ImageDraw
 rom=Path(sys.argv[1]).read_bytes();wram=Path(sys.argv[2]).read_bytes();out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True);frames=catalog(rom,wram);colors=[int.from_bytes(rom[0x2cc57a+i*2:0x2cc57c+i*2],'little')for i in range(16)]
 for kind in ['primary','secondary']:
  subset=[f for f in frames if f['kind']==kind];page=Image.new('RGB',(16*120,((len(subset)+15)//16)*120),'#262626');draw=ImageDraw.Draw(page)
  for n,f in enumerate(subset):
   im,_=image(f,colors);im.thumbnail((95,95));x=n%16*120;y=n//16*120;page.paste(im,(x+(120-im.width)//2,y+20),im);draw.text((x+4,y+3),str(f['index']),fill='white')
  page.save(out/(kind+'-catalog.png'))
 print('Decoded',len(frames),'directory entries')
