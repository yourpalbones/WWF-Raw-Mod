"""Read-only pixel/palette comparison for the private Boss Man Raw prototype."""
import argparse,json
from pathlib import Path
from extract_oam import objects
from verify_hogan_genesis_capture import normalize
from build_hogan_motion_probe import pack_objects
from build_bossman_slot_probe import ROOTS
import rage_cage_boss_source as cd

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('rom','chr','tab','captures'):p.add_argument(n,type=Path)
 p.add_argument('--actor',type=int,choices=(0,1),default=0);p.add_argument('--output',type=Path,required=True);a=p.parse_args();cd.load_source(a.chr,a.tab);rom=a.rom.read_bytes();palette=rom[0x5d6a00:0x5d6a20];sources={}
 for pose in set(ROOTS.values()):
  im=cd.pose(pose);pixels={}
  for y in range(im.height):
   for x in range(im.width):
    v=im.getpixel((x,y))
    if v:
     color=int.from_bytes(palette[v*2:v*2+2],'little');pixels[(x,y)]=tuple((color>>s&31)*255//31 for s in (0,5,10))
  sources[pose]=(pixels,len(pack_objects(im)))
 rows=[]
 for file in sorted(a.captures.glob('*-oam.bin')):
  prefix=Path(str(file)[:-8]);read=lambda s:Path(str(prefix)+'-'+s+'.bin').read_bytes();cg=read('cgram');records=objects(read('vram'),read('oam'),cg,read('registers')[0x2101]);body=[(o,im)for o,im in records if o['palette']==a.actor and a.actor*64<=o['tile']<(a.actor+1)*64 and o['y']<224];matched=[]
  for pose,(pixels,count)in sources.items():
   if len(body)<count:continue
   actual={}
   for o,im in reversed(body[:count]):
    for y in range(im.height):
     for x in range(im.width):
      q=im.getpixel((x,y))
      if q[3]:actual[(o['x']+x,o['y']+y)]=q[:3]
   expected={(-x if body[0][0]['hflip']else x,y):c for (x,y),c in pixels.items()}
   if normalize(actual)==normalize(expected):matched.append(pose)
  rows.append({'frame':prefix.name,'matched_poses':matched,'palette_exact':cg[256+a.actor*32:288+a.actor*32]==palette})
 result={'frames':len(rows),'exact_frames':sum(bool(r['matched_poses'])for r in rows),'exact_palettes':sum(r['palette_exact']for r in rows),'poses_verified':sorted({p for r in rows for p in r['matched_poses']}),'complete_character_verified':False,'rows':rows};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='rows'}))
 if not rows or result['exact_frames']!=len(rows)or result['exact_palettes']!=len(rows):raise SystemExit('Frames need investigation')
if __name__=='__main__':main()
