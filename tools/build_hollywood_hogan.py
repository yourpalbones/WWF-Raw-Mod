"""Convert the existing 16-slot Hogan artwork without changing gameplay code.

Requires private user ROMs. Masks/joints describe source body components, never
palette-wide skin replacement. Only mapped existing poses are converted. The
source sprite/pose hashes are checked against the actual compiled input first.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
from PIL import Image,ImageDraw
from genesis_royal_sprites import render_pose,render_component,pose
from genesis_royal_graphics import color_lookup,SOURCE_SHA256
from build_hogan_motion_probe import ROOTS
from build_hogan_grapple_probe import BINDINGS
from decode_sprite_tile import decode_sprite_tile,encode_sprite_tile
from build_bret_gear import planar
from build_nwo_gear import checksum

# Hip -> knee axes, measured in each source lower-body component's tight crop.
# Shared source components use one mask/design across every composed frame.
LEGS={
17:[(4,6,4,24),(15,6,18,23)],19:[(4,6,10,21)],21:[(5,6,12,23)],23:[(4,5,13,24)],25:[(5,6,6,25),(10,5,15,22)],
27:[(7,5,3,23),(13,5,25,18)],29:[(4,5,12,24),(11,4,22,23)],30:[(6,6,7,24),(11,6,16,23)],31:[(5,5,5,22)],32:[(5,5,5,24),(10,5,14,23)],33:[(4,4,4,19),(11,5,15,20)],34:[(5,5,6,23),(10,5,13,24)],
71:[(5,19,17,6)],74:[(5,21,18,5)],76:[(3,12,10,21),(8,17,21,7)],80:[(6,5,13,20),(12,5,24,15)],
105:[(6,7,17,25),(10,3,28,4)],107:[(7,7,22,28),(15,4,27,1)],123:[(5,6,14,24)],125:[(24,7,17,19),(28,5,38,20)],127:[(24,6,32,22),(19,7,16,21)],
179:[(6,6,11,24),(13,6,23,21)],267:[(8,5,21,22),(14,4,29,17)],182:[(16,5,17,24),(21,6,32,20)],184:[(5,6,11,24)],193:[(8,5,22,24),(15,4,29,21)],195:[(7,6,12,25),(12,4,21,10)],198:[(6,5,7,25),(10,4,29,3)],208:[(7,7,18,17)],
275:[(14,5,10,23),(20,6,31,21)],277:[(6,7,15,24)],279:[(7,7,13,24)],281:[(7,7,16,25)],283:[(7,6,17,25)],285:[(7,7,18,25)],431:[(5,7,10,24)],326:[(6,8,9,24)],342:[(5,8,10,24)],344:[(6,7,15,20)],346:[(6,7,11,20)],348:[(5,7,14,22)],350:[(7,8,10,26),(14,11,20,23)],455:[(7,7,18,22)],
756:[(7,41,24,40)],757:[(7,40,26,34)],758:[(9,41,26,32)],759:[(23,39,31,26)],760:[(22,37,36,33)]}
# Whole-body landing drawings need explicit cloth boundaries to preserve torso.
MIXED={756:[(0,42),(8,36),(23,36),(49,39),(49,64),(0,64)],757:[(0,40),(7,37),(27,31),(51,32),(51,52),(0,52)],758:[(4,41),(10,36),(24,29),(51,25),(51,49),(4,49)],759:[(17,41),(27,32),(28,21),(58,12),(58,48),(17,48)],760:[(16,35),(25,32),(60,29),(60,55),(16,55)]}
PALETTE=[(0,0,0),(106,32,0),(148,74,0),(180,106,32),(222,148,106),(8,8,16),(24,24,32),(40,40,48),(64,64,72),(173,173,173),(247,247,239),(66,24,16),(115,49,32),(181,165,107),(247,231,181),(74,32,0)]
CLOTH={1:5,2:6,3:7,4:8,5:5,6:5,7:6,8:7,9:7,10:8,11:5,12:6,13:6,14:7,15:5}

def palette_bytes():
 return b''.join((round(r*31/255)|round(g*31/255)<<5|round(b*31/255)<<10).to_bytes(2,'little')for r,g,b in PALETTE)
def physical(a):return a if 0x400000<=a<0x7e0000 else a&0x3fffff
def word(r,a):return int.from_bytes(r[a:a+2],'little')
def long(r,a):return int.from_bytes(r[a:a+3],'little')
def tile_pixels(raw):
 return [sum(((raw[y*2+(b&1)+(16 if b>=2 else 0)]>>(7-x))&1)<<b for b in range(4))for y in range(8)for x in range(8)]
def descriptors(r):
 result=[]
 for i in range(256):
  root=word(r,0x4a7000+i*4)
  if root==65535:break
  address=physical(long(r,0x4ab000+i*3));at=address;n,large=r[at:at+2];at+=2;parts=[]
  if not 1<=n<=15 or large>n:raise ValueError('Unsupported body-object layout')
  for j in range(n):
   mode,x,y=r[at:at+3];at+=3
   if mode:raise ValueError('Unsupported body coordinate mode')
   x=(x-128 if x&64 else x)+80;y=y-105+112;s=16 if j<large else 8;ids=[]
   for k in range(s*s//64):ids.append((at,word(r,at)));at+=2
   parts.append((x,y,s,ids))
  result.append(dict(root=root,address=address,end=at,parts=parts))
 return result

def original_pose(r,record):
 im=Image.new('P',(160,160))
 for x,y,s,ids in record['parts']:
  for k,(_,ident) in enumerate(ids):
   offset=physical(long(r,0x548000+(ident&16383)*3));pixels=tile_pixels(decode_sprite_tile(r,offset)[0]);tx=k%(s//8)*8;ty=k//(s//8)*8
   for py in range(8):
    for px in range(8):
     v=pixels[py*8+px]
     if v:im.putpixel((x+tx+px,y+ty+py),v)
 return im

def convert_component(source,index):
 im=source.copy();bb=source.getbbox()
 if not bb:return im
 crop=source.crop(bb);out=crop.copy();mask=Image.new('L',crop.size)
 if index in LEGS:
  if index in MIXED:ImageDraw.Draw(mask).polygon(MIXED[index],fill=255)
  else:mask.paste(255,(0,0,*crop.size))
  for y in range(crop.height):
   for x in range(crop.width):
    v=crop.getpixel((x,y))
    if v and (mask.getpixel((x,y)) or (index in MIXED and y>=28 and v in (13,14))):
     mask.putpixel((x,y),255);out.putpixel((x,y),CLOTH[v])
  # Native-scale angular lightning, clipped inside cloth. One-pixel main stem
  # with a sparse branch; articulated hip/knee axes follow the actual drawing.
  for hx,hy,kx,ky in LEGS[index]:
   dx,dy=kx-hx,ky-hy;length=max(1,math.hypot(dx,dy));nx,ny=-dy/length,dx/length
   points=[]
   for t,bend in [(0,0),(.20,-1),(.36,1),(.50,-1),(.68,1),(.84,0),(1,-1)]:points.append((round(hx+dx*t+nx*bend),round(hy+dy*t+ny*bend)))
   bolt=Image.new('L',crop.size);d=ImageDraw.Draw(bolt);d.line(points,fill=10,width=1);p=points[3];d.line([p,(round(p[0]-nx*3+dx*.10),round(p[1]-ny*3+dy*.10))],fill=9,width=1)
   for y in range(crop.height):
    for x in range(crop.width):
     v=bolt.getpixel((x,y))
     if v and mask.getpixel((x,y)) and crop.getpixel((x,y)) and out.getpixel((x,y))!=5:out.putpixel((x,y),v)
 # Preserve the exact face landmarks and hair outline; the private hair ramp
 # becomes pale blond rather than changing skin values into hair or paint.
 im.paste(out,bb[:2]);return im

def source_bindings():return {**ROOTS,**BINDINGS,**{0xf000+i*2:p for i,p in enumerate([115,57,58,475,476,477,478,479])}}
def build(base,genesis,destination):
 if hashlib.sha256(genesis).hexdigest()!=SOURCE_SHA256:raise ValueError('Unsupported source ROM')
 if len(base)!=0x800000 or base[0x19d43f]!=16 or base[0x4aef00:0x4aef0e]!=b'HOGAN14-PROBE1':raise ValueError('Requires the supported sixteen-slot preview')
 destination.mkdir(parents=True,exist_ok=True);source_dir=destination/'native-poses';source_dir.mkdir(exist_ok=True)
 out=bytearray(base);records=descriptors(base);bindings=source_bindings();lookup=color_lookup(genesis);cache={};tiles={};pointer_writes=[];reports=[]
 for i,record in enumerate(records):
  root=record['root'];source_index=bindings[root];original,_=render_pose(genesis,6,source_index,lookup);original=original.crop((16,17,176,177));actual=original_pose(base,record)
  if original.tobytes()!=actual.tobytes():raise ValueError(f'Existing art differs from source at root {root:04x}; do not overwrite edits')
  picture=Image.new('P',(192,192))
  for part in reversed(pose(genesis,source_index)['parts']):
   if part.get('shadow'):continue
   ident=part['component']
   if ident not in cache:
    im,_=render_component(genesis,6,ident,lookup);cache[ident]=convert_component(im,ident)
   im=cache[ident];mask=Image.frombytes('L',im.size,bytes(255 if v else 0 for v in im.getdata()));picture.paste(im,(96+part['dx'],128+part['dy']),mask)
  picture=picture.crop((16,17,176,177))
  if bytes(bool(v)for v in picture.getdata())!=bytes(bool(v)for v in actual.getdata()):raise ValueError('Appearance edit changed the native silhouette')
  for x,y,s,ids in record['parts']:
   for k,(at,oldident) in enumerate(ids):
    tx=k%(s//8)*8;ty=k//(s//8)*8;raw=planar([picture.getpixel((x+tx+px,y+ty+py))for py in range(8)for px in range(8)])
    if raw not in tiles:tiles[raw]=len(tiles)
    out[at:at+2]=(0xc000|tiles[raw]).to_bytes(2,'little')
  reports.append({'root':f'{root:04X}','source_pose':source_index,'body_objects':len(record['parts']),'silhouette_preserved':True,'changed_pixels':sum(a!=b for a,b in zip(actual.getdata(),picture.getdata()))})
  for im,label in [(picture,'hollywood'),(actual,'original')]:
   pal=palette_bytes() if label=='hollywood'else base[0x4a6a00:0x4a6a20];rgb=[tuple((word(pal,j*2)>>s&31)*255//31 for s in(0,5,10))for j in range(16)];im.putpalette(sum([list(c)for c in rgb],[])+[0]*720);im.save(source_dir/f'{i:02d}-{root:04x}-{label}.png')
 # Private Hogan pools only; exclude HUD atlas, existing descriptors and added
 # worker MIDI at 543000. No engine/profile/stat/AI/collision bytes are touched.
 pools=[(0x550000,0x558000),(0x55b000,0x560000),(0x54a000,0x550000)]
 for a,b in pools:out[a:b]=b'\xff'*(b-a)
 pool=0;cursor=pools[0][0]
 for raw,ident in tiles.items():
  data=encode_sprite_tile(raw)
  if cursor+len(data)>pools[pool][1]:pool+=1;cursor=pools[pool][0]
  if cursor+len(data)>pools[pool][1]:raise ValueError('Hogan sprite pool exhausted')
  out[cursor:cursor+len(data)]=data;at=0x548000+ident*3
  if at+3>0x54a000:raise ValueError('Private tile directory exhausted')
  out[at:at+3]=cursor.to_bytes(3,'little');cursor+=len(data)
 out[0x4a6a00:0x4a6a20]=palette_bytes();checksum(out);out[0x400000:0x410000]=out[:65536]
 # Decode every newly written object: compare its actual compiled image to the
 # authored composite, not just whether serialization/build returned success.
 for i,record in enumerate(descriptors(out)):
  decoded=original_pose(out,record);authored=Image.open(source_dir/f'{i:02d}-{record["root"]:04x}-hollywood.png')
  if decoded.tobytes()!=authored.tobytes():raise ValueError('Compiled tile round trip failed')
 (destination/'Hollywood-Hogan-art.sfc').write_bytes(out)
 report={'input_sha256':hashlib.sha256(base).hexdigest(),'output_sha256':hashlib.sha256(out).hexdigest(),'slot':13,'display_slot':14,'mapped_poses':len(records),'private_tiles':len(tiles),'packet_end':hex(cursor),'components':len(cache),'converted_clothing_components':sorted(set(cache)&set(LEGS)),'palette_colors_including_transparent':16,'gameplay_code_changed':False,'silhouettes_and_descriptors_geometry_preserved':True,'compiled_pose_roundtrips':len(records),'complete_animation_coverage':False,'limitation':'Existing unmapped native actions still use the original standing fallback; this conversion does not add animation mappings.','poses':reports}
 (destination/'art-verification.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('base',type=Path);p.add_argument('genesis',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=build(a.base.read_bytes(),a.genesis.read_bytes(),a.output);print(json.dumps({k:v for k,v in r.items()if k!='poses'},indent=2))
