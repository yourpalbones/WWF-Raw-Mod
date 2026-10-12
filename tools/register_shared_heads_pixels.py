"""Register shared pose heads with exact native skin texture, independent of tile cuts."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.fft import rfft2,irfft2
from scott_frame_catalog import catalog,raster
from native_gear_art import SKIN,head_region
p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--all',action='store_true');a=p.parse_args();repo=Path(__file__).resolve().parents[1];fs=catalog(a.rom.read_bytes(),a.wram.read_bytes(),9);own=json.loads((repo/'data/nwo-native-anatomy.json').read_text())['heads'];donors=[];values=sorted(SKIN);ci={v:i for i,v in enumerate(values)}
for f in fs:
 if f['kind']!='primary'or f.get('common')or str(f['index'])not in own:continue
 pts,_=raster(f);head,neck=head_region(f,pts);body={q:v for q,v in pts.items()if q not in head and v in SKIN}
 if len(body)<160:continue
 donors.append((f['index'],own[str(f['index'])]['bounds'],neck,body))
target_ids=set([697,698,705,707,711,832,835,836,837,839,840,841,842,844,847,848,850]);targets=[(f,raster(f)[0])for f in fs if f['kind']=='primary'and f.get('common')and(a.all or f['index']in target_ids)];heads={}
for sx,sy in [(1,1),(-1,1),(1,-1),(-1,-1)]:
 bank=np.zeros((len(donors),6,128,128),dtype=np.float32)
 for j,(idx,b,n,body)in enumerate(donors):
  for(x,y),v in body.items():bank[j,ci[v],sy*y%128,sx*x%128]=1
 freq=rfft2(bank,workers=2);del bank
 for f,pts in targets:
  common=np.zeros((6,128,128),dtype=np.float32)
  for(x,y),v in pts.items():
   if v in SKIN:common[ci[v],y%128,x%128]=1
  product=(rfft2(common,workers=2)[None]*freq.conj()).sum(axis=1);corr=irfft2(product,workers=2);peaks=corr.reshape(len(donors),-1).argmax(axis=1);scores=corr.reshape(len(donors),-1)[np.arange(len(donors)),peaks];order=np.argsort(scores)[-8:][::-1]
  for j in order:
   idx,b,neck,body=donors[j];score=float(scores[j])
   if score<160 or score<len(body)*0.94:continue
   dy,dx=divmod(int(peaks[j]),128);dx=dx if dx<64 else dx-128;dy=dy if dy<64 else dy-128
   exact=sum(pts.get((sx*x+dx,sy*y+dy))==v for(x,y),v in body.items())
   if exact<len(body)*0.94:continue
   l,t,r,bottom=b;xx=[sx*l+dx,sx*r+dx];yy=[sy*t+dy,sy*bottom+dy];box=[min(xx),min(yy),max(xx),max(yy)];inside={q:v for q,v in pts.items()if box[0]<=q[0]<=box[2]and box[1]<=q[1]<=box[3]}
   if len(inside)<40 or sum(v in SKIN for v in inside.values())<18:continue
   old=heads.get(str(f['index']))
   if old and old['matching_skin_pixels']>=exact:continue
   heads[str(f['index'])]={'bounds':box,'neck':[sx*neck[0],sy*neck[1]],'donor_primary_piece':int(idx),'matching_skin_pixels':exact,'body_skin_fraction':exact/len(body),'transform':[sx,sy,dx,dy]}
  if str(f['index'])in heads:print(f['index'],heads[str(f['index'])]['donor_primary_piece'],round(heads[str(f['index'])]['body_skin_fraction'],3),flush=True)
 del freq
 a.output.write_text(json.dumps({'version':1,'method':'At least 160 exact skin-shade matches and 94 percent of the known donor body skin. FFT proposes alignment; explicit world-coordinate comparison rejects wrapping.','heads':heads},indent=2)+'\n')
print('Registered',len(heads),'shared heads with skin texture')
