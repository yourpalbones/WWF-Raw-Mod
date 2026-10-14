"""Experimental contextual-R leg-drop route. Must pass native gameplay checks.

Keeps the opponent's native downed pose; does not borrow another identity's art.
The automatic source rope run is not implemented, so this is an animation test.
"""
import argparse,json
from pathlib import Path
from PIL import Image
from build_hogan_motion_probe import ROOTS,compile_motion
from build_hogan_slot_probe import build
from genesis_royal_graphics import u16
from build_shawn_kick_prototype import Program
from build_nwo_gear import emit_address,checksum


def sequence_hook():
    p=Program();p.emit('08 48 da 5a a6 36 bd 74 0b c9 1a 00');p.branch('d0','old')
    p.emit('bd 26 05 c9 04 00');p.branch('b0','old')
    p.emit('a5 44 c9 8c 00');p.branch('d0','old')
    p.emit('bd ec 0b c9 04 00');p.branch('d0','old')
    p.emit('a5 48');p.branch('d0','not_start')
    p.emit('a9 00 00');emit_address(p,'8f',0x7ee080)
    p.label('not_start');p.emit('a5 48 c9 31 00');p.branch('90','play')
    emit_address(p,'af',0x7ee080);p.branch('d0','end_check')
    p.emit('bd fc 0a c9 0c 00');p.branch('b0','end_check')
    p.emit('aa a9 56 00 22 9d f8 80 a9 01 00 9d d8 0a');emit_address(p,'8f',0x7ee080)
    p.label('end_check');p.emit('a5 48 c9 3f 00');p.branch('90','play')
    p.emit('a6 36 9e ec 0b 9e 2c 0b')
    p.label('play');p.emit('a5 48 18 69 00 d0 85 7c a9 4a 00 85 7e 7a fa 68 28 5c 80 f0 80')
    p.label('old');p.emit('7a fa 68 28');emit_address(p,'5c',0x4af500);return p.finish()


def build_test(base,genesis,stock,portrait):
    pos=0xbb792+u16(genesis,0xbb792+0x170);rows=[]
    while u16(genesis,pos)!=65535:
        rows.append((u16(genesis,pos)//2,genesis[pos+2:pos+6]));pos+=6
    old=dict(ROOTS)
    try:
        for i,pose in enumerate(dict.fromkeys(p for p,data in rows)):ROOTS[0xf000+i*2]=pose
        probe,_=build(base,genesis,stock,portrait);out,report=compile_motion(probe,genesis)
        poses=list(ROOTS.values());sequence=bytearray()
        for pose,data in rows:
            profile=0xc000+poses.index(pose)*10
            sequence+=bytes([0x4a])+profile.to_bytes(2,'little')+data
        sequence+=b'\xff'*7
        out[0x4ad000:0x4ad000+len(sequence)]=sequence
        code=sequence_hook();out[0x4af600:0x4af600+len(code)]=code
        out[0xf073:0xf077]=b'\x5c'+(0x4af600).to_bytes(3,'little')
        for n,value in enumerate((0,140,70,266,34,4)):
            out[0x708600+n*32+26:0x708602+n*32+26]=value.to_bytes(2,'little')
        checksum(out);out[0x400000:0x410000]=out[:65536]
        report.update(finisher_disabled=False,finisher_verified=False,
                      finisher_action=140,automatic_rope_run=False,source_finisher_poses=[p for p,data in rows])
        return out,report
    finally:ROOTS.clear();ROOTS.update(old)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','genesis','stock','portrait'):p.add_argument(n,type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out,report=build_test(a.base.read_bytes(),a.genesis.read_bytes(),a.stock.read_bytes(),Image.open(a.portrait))
    a.output.write_bytes(out);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='poses'},indent=2))
