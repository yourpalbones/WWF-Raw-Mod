"""Register authored Sting head masks to repeated donor drawings and reflections."""
import argparse,json,hashlib
from collections import Counter
from pathlib import Path
from scott_frame_catalog import catalog,raster
from build_bret_gear import planar
SKIN={7,9,10,11,12,15}
from sting_rebuild_art import SCORPION

def register(rom,wram,seeds):
    frames=catalog(rom,wram,2);by_id={(f['kind'],f['index']):f for f in frames};templates={}
    for key,seed in seeds.items():
        pts,_=raster(by_id[seed.get('kind','primary'),seed['piece']]);l,t,r,b=seed.get('match_box',seed['box'])
        templates[key]={q:v for q,v in pts.items()if l<=q[0]<=r and t<=q[1]<=b}
    # A native face is often assembled from shared tiles even when its complete
    # crop differs. Carry only reviewed head pixels into exact matching tiles;
    # never propagate added hair into the universally shared empty tile.
    tile_masks={}
    for key,seed in seeds.items():
        frame=by_id[seed.get('kind','primary'),seed['piece']];points,mapping=raster(frame);paint={}
        l,t,r,b=seed['box']
        for q,v in points.items():
            colors={1,9,10,12}if seed.get('hair_only')else SKIN|{1}
            if l<=q[0]<=r and t<=q[1]<=b and v in colors:paint[q]=1 if v in {1,9,10}else 14
        for field,value in [('face',5),('face_shadow',13),('eyes',1),('cheeks',1),('mouth',1),('nose',13)]:
            for q in seed.get(field,[]):
                if tuple(q)in points:paint[tuple(q)]=value
        for q,value in paint.items():
            ref,k=mapping[q];digest=hashlib.sha256(planar(ref['pixels'])).hexdigest()
            mask=tile_masks.setdefault(digest,{})
            # The first independently reviewed drawing is canonical for a
            # shared native tile; full registered heads override this fallback.
            mask.setdefault(str(k),value)
    heads={}
    for frame in frames:
        points,_=raster(frame);by_value={}
        for q,v in points.items():by_value.setdefault(v,[]).append(q)
        matches=[]
        for key,template in templates.items():
            # Spatially spread feature anchors make exact translation search
            # cheap. The complete head mask is checked before accepting it.
            items=list(template.items());anchors=items[::max(1,len(items)//12)][:14]
            for sx,sy in [(1,1),(-1,1),(1,-1),(-1,-1)]:
                votes=Counter((x-sx*tx,y-sy*ty)for(tx,ty),v in anchors for x,y in by_value.get(v,[]))
                for(dx,dy),count in votes.most_common(4):
                    if count<5:continue
                    exact=sum(points.get((sx*x+dx,sy*y+dy))==v for(x,y),v in template.items())
                    shape=all(points.get((sx*x+dx,sy*y+dy))in SKIN if v in SKIN else points.get((sx*x+dx,sy*y+dy))==v for(x,y),v in template.items())
                    if shape and exact>=len(template)*.82:
                        matches.append((exact,len(template),key,[sx,sy,dx,dy]))
        direct=[m for m in matches if seeds[m[2]].get('kind','primary')==frame['kind'] and seeds[m[2]]['piece']==frame['index'] and m[3]==[1,1,0,0]]
        if direct:matches=direct
        if matches:
            matches.sort(key=lambda m:(-m[0],-m[1],m[2],m[3]));exact,size,key,transform=matches[0]
            identifier=str(frame['index'])if frame['kind']=='primary'else 'secondary:'+str(frame['index'])
            heads[identifier]={'template':key,'transform':transform,'matched_pixels':exact,'template_pixels':size}
    return {'version':1,'donor_selector':2,'method':'Specific native head drawings matched under translation/reflection; at least 82% exact shades and every non-skin feature preserved. Exact tile hashes additionally carry authored head pixels.','templates':seeds,'heads':heads,'tile_masks':tile_masks}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('--seeds',type=Path,default=Path(__file__).resolve().parents[1]/'data/sting-head-seeds.json');p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'data/sting-rebuild-heads.json');a=p.parse_args();r=register(a.rom.read_bytes(),a.wram.read_bytes(),json.loads(a.seeds.read_text()));a.output.write_text(json.dumps(r,indent=2)+'\n');print('Registered',len(r['heads']),'Sting head drawings')
