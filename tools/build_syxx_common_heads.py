"""Propagate known native head pixel masks into shared animation pieces."""
import argparse,json
from pathlib import Path
from collections import defaultdict,Counter
from scott_frame_catalog import catalog,raster
from build_scott_hall_gear import components
p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();repo=Path(__file__).resolve().parents[1];fs=catalog(a.rom.read_bytes(),a.wram.read_bytes(),9);own=json.loads((repo/'data/nwo-native-anatomy.json').read_text())['heads'];masks=defaultdict(set)
for f in fs:
 if f['kind']!='primary' or f.get('common')or str(f['index'])not in own:continue
 entry=own[str(f['index'])];l,t,r,b=entry['bounds'];pts,mapping=raster(f)
 for q,v in pts.items():
  if l<=q[0]<=r and t<=q[1]<=b:
   ref,k=mapping[q]
   if ref['source']not in entry['shared_sources']:masks[ref['source']].add(k)
# Shared specials also borrow head tiles from other slim-body roster sprites.
for slot,name in [(1,'bret-hart'),(5,'razor-ramon'),(8,'shawn-michaels'),(10,'diesel'),(11,'owen-hart')]:
 wram=Path('/workspace/raw-analysis/roster-match-'+name+'/frame-001200-wram.bin')
 if not wram.exists()and slot==1:wram=Path('/workspace/raw-analysis/special-ready-v2-bret/frame-001450-wram.bin')
 other=catalog(a.rom.read_bytes(),wram.read_bytes(),slot)
 for f,g in zip(other,fs):
  if f['kind']!='primary'or f.get('common')or str(f['index'])not in own:continue
  l,t,r,b=own[str(f['index'])]['bounds'];pts,mapping=raster(f);common={ref['source']for part in f['parts']for ref in part['refs']}&{ref['source']for part in g['parts']for ref in part['refs']}
  for q,v in pts.items():
   if l<=q[0]<=r and t<=q[1]<=b:
    ref,k=mapping[q]
    if ref['source']not in common:masks[ref['source']].add(k)
anchors=json.loads((repo/'data/syxx-head-anchors.json').read_text())['heads']
for f in fs:
 if f['kind']!='primary'or str(f['index'])not in anchors:continue
 l,t,r,b=anchors[str(f['index'])]['bounds'];pts,mapping=raster(f)
 for q,v in pts.items():
  if l<=q[0]<=r and t<=q[1]<=b:
   ref,k=mapping[q];masks[ref['source']].add(k)
heads={}
for f in fs:
 if f['kind']!='primary'or not f.get('common'):continue
 pts,mapping=raster(f);matched={q:1 for q in pts if mapping[q][1]in masks.get(mapping[q][0]['source'],set())}
 counts={ref['field']:Counter(ref['pixels'])for part in f['parts']for ref in part['refs']}
 eligible={field for field,c in counts.items()if c[1]>=18 and sum(c[v]for v in[7,9,10,11,12,15])>=4 and sum(c[v]for v in[2,3,4,5])<=8}
 matched.update({q:1 for q in pts if mapping[q][0]['field']in eligible})
 hair={field for field,c in counts.items()if c[1]>=36 and sum(c[v]for v in[2,3,4,5])<=8}
 for q in pts:
  if mapping[q][0]['field']in hair and any(abs(q[0]-x)<=8 and abs(q[1]-y)<=8 for x,y in matched):matched[q]=1
 groups=components(matched,{1})
 if not groups:continue
 group=max(groups,key=len)
 if len(group)<35:continue
 l=min(x for x,y in group);r=max(x for x,y in group);t=min(y for x,y in group);b=max(y for x,y in group)
 if not(6<=r-l<=25 and 6<=b-t<=25):continue
 if sum(pts[q]in {1,6,8,13,14}for q in group)<6 or sum(pts[q]in {7,9,10,11,12,15}for q in group)<20:continue
 heads[str(f['index'])]={'bounds':[l,t,r,b],'matched_head_pixels':len(group)}
heads.update(anchors)
a.output.write_text(json.dumps({'version':1,'method':'Exact source-pixel identities from character-specific head artwork; largest connected matched region.','heads':heads},indent=2)+'\n');print('Mapped',len(heads),'shared head regions');print('Specials', {str(i):heads.get(str(i))for i in[698,699,701,706,830,831,832,839]})
