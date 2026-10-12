"""Propose unmapped shared heads from thick black hair near the upper-body objects."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_opening,label
from scott_frame_catalog import catalog,raster
SKIN={7,9,10,11,12,15}
p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();fs=catalog(a.rom.read_bytes(),a.wram.read_bytes(),9);result={}
for f in fs:
 if f['kind']!='primary'or not f.get('common'):continue
 pts,mapping=raster(f);mask=np.zeros((128,128),dtype=bool)
 for(x,y),v in pts.items():
  if v==1 and 0<=y+105<128 and 0<=x+64<128:mask[y+105,x+64]=1
 opened=binary_opening(mask,structure=np.ones((2,2)));labels,n=label(opened);fields={r['field']for part in f['parts'][:2]for r in part['refs']};candidates=[]
 for group in range(1,n+1):
  ys,xs=np.where(labels==group);core=[(int(x)-64,int(y)-105)for x,y in zip(xs,ys)]
  if len(core)<6:continue
  if not any(q in mapping and mapping[q][0]['field']in fields for q in core):continue
  cx=sum(x for x,y in core)/len(core);cy=sum(y for x,y in core)/len(core);near=[q for q,v in pts.items()if v in SKIN and abs(q[0]-cx)<=8 and abs(q[1]-cy)<=8]
  if len(near)<35:continue
  body=[q for q,v in pts.items()if v in SKIN and q not in near]
  if not body:continue
  dx=sum(x for x,y in body)/len(body)-cx;dy=sum(y for x,y in body)/len(body)-cy
  nx,ny=(1 if dx>=0 else -1,0)if abs(dx)>abs(dy)*1.3 else(0,1 if dy>=0 else -1)
  score=min(x*nx+y*ny for x,y in core)-1;cross=sum(x*ny-y*nx for x,y in near)/len(near);corners=[]
  for s in[score,score+15]:
   for u in[round(cross)-7,round(cross)+7]:corners.append((s*nx+u*ny,s*ny-u*nx))
  box=[min(x for x,y in corners),min(y for x,y in corners),max(x for x,y in corners),max(y for x,y in corners)];candidates.append((len(core),{'bounds':box,'neck':[nx,ny],'hair_core_pixels':len(core),'nearby_skin_pixels':len(near)}))
 if candidates:result[str(f['index'])]=max(candidates,key=lambda c:c[0])[1]
a.output.write_text(json.dumps({'version':1,'method':'Proposals only: opened thick black hair in the first two upper-body objects, with at least 35 neighboring skin pixels.','heads':result},indent=2)+'\n');print('Proposed',len(result),'shared heads');print({str(i):result.get(str(i))for i in[697,705,707,711,835,836,837,839,840,841,842,844,847,850]})
