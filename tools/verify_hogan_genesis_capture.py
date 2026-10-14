"""Compare ROM-decoded Hogan composite pixels against native sprite memory.

This verifies source reconstruction, not an imported Raw character. Nearby
requests are considered because the VDP consumes queued sprite updates.
"""
import argparse
import json
from pathlib import Path
from genesis_royal_sprites import render_pose,pose,component
from genesis_sprite_capture import sprite_entries,object_pixels,word


def normalize(points):
    if not points:return {}
    left=min(x for x,y in points);top=min(y for x,y in points)
    return {(x-left,y-top):v for (x,y),v in points.items()}


def check(rom,trace,captures,actor):
    requests=[e for e in map(json.loads,trace.read_text().splitlines())
              if e['pc']==0x87ee and e['selector']==12 and e['a'][5]==actor]
    rows=[]
    for file in sorted(captures.glob('*-wram.bin')):
        prefix=Path(str(file)[:-len('-wram.bin')]);ram=file.read_bytes();tick=word(ram,0xd3ee)
        nearby=[e for e in requests if e['tick']<=tick][-4:]
        if not nearby:continue
        read=lambda suffix:Path(str(prefix)+'-'+suffix+'.bin').read_bytes()
        v,s,r=map(read,('vram','oam','registers'))
        entries=[o for o in sprite_entries(v,s,r)if actor*32<=o['tile']<(actor+2)*32 and o['palette']==3]
        match=None
        for request in reversed(nearby):
            index=(request['d'][0]&65535)//2
            record=pose(rom,index)
            count=sum(len(component(rom,6,p['component'])['objects'])for p in record['parts']if not p.get('shadow'))
            if len(entries)<count:continue
            native={}
            for obj in reversed(entries[:count]):
                values=object_pixels(v,obj)
                for y in range(obj['height']):
                    for x in range(obj['width']):
                        value=values[y*obj['width']+x]
                        if value:native[(obj['x']+x,obj['y']+y)]=value
            image,_=render_pose(rom,6,index,bytes.fromhex(request['lookup']))
            source={(x,y):image.getpixel((x,y))for y in range(image.height)for x in range(image.width)if image.getpixel((x,y))}
            if entries[0]['hflip']:source={(-x,y):v for (x,y),v in source.items()}
            if normalize(source)==normalize(native):
                match=dict(pose=index,source_request_tick=request['tick'],opaque_pixels=len(native),body_objects=count)
                break
        rows.append(dict(frame=int(prefix.name[6:]),tick=tick,match=match))
    return dict(source_worker=6,native_selector=12,actor=actor,frames_checked=len(rows),
                frames_exact=sum(bool(r['match'])for r in rows),rows=rows,
                raw_import_verified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path);p.add_argument('trace',type=Path);p.add_argument('captures',type=Path)
    p.add_argument('--actor',type=int,choices=(0,2),default=2)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=check(a.rom.read_bytes(),a.trace,a.captures,a.actor)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='rows'},indent=2))
    if report['frames_exact']!=report['frames_checked'] or not report['frames_checked']:
        raise SystemExit('Some source reconstruction frames need investigation')
