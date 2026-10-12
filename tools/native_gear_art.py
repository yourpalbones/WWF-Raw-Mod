"""Author gear details in mapped native anatomical regions, preserving silhouettes."""
from pathlib import Path
from functools import lru_cache
import json
from scott_frame_catalog import raster
from build_scott_hall_gear import components
SKIN={7,9,10,11,12,15}
@lru_cache(maxsize=1)
def anatomy():return json.loads((Path(__file__).resolve().parents[1]/'data/nwo-native-anatomy.json').read_text())['heads']

@lru_cache(maxsize=1)
def common_anatomy():return json.loads((Path(__file__).resolve().parents[1]/'data/syxx-common-heads.json').read_text())['heads']

def head_region(frame,points,include_common=False):
 if frame['kind']!='primary':return {},None
 entry=anatomy().get(str(frame['index']))if not frame.get('common') else common_anatomy().get(str(frame['index']))if include_common else None
 if not entry:return {},None
 l,t,r,b=entry['bounds'];head={q:v for q,v in points.items()if l<=q[0]<=r and t<=q[1]<=b};outside=[q for q,v in points.items()if q not in head and v in SKIN]
 cx,cy=(l+r)/2,(t+b)/2
 if outside:
  dx=sum(x for x,y in outside)/len(outside)-cx;dy=sum(y for x,y in outside)/len(outside)-cy
 else:dx,dy=0,1
 # The neck points toward the rest of the torso, not the screen bottom.
 if abs(dx)>abs(dy)*1.3:neck=(1 if dx>=0 else -1,0)
 else:neck=(0,1 if dy>=0 else -1)
 return head,neck

def decorate(frame,slot):
 points,mapping=raster(frame);changes={};head,neck=head_region(frame,points,slot==9)
 def put(q,value):
  if q in mapping:
   ref,k=mapping[q];changes.setdefault(ref['field'],ref['pixels'].copy())[k]=value
 if slot==10:
  for q,v in points.items():
   if v in {2,3,4,5,6,8,13,14}:
    # Primary native singlet is red, secondary leg/boot cloth stays black.
    put(q,({2:2,3:3,4:6,5:8,6:6,8:8,13:13,14:14} if frame['kind']=='primary' else {2:2,3:3,4:2,5:3,6:2,8:3,13:2,14:3})[v])
  for q,v in head.items():
   if v in {2,3,4,5,6,8,13,14} and (v not in {4,5} or mapping[q][0]['source'] not in anatomy()[str(frame['index'])]['shared_sources']):put(q,13 if v in {2,4,6,13} else 14)
 else:
  # Original blue cloth becomes black; native gray hair uses brown/black.
  # No global white slot, and no arbitrary connected-component white glyph.
  for q,v in points.items():
   if v==5:put(q,8)
  for q,v in head.items():
   if v in {1,4,5,6,8,13,14}:put(q,1 if v==1 else 6 if v in {4,6,13} else 8)
 if slot==9:
  from syxx_head_art import draw_head
  draw_head(frame,points,head,neck,put)
 # Place a small authored chest mark only on front-facing, upright torso cloth.
 if frame['kind']=='primary' and head and neck==(0,1) and sum(v in SKIN for v in head.values())>60:
  garments=components({q:v for q,v in points.items()if q not in head},{4,5})
  if garments:
   garment=max(garments,key=len);l=min(x for x,y in garment);r=max(x for x,y in garment);t=min(y for x,y in garment);b=max(y for x,y in garment)
   if r-l>=12 and b-t>=8 and len(garment)>=60:
    if slot==10:
     # OUT / SIDERS in compact native-sized lettering; black on red.
     pattern=['00001101001110000','00001011010100000','00001011010100000','00001101110100000','00000000000000000','11111010111110111','10001111110011010','01101111110010001','11111010111110111'];ink=2
    else:
     # Stylized THUG chest mark in red, clipped to the native shirt.
     pattern=['111101101011110','010101101010101','010111101010110','010101111011110'];ink=2
    ox=(l+r-len(pattern[0])+1)//2;oy=t+max(2,(b-t-len(pattern))//2)
    for y,row in enumerate(pattern):
     for x,v in enumerate(row):
      q=(ox+x,oy+y)
      if v=='1' and q in garment:put(q,ink)
 return changes
