"""Compare privately decoded Boss Man poses against native Sega CD snapshots."""
import argparse,json
from pathlib import Path
from PIL import Image
import rage_cage_boss_source as source
from genesis_sprite_capture import sprite_entries,object_pixels,reconstruct

def normalized(im):
 box=im.getbbox()
 if not box:return None
 im=im.crop(box)
 return im.size,im.tobytes()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('chr',type=Path);p.add_argument('tab',type=Path);p.add_argument('capture',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();source.load_source(a.chr,a.tab)
 catalog={}
 for i in range(415):
  im=source.pose(i)
  for flip in (False,True):
   q=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else im
   catalog.setdefault(normalized(q),[]).append({'pose':i,'hflip':flip})
 records=[]
 for png in sorted(a.capture.glob('frame-*.png')):
  prefix=str(png.with_suffix(''));read=lambda n:Path(prefix+'-'+n+'.bin').read_bytes()
  v,s,r,c=map(read,('vram','oam','registers','cgram'));screen=Image.open(png).convert('RGB');im=Image.new('P',screen.size)
  entries=[e for e in sprite_entries(v,s,r) if e['palette']==2 and e['tile']<64]
  for e in reversed(entries):
   px=object_pixels(v,e)
   for y in range(e['height']):
    for x in range(e['width']):
     value=px[y*e['width']+x];ix,iy=e['x']+x,e['y']+y
     if value and 0<=ix<im.width and 0<=iy<im.height:im.putpixel((ix,iy),value)
  actual=reconstruct(v,s,r,c,entries,screen.size);opaque=matching=0
  for y in range(actual.height):
   for x in range(actual.width):
    q=actual.getpixel((x,y))
    if q[3]:opaque+=1;matching+=screen.getpixel((x,y))==q[:3]
  records.append({'frame':png.stem,'exact_source_matches':catalog.get(normalized(im),[]),'opaque_pixels':opaque,'native_screen_matching_pixels':matching})
 result={'snapshots':len(records),'exact_source_matched_snapshots':sum(bool(r['exact_source_matches']) for r in records),'fully_visible_screen_matched_snapshots':sum(r['opaque_pixels']>0 and r['opaque_pixels']==r['native_screen_matching_pixels'] for r in records),'poses_observed':sorted({m['pose'] for r in records for m in r['exact_source_matches']}),'full_animation_coverage_verified':False,'records':records}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='records'}))
if __name__=='__main__':main()
