"""Compare converted Hogan basic poses with native Raw OAM/VRAM captures.

This verifies visible source pixels and palette, not untested move coverage.
The caller must provide the read-only Hogan root observer log from the same run.
"""
import argparse,json
from pathlib import Path
from build_hogan_motion_probe import ROOTS,pack_objects
from genesis_royal_sprites import render_pose
from genesis_royal_graphics import color_lookup,snes_palette
from extract_oam import objects
from verify_hogan_genesis_capture import normalize


def check(genesis,trace,directory,legdrop=False,min_frame=0):
    requests=[r for r in map(json.loads,trace.read_text().splitlines())
              if r['pc']==0x4af300 and r['actor']==0 and r['selector']==26 and r['x']in((0xc8,0x4a)if legdrop else(0xc8,))]
    private_poses=list(ROOTS.values())+[115,57,58,475,476,477,478,479]
    sources={}
    for pose in set(private_poses if legdrop else ROOTS.values()):
        im,_=render_pose(genesis,6,pose,color_lookup(genesis))
        sources[pose]=(im,len(pack_objects(im)))
    rows=[];expected_palette=snes_palette(genesis)
    for file in sorted(directory.glob('*-oam.bin')):
        prefix=Path(str(file)[:-8]);frame=int(prefix.name[6:])
        if frame<min_frame:continue
        nearby=[r for r in requests if r['frame']<=frame][-4:]
        if not nearby:continue
        read=lambda suffix:Path(str(prefix)+'-'+suffix+'.bin').read_bytes()
        cgram=read('cgram');records=objects(read('vram'),read('oam'),cgram,read('registers')[0x2101])
        body=[(o,im)for o,im in records if o['palette']==0 and o['tile']<64 and o['y']<224]
        match=None
        for request in reversed(nearby):
            pose=ROOTS.get(request['a'],0)
            if request['x']==0x4a:
                index=(request['a']-0xc000)//10
                if not 0<=index<len(private_poses):continue
                pose=private_poses[index]
            source,count=sources[pose]
            if len(body)<count:continue
            native={}
            for obj,im in reversed(body[:count]):
                for y in range(im.height):
                    for x in range(im.width):
                        rgba=im.getpixel((x,y))
                        if rgba[3]:native[(obj['x']+x,obj['y']+y)]=rgba[:3]
            pixels={}
            for y in range(source.height):
                for x in range(source.width):
                    v=source.getpixel((x,y))
                    if not v:continue
                    color=int.from_bytes(expected_palette[v*2:v*2+2],'little')
                    pixels[(-x if body[0][0]['hflip']else x,y)]=tuple((color>>s&31)*255//31 for s in (0,5,10))
            if normalize(native)==normalize(pixels):match=dict(pose=pose,root=request['a'],pixels=len(native));break
        rows.append(dict(frame=frame,match=match,palette_exact=cgram[256:288]==expected_palette))
    return dict(frames_checked=len(rows),frames_exact=sum(r['match']is not None for r in rows),
                palettes_exact=sum(r['palette_exact']for r in rows),
                source_poses_verified=sorted({r['match']['pose']for r in rows if r['match']}),
                full_character_complete=False,finisher_verified=False,rows=rows)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('genesis','trace','captures'):p.add_argument(n,type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--min-frame',type=int,default=0,help='First gameplay snapshot; exclude explicitly paused/menu captures')
    p.add_argument('--legdrop',action='store_true',help='Include the separate experimental landing sequence')
    a=p.parse_args()
    result=check(a.genesis.read_bytes(),a.trace,a.captures,a.legdrop,a.min_frame);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='rows'},indent=2))
    if result['frames_exact']!=result['frames_checked']or not result['frames_checked']:raise SystemExit('Native frames need investigation')
