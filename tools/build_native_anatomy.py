"""Find native head regions using corresponding Nash/Syxx frame differences.

Publishes anatomical coordinates only, never extracted source pixels.
"""
from pathlib import Path
import argparse,json
from scott_frame_catalog import catalog,raster
from build_scott_hall_gear import components

def heads(nash,syxx):
 out={}
 for a,b in zip(nash,syxx):
  if a['kind']!='primary' or a.get('common'):continue
  p,_=raster(a);q,_=raster(b);diff={v:1 for v in p.keys()|q.keys() if p.get(v)!=q.get(v)}
  groups=components(diff,{1})
  if not groups:continue
  group=max(groups,key=len)
  if len(group)<12:continue
  hair=[q for q,v in p.items()if v==8]
  if hair:
   l=min(x for x,y in hair)-2;r=max(x for x,y in hair)+2;t=min(y for x,y in hair)-1;d=max(y for x,y in hair)+1
  else:
   l=min(x for x,y in group);r=max(x for x,y in group);t=min(y for x,y in group);d=max(y for x,y in group)
  if r-l>28 or d-t>28:continue
  shared={ref['source']for part in a['parts']for ref in part['refs']} & {ref['source']for part in b['parts']for ref in part['refs']}
  out[str(a['index'])]={'bounds':[l,t,r,d],'difference_pixels':len(group),'shared_sources':sorted(shared)}
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('nash_wram',type=Path);p.add_argument('syxx_wram',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rom=a.rom.read_bytes();result=heads(catalog(rom,a.nash_wram.read_bytes(),10),catalog(rom,a.syxx_wram.read_bytes(),9));a.output.write_text(json.dumps({'version':1,'method':'Largest connected difference between corresponding native Nash and Syxx primary frames; review bounds before authoring details.','heads':result},indent=2)+'\n');print('Located',len(result),'native head regions')
