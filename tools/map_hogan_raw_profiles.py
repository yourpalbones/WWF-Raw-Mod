"""Find exact complete Bret silhouette candidates for Raw-to-Genesis poses.

Recipes contain addresses, indices and translations only. Exact geometry is a
candidate, not proof that move timing/semantics match. No guessed fallback art.
"""
import argparse,json
from pathlib import Path
import scott_frame_catalog as raw
import genesis_royal_sprites as genesis
from compare_royal_raw_poses import silhouette


def candidates(rawrom,wram,segarom):
    frames={(f['kind'],f['index']):raw.raster(f)[0]for f in raw.catalog(rawrom,wram,1)}
    shapes={};genpoints={}
    # Geometric comparison preserves every nonzero source nibble, independent
    # of a palette remap that might make a gear color transparent.
    for i in range(genesis.POSE_COUNT):
        im,_=genesis.render_pose(segarom,3,i,bytes(range(256)))
        points={(x-96,y-128):v for y in range(im.height)for x in range(im.width)if(v:=im.getpixel((x,y)))}
        key=silhouette(points)
        if key:shapes.setdefault(key,[]).append(i);genpoints[i]=points
    component_shapes={};component_points={};parents={}
    for i in range(16,genesis.COMPONENT_COUNT):
        im,_=genesis.render_component(segarom,3,i,bytes(range(256)))
        points={(x,y):v for y in range(128)for x in range(128)if(v:=im.getpixel((x,y)))}
        component_points[i]=points
        key=silhouette(points)
        if key:component_shapes.setdefault(key,[]).append(i)
    for i in range(genesis.POSE_COUNT):
        for p in genesis.pose(segarom,i)['parts']:
            if not p.get('shadow'):parents.setdefault(p['component'],[]).append((i,p))
    records=[]
    for at in range(0x80000,0x90000,2):
        cursor=at;parts=[];body={};complete=False
        for _ in range(8):
            ident=int.from_bytes(rawrom[cursor:cursor+2],'little');cursor+=2
            if ident==65535:complete=True;break
            if ident==65534:break
            kind='secondary'if ident&32768 else'primary';offset=ident&32767
            if offset%3:break
            index=offset//3
            if (kind,index)not in frames:break
            dx,dy=rawrom[cursor:cursor+2];cursor+=2
            parts.append(dict(kind=kind,index=index,dx=dx-256 if dx&128 else dx,dy=dy-256 if dy&128 else dy))
        if not complete or not parts:continue
        for part in reversed(parts):
            if part['kind']=='secondary'and part['index']<32:continue
            for(x,y),value in frames[part['kind'],part['index']].items():body[x+part['dx'],y+part['dy']]=value
        if not body:continue
        matched=shapes.get(silhouette(body),[])
        if len(matched)==1:
            index=matched[0];other=genpoints[index]
            dx=min(x for x,y in body)-min(x for x,y in other)
            dy=min(y for x,y in body)-min(y for x,y in other)
            method='exact-composite';score=0.0
        else:
            evidence=[]
            for p in parts:
                if p['kind']!='primary':continue
                points=frames[p['kind'],p['index']]
                ids=component_shapes.get(silhouette(points),[])
                if len(ids)!=1 or len(points)<200:continue
                comp=ids[0];evidence.append((p,points,comp,{i for i,gp in parents.get(comp,[])}))
            if not evidence:continue
            possible=set.intersection(*(e[3]for e in evidence))
            if not possible:continue
            p,points,comp,_=max(evidence,key=lambda e:len(e[1]));other=component_points[comp]
            scored=[]
            for candidate in possible:
                gp=next(gp for i,gp in parents[comp]if i==candidate)
                tx=min(x for x,y in points)+p['dx']-min(x for x,y in other)-gp['dx']
                ty=min(y for x,y in points)+p['dy']-min(y for x,y in other)-gp['dy']
                translated={(x+tx,y+ty)for x,y in genpoints[candidate]}
                score=len(set(body)^translated)/max(1,len(set(body)|translated))
                scored.append((score,candidate,tx,ty))
            scored.sort()
            if scored[0][0]>.25 or(len(scored)>1 and scored[1][0]-scored[0][0]<.025):continue
            score,index,dx,dy=scored[0]
            method='exact-primary-component-inferred-pose'
        records.append(dict(raw_profile=0xc80000|(at&65535),source_pose=index,dx=dx,dy=dy,parts=parts,match=method,silhouette_difference=score))
    return dict(method='Exact full silhouettes plus explicitly labelled component-inferred geometry candidates',
                semantic_mapping_verified=False,source_worker=6,
                matched_raw_profiles=len(records),unique_source_poses=len({r['source_pose']for r in records}),records=records)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','wram','genesis'):p.add_argument(name,type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=candidates(a.raw.read_bytes(),a.wram.read_bytes(),a.genesis.read_bytes())
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='records'},indent=2))
