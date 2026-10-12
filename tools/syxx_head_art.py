"""Syxx reference head: tall forehead bandana, long hair and connected beard."""
SKIN={7,9,10,11,12,15}
from functools import lru_cache
from pathlib import Path
import json

@lru_cache(maxsize=1)
def face_landmarks():
 return json.loads((Path(__file__).resolve().parents[1]/'data/syxx-face-landmarks.json').read_text())

def draw_head(frame,points,head,neck,put):
 if not head or not neck:return
 nx,ny=neck;score=lambda q:q[0]*nx+q[1]*ny;cross=lambda q:q[0]*ny-q[1]*nx;top=min(map(score,head));face=[q for q,v in head.items()if v in SKIN and top+5<=score(q)<=top+12]
 if not face:return
 center=sum(map(cross,face))/len(face);front=len(face)>=45
 # Restore dark hair around the crown instead of a red cap across its width.
 for q,v in head.items():
  depth=score(q)-top
  if depth<=5 and v in {1,6,8}:put(q,1 if v==1 else 6 if v==6 else 8)
 # A tall central forehead panel sits UNDER the hair. Rear views show the wrap.
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
  if 4<=depth<=12 and 4<=abs(u)<=5.5 and q in head and v in SKIN:put(q,6)
  if neck==(0,1)and front and 12<=depth<=21:
   strand=4.5+(0.5 if depth in {14,15,18,19}else 0)
   if abs(abs(u)-strand)<0.7 and (depth<18 or depth%2==0)and v in SKIN|{1,4,5,6,8}:put(q,6)
 # Exact original-face registration carries the user's nose/mouth landmarks
 # into translated/reflected frames. Never infer a beard from the hair top.
 entry=face_landmarks()['heads'].get(str(frame['index']))
 if not entry:return
 sx,sy,dx,dy=entry['transform']
 transform=lambda x,y:(sx*x+dx,sy*y+dy)
 # In the annotated original: nose y=-33, upper lip=-32, mouth=-31/-30,
 # jaw=-29. Leave the marked mouth pixels open and the eyes untouched.
 beard={}
 for x in range(1,6):beard[x,-32]=6
 for x in (0,1,5):beard[x,-31]=6
 for x in (0,1,4):beard[x,-30]=6
 for x in range(1,5):beard[x,-29]=6
 beard[1,-29]=1
 for (x,y),value in beard.items():
  q=transform(x,y)
  if points.get(q)in SKIN:put(q,value)
 # Even when a broader hair/bandana proposal has imperfect bounds, preserve
 # the exact user-marked facial features in all registered reflections.
 for key in ('eyes','nose','mouth'):
  anchors=face_landmarks()['templates'][str(entry['template'])]['landmarks'][key]
  if key=='nose':anchors=[anchors]
  for x,y in anchors:
   q=transform(x,y)
   if q in points:put(q,points[q])
