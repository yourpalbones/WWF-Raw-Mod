"""Check complete private ownership and makeup throughout the submitted move."""
import argparse,json,copy
from pathlib import Path
from scott_frame_catalog import catalog,raster
from inspect_rom import tile
from build_nwo_gear import CONFIGS

p=argparse.ArgumentParser(description=__doc__);p.add_argument('original',type=Path);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('captures',type=Path);p.add_argument('grapples',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
original=a.original.read_bytes();rom=a.rom.read_bytes();c=CONFIGS[7];counts={};frames=catalog(original,a.wram.read_bytes(),2)
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
    counts[kind,f['index']]=sum(v==5 for v in raster(f)[0].values())
head_poses=[('primary',i)for i in [623,729,730,731,732,737,738]]+[('secondary',i)for i in [617,618,619,620,621,622,628]]
for key in head_poses:assert counts[key]>=6,('Finisher head has no Crow makeup',key,counts[key])
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
        'complete_live_animation_coverage':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
