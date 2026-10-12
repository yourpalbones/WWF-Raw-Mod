"""Consistent red detail on anatomically mapped native Scott trunk pixels."""
from pathlib import Path
from functools import lru_cache
import json
from scott_frame_catalog import raster
@lru_cache(maxsize=1)
def trunk_sources():return json.loads((Path(__file__).resolve().parents[1]/'data/scott-trunk-anatomy.json').read_text())['sources']

def finish_trunks(frame,changes):
 from build_scott_hall_gear import components
 points,mapping=raster(frame);sources=trunk_sources();trunk={q for q,v in points.items()if v in {2,3,4,5,6,8} and mapping[q][1]in sources.get(str(mapping[q][0]['source']),[])}
 def put(q,value):
  ref,k=mapping[q];changes.setdefault(ref['field'],ref['pixels'].copy())[k]=value
 for group in components({q:1 for q in trunk},{1}):
  if len(group)<5:continue
  def current(q):
   ref,k=mapping[q];return changes.get(ref['field'],ref['pixels'])[k]
  if sum(current(q)in {2,3,8}for q in group)>=3:continue
  for q in group:put(q,4 if points[q]in {2,4,6} else 5)
  l=min(x for x,y in group);r=max(x for x,y in group);t=min(y for x,y in group);b=max(y for x,y in group);w=r-l+1;h=b-t+1
  # Keep recognizable detail on narrow views, not a plain black fallback.
  for x,y in group:
   if points[x,y]in {6,8} or (x==l if h>w+3 else y==t):put((x,y),8)
  # Compact HALL mark; clip all pixels to the native cloth island.
  pattern=['101010100100','101101100100','111111100100','101101111111']
  rotate=h>w+3;pw,ph=(4,12)if rotate else(12,4)
  if w>=pw and h>=ph:
   ox=l+(w-pw)//2;oy=t+(h-ph)//2
   for y,row in enumerate(pattern):
    for x,v in enumerate(row):
     q=(ox+3-y,oy+x)if rotate else(ox+x,oy+y)
     if v=='1'and q in group:put(q,8)
 return changes
