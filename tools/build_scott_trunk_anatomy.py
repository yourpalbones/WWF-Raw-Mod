"""Map native trunk pixels by source identity, including pieces without a logo."""
import argparse,json
from pathlib import Path
from collections import defaultdict
from scott_frame_catalog import catalog,raster
from build_scott_hall_gear import components
p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();frames=catalog(a.rom.read_bytes(),a.wram.read_bytes(),5);sources=defaultdict(set);seeded=[]
for f in frames:
 if f['kind']=='primary'and not f.get('common'):continue
 points,mapping=raster(f)
 for group in components(points,{2,3,4,5,6,8}):
  cloth={q for q in group if points[q]in{2,3,4,5}};gold={q for q in group if points[q]in{6,8}}
  if len(cloth)<8 or len(gold)<3:continue
  l=min(x for x,y in group);r=max(x for x,y in group);t=min(y for x,y in group);b=max(y for x,y in group)
  if r-l+1>32 or b-t+1>24 or len(group)>350:continue
  seeded.append([f['kind'],f['index']])
  for q in group:
   ref,k=mapping[q];sources[str(ref['source'])].add(k)
sources={key:sorted(value)for key,value in sources.items()if len(value)>=6};a.output.write_text(json.dumps({'version':1,'method':'Native gold-marked trunk islands, propagated through identical tile source pixels.','sources':sources,'seed_frames':seeded},separators=(',',':'))+'\n');print(len(sources),'trunk tile sources;',len(seeded),'seed frame islands')
