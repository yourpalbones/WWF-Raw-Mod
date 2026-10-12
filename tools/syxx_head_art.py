"""Syxx reference head: tall forehead bandana, long hair and connected beard."""
SKIN={7,9,10,11,12,15}
from functools import lru_cache
from pathlib import Path
import json
from scott_frame_catalog import raster

@lru_cache(maxsize=1)
def face_landmarks():
 return json.loads((Path(__file__).resolve().parents[1]/'data/syxx-face-landmarks.json').read_text())

def draw_head(frame,points,head,neck,put):
 if not head or not neck:return
 entry=face_landmarks()['heads'].get(str(frame['index']))
 # Several primary descriptors contain only an arm, a weapon or an effect.
 # Their heuristic anatomy boxes must not receive a red forehead panel.
 if not entry and sum(v in {1,6,8}for v in head.values())<12:return
 # Each template records its own drawing axis. Body centroids can point
 # sideways when an arm is raised; the copied face supplies its orientation
 # even in reflected/upside-down animation pieces.
 if entry:
  template=face_landmarks()['templates'][str(entry['template'])]
  sx,sy,dx,dy=entry['transform']
  tx,ty=template.get('head_axis',[0,1]);neck=(tx*sx,ty*sy)
  l,t,r,b=template['source_box'];mapping=raster(frame)[1]
  face_fields={mapping[sx*x+dx,sy*y+dy][0]['field']for y in range(t,b+1)for x in range(l,r+1)if(sx*x+dx,sy*y+dy)in mapping}
 nx,ny=neck;score=lambda q:q[0]*nx+q[1]*ny;cross=lambda q:q[0]*ny-q[1]*nx;top=min(map(score,head));face=[q for q,v in head.items()if v in SKIN and top+5<=score(q)<=top+12]
 if not face:return
 center=sum(map(cross,face))/len(face);front=len(face)>=45
 if entry:
  template=face_landmarks()['templates'][str(entry['template'])]
  sx,sy,dx,dy=entry['transform']
  top=template.get('crown_score',template['crown_y'])+nx*dx+ny*dy
  center=template['hair_center']*sx*sy+dx*ny-dy*nx
 # Restore dark hair around the crown instead of a red cap across its width.
 for q,v in head.items():
  depth=score(q)-top
  if depth<=5 and v in {1,6,8}:put(q,1 if v==1 else 6 if v==6 else 8)
  # Native brown hair highlights share a shade with skin. Recolor only
  # pixels surrounded by existing hair, not every use of that skin shade.
  if v==9 and sum(head.get((q[0]+dx,q[1]+dy))in {1,6,8}for dx,dy in[(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)])>=3:put(q,6)
 # A tall central forehead panel sits UNDER the hair. Rear views show the wrap.
 if entry:
  for x,y,value in template['bandana']:
   q=(sx*x+dx,sy*y+dy)
   if template.get('face_occluded')and points.get(q)not in {1,6,8}:continue
   if q in mapping and mapping[q][0]['field']in face_fields:put(q,value)
 else:
  half=3.5 if front else 5
  for q in head:
   depth=score(q)-top;u=cross(q)-center
   if (1<=depth<=5 if front else 2<=depth<=3)and abs(u)<=half and head[q]not in {4,5}:
    put(q,3 if depth==1 or abs(u)>half-1 else 2)
    if front and ((depth==2 and abs(u)<0.6)or(depth==4 and 0.8<u<1.8)):put(q,5)
 # Thick wet strands frame the face and fall over existing shoulder pixels.
 # Keep the native silhouette; no detached strands or new opaque pixels.
 for q,v in points.items():
  depth=score(q)-top;u=cross(q)-center
  if 4<=depth<=12 and 4<=abs(u)<=5.5 and q in head and v in SKIN and(not entry or not template.get('face_occluded')and mapping[q][0]['field']in face_fields):put(q,6)
  if neck==(0,1)and front and entry and entry['template']==1 and 12<=depth<=21:
   strand=4.5+(0.5 if depth in {14,15,18,19}else 0)
   if abs(abs(u)-strand)<0.7 and (depth<18 or depth%2==0)and v in SKIN|{1,4,5,6,8}:put(q,6)
 # Exact original-face registration carries the user's nose/mouth landmarks
 # into translated/reflected frames. Never infer a beard from the hair top.
 if not entry:return
 sx,sy,dx,dy=entry['transform']
 transform=lambda x,y:(sx*x+dx,sy*y+dy)
 template=face_landmarks()['templates'][str(entry['template'])]
 # Each independently traced head drawing has its own mouth and jaw rows.
 # The original user-approved front-facing mask remains unchanged.
 beard={}
 for y,xs in template['beard_rows'].items():
  for x in xs:beard[x,int(y)]=6
 for x,y in template.get('dark_pixels',[]):beard[x,y]=1
 for (x,y),value in beard.items():
  q=transform(x,y)
  if points.get(q)in SKIN and mapping[q][0]['field']in face_fields:put(q,value)
 # Even when a broader hair/bandana proposal has imperfect bounds, preserve
 # the exact user-marked facial features in all registered reflections.
 for key in ('eyes','nose','mouth'):
  anchors=template['landmarks'][key]
  if key=='nose':anchors=[anchors]
  for x,y in anchors:
   q=transform(x,y)
   if q in points:put(q,points[q])
