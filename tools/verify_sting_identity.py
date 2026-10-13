"""Check private ownership, emitted head landmarks and observed native tile use.

Small cropped faces may contain only part of the Crow grayscale plane. These
checks verify pixels and actual trace logs; they do not judge visual likeness.
"""
import argparse,json,copy
from pathlib import Path
from scott_frame_catalog import catalog,raster
from inspect_rom import tile
from build_nwo_gear import CONFIGS

def coordinates(value):
    if len(value)==2 and all(isinstance(v,int)for v in value):return [tuple(value)]
    return [tuple(q)for q in value]

def object_coverage(frame):
    return {(part['x']+x,part['y']+y)for part in frame['parts']
            for y in range(part['size'])for x in range(part['size'])}

def check_head(frame,points,atlas,palette):
    identifier=str(frame['index'])if frame['kind']=='primary'else 'secondary:'+str(frame['index'])
    assert identifier in atlas['heads'],('Finisher head lacks reviewed registration',identifier)
    entry=atlas['heads'][identifier];seed=atlas['templates'][entry['template']]
    sx,sy,dx,dy=entry['transform'];world=lambda q:(sx*q[0]+dx,sy*q[1]+dy)
    # Count only dedicated face gray slots in the actual authored head area.
    # Scorpion colors 6/8 elsewhere on the torso must not count as makeup.
    if seed.get('paint'):
        area={world(q)for q in seed['paint']}
    else:
        l,t,r,b=seed['box'];area={world((x,y))for y in range(t,b+1)for x in range(l,r+1)}
    grays={i for i in {4,5,13}if max(palette[i])-min(palette[i])<=20}
    visible=[v for q,v in points.items()if q in area and v in grays]
    assert len(visible)>=4,('Finisher head lost its visible grayscale makeup',identifier,len(visible))
    assert len(set(visible))>=2,('Finisher face collapsed to a single gray plane',identifier,visible)
    coverage=object_coverage(frame);occluded={world(q)for q in seed.get('occlusion',[])}
    landmarks={};checked=0
    for name in ['eyes','eye_pupils','nose','mouth']:
        rows=[]
        for q in coordinates(seed.get('landmarks',{}).get(name,[])):
            position=world(q);value=points.get(position,0)
            reason='foreground occlusion'if position in occluded else 'outside native OBJ coverage'if position not in coverage else None
            if reason is None:
                expected={1}if name in {'eyes','mouth'}else grays
                assert value in expected,('Emitted facial landmark differs',identifier,name,position,value,sorted(expected))
                checked+=1
            rows.append({'point':list(position),'palette_index':value,'verified':reason is None,**({'cropped_or_occluded':reason}if reason else{})})
        if rows:landmarks[name]=rows
    return {'template':entry['template'],'visible_face_gray_pixels':len(visible),
            'face_gray_palette_indices':sorted(set(visible)),'landmarks_checked':checked,'landmarks':landmarks}

p=argparse.ArgumentParser(description=__doc__);p.add_argument('original',type=Path);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('captures',type=Path);p.add_argument('grapples',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
original=a.original.read_bytes();rom=a.rom.read_bytes();c=CONFIGS[7];counts={};frames=catalog(original,a.wram.read_bytes(),2)
assert len(frames)==1720
atlas=json.loads((Path(__file__).resolve().parents[1]/'data/sting-rebuild-heads.json').read_text())
palette_words=[int.from_bytes(rom[0x2cc5ba+i*2:0x2cc5bc+i*2],'little')for i in range(16)]
palette=[tuple((v>>shift&31)*255//31 for shift in [0,5,10])for v in palette_words]
head_poses=[('primary',i)for i in [623,729,730,731,732,737,738]]+[('secondary',i)for i in [617,618,619,620,621,622,628]]
head_reports={}
for f in frames:
    kind=f['kind'];table=c['primary_table']if kind=='primary'else c['secondary_table'];pointer=c['pointers']if kind=='primary'else c['secondary_pointers']
    descriptor=int.from_bytes(rom[table+f['index']*3:table+f['index']*3+3],'little')
    assert descriptor>>16==(0x60 if kind=='primary'else 0x61)
    assert rom[descriptor:descriptor+2]==original[f['offset']:f['offset']+2]
    for part in f['parts']:
        for ref in part['refs']:
            ident=int.from_bytes(rom[descriptor+ref['relative']:descriptor+ref['relative']+2],'little')
            assert ident>=0xc000,'Original tile reference remained in the replacement'
            source=int.from_bytes(rom[pointer+(ident&0x3fff)*3:pointer+(ident&0x3fff)*3+3],'little')
            assert c['packets_start']<=source and source+32<=c['packets_end']
            ref['pixels']=tile(rom[source:source+32],0,4)
    if(kind,f['index'])in head_poses:
        head_reports[kind,f['index']]=check_head(f,raster(f)[0],atlas,palette)
        counts[kind,f['index']]=head_reports[kind,f['index']]['visible_face_gray_pixels']
calls=0;stock=[]
logs=[p for root in [a.captures/'actions',a.captures/'specials',a.grapples]for p in root.glob('*/tile_calls.jsonl')]
for log in logs:
    for line in log.read_text().splitlines():
        e=json.loads(line)
        if e['actor_slot']!=0:continue
        calls+=1
        if not(c['packets_start']<=e['source']<c['packets_end']and e['descriptor']>>16 in [0x60,0x61]and not e['compressed']):stock.append({'case':log.parent.name,'frame':e['frame'],'source':e['source'],'descriptor':e['descriptor']})
assert calls>0 and not stock,('Stock graphics fallback',stock[:8])
report={'all_1720_descriptors_fully_private':True,'native_sting_tile_requests':calls,'stock_graphics_fallbacks':0,
        'makeup_in_every_visible_deathlock_head':{f'{kind}:{index}':counts[kind,index]for kind,index in head_poses},
        'native_deathlock_head_landmarks':{f'{kind}:{index}':head_reports[kind,index]for kind,index in head_poses},
        'makeup_count_scope':'Dedicated face gray pixels inside reviewed head masks; excludes chest scorpion colors. Partial native faces are allowed.',
        'visual_likeness_verified':False,'complete_live_animation_coverage':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
