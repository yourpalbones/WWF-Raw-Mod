"""Locate shared heads by registering identical native body pixels to known poses."""
import argparse,json
from pathlib import Path
from collections import Counter,defaultdict
from scott_frame_catalog import catalog,raster
from native_gear_art import SKIN,head_region
p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();repo=Path(__file__).resolve().parents[1];fs=catalog(a.rom.read_bytes(),a.wram.read_bytes(),9);own=json.loads((repo/'data/nwo-native-anatomy.json').read_text())['heads'];signatures={}
def skin_signature(ref):
 if ref['source']not in signatures:signatures[ref['source']]=bytes(v if v in SKIN else 0 for v in ref['pixels'])
 return signatures[ref['source']]
donors=[];by_source=defaultdict(set)
for f in fs:
 if f['kind']!='primary'or f.get('common')or str(f['index'])not in own:continue
 pts,mapping=raster(f);head,neck=head_region(f,pts);body={}
 for q,v in pts.items():
  if q not in head and v in SKIN:
   ref,k=mapping[q];body.setdefault((skin_signature(ref),k),[]).append(q)
 sources={s for s,k in body};donors.append((f['index'],own[str(f['index'])]['bounds'],neck,body,sources))
 for s in sources:by_source[s].add(len(donors)-1)
heads={}
for f in fs:
 if f['kind']!='primary'or not f.get('common'):continue
 pts,mapping=raster(f);body={}
 for q,v in pts.items():
  if v in SKIN:
   ref,k=mapping[q];body.setdefault((skin_signature(ref),k),[]).append(q)
 votes=Counter(j for s in{s for s,k in body}for j in by_source[s]);best=None
 for j,n in votes.most_common(14):
  if n<5:continue
  index,bounds,neck,other,sources=donors[j];keys=body.keys()&other.keys()
  for sx,sy in[(1,1),(-1,1),(1,-1),(-1,-1)]:
   offsets=Counter((x-sx*xx,y-sy*yy)for key in keys for x,y in body[key]for xx,yy in other[key])
   if not offsets:continue
   (dx,dy),count=offsets.most_common(1)[0]
   if count<90 or(best and count<=best[0]):continue
   supported={s for s,k in keys if any(x==sx*xx+dx and y==sy*yy+dy for x,y in body[s,k]for xx,yy in other[s,k])}
   if len(supported)<5:continue
   l,t,r,b=bounds;xx=[sx*l+dx,sx*r+dx];yy=[sy*t+dy,sy*b+dy];box=[min(xx),min(yy),max(xx),max(yy)];inside={q:v for q,v in pts.items()if box[0]<=q[0]<=box[2]and box[1]<=q[1]<=box[3]}
   if len(inside)<40 or sum(v in SKIN for v in inside.values())<18:continue
   best=(count,{'bounds':box,'neck':[sx*neck[0],sy*neck[1]],'donor_primary_piece':index,'matching_skin_pixels':count,'matching_tile_sources':len(supported),'transform':[sx,sy,dx,dy]})
 if best:heads[str(f['index'])]=best[1]
 print('registered',f['index'],best[1]['donor_primary_piece']if best else None,flush=True)if f['index']in[698,705,707,711,830,832,835,836,837,839,840,841,842]else None
a.output.write_text(json.dumps({'version':1,'method':'At least 90 identical skin-pixel matches across five distinct normalized native body tiles; transferred head bounds from the best registered character-specific pose.','heads':heads},indent=2)+'\n');print('Registered',len(heads),'shared heads')
