"""Wire the intermediate private Mr. Perfect graphics into Raw's thirteenth slot.

Development build only: Perfect-Plex and complete pose conversion remain required.
"""
import argparse
import json
from pathlib import Path
from build_nwo_gear import checksum,emit_address
from build_shawn_kick_prototype import Program


def hook_worker(secondary, native=True):
    p=Program();p.emit('08 48 da a6 36 bd 74 0b c9 18 00')
    p.branch('f0','perfect')
    # Chain through the current gear dispatcher for every existing wrestler.
    p.emit('fa 68 28')
    if native:emit_address(p,'5c',0x4be200 if secondary else 0x4be100)
    else:p.emit('7f 47 d5 ad 5c 1d ed 80'if secondary else'7f 13 d5 ad 5c c5 ec 80')
    p.label('perfect');p.emit('fa 68 c9 '+('76 08'if secondary else'b2 0b'))
    p.branch('b0','fallback');p.emit('48 da aa')
    table=0x711000 if secondary else 0x710000
    emit_address(p,'bf',table);p.emit('85 80');emit_address(p,'bf',table+2)
    p.emit('29 ff 00 85 82 fa 68 28 a5 80')
    p.emit('99 50 05 a5 82 99 52 05 5c 38 ed 80'if secondary else'99 4e 05 a5 82 99 50 05 c8 c8 5c e2 ec 80')
    p.label('fallback');p.emit('28 '+('7f 47 d5 ad 5c 1d ed 80'if secondary else'7f 13 d5 ad 5c c5 ec 80'))
    return p.finish()


def hook_lookup(native=True):
    p=Program();p.emit('48 a5 82 29 ff 00 c9 72 00');p.branch('90','old')
    p.emit('c9 76 00');p.branch('b0','old')
    p.emit('68 48 c9 00 c0');p.branch('90','stock')
    p.emit('68 29 ff 3f da 48 0a 18 63 01 aa 68 a5 82 29 ff 00 c9 74 00')
    p.branch('b0','secondary')
    for label,ptr in [('primary',0x7d0000),('secondary',0x7dc000)]:
        if label=='secondary':p.label(label)
        emit_address(p,'bf',ptr);p.emit('85 db e2 20');emit_address(p,'bf',ptr+2)
        p.emit('85 dd c2 20 fa a9 01 00 6b')
    p.label('stock');p.emit('68 cf 48 0f 00 5c e8 f6 ac')
    p.label('old');p.emit('68')
    if native:emit_address(p,'5c',0x4be000)
    else:p.emit('cf 48 0f 00 5c e8 f6 ac')
    return p.finish()


def build(base,cgram,original=None,portrait=None):
    if len(base)!=0x800000:raise ValueError('Requires eight-MiB private graphics staging')
    native=base[0xecc1:0xecc5]==bytes.fromhex('5c 00 e1 4b')
    if not native and base[0xecc1:0xecc5]!=bytes.fromhex('7f 13 d5 ad'):
        raise ValueError('Unsupported existing sprite dispatcher')
    out=bytearray(base);changes=[]
    def write(at,expected,new):
        if base[at:at+len(expected)]!=expected:raise ValueError(f'Unexpected hook at {at:06x}')
        out[at:at+len(new)]=new
        changes.append({'offset':at,'before':expected.hex(),'after':new.hex()})
    # Guard a separate configuration bank; graphics are already in 71..7D.
    if any(v!=255 for v in base[0x708000:0x710000]):raise ValueError('Configuration region occupied')
    profiles=bytearray(base[0x2efaf5:0x2efd11]);profiles+=profiles[45:90]
    out[0x708000:0x708000+len(profiles)]=profiles
    helper=bytes.fromhex('a2 2d 00 22 5f ff ad 18 69 f5 fa aa f4 fa ae ab ab 60')
    at=base.index(helper)
    write(at+9,bytes.fromhex('f5 fa'),bytes.fromhex('00 80'))
    write(at+13,bytes.fromhex('fa ae'),bytes.fromhex('80 70'))
    write(0x2afe99,b'\xae',b'\x70')
    for field in [40,41,42,43]:
        old=0x2efaf5+field|0x800000
        at=base.index(b'\xbf'+old.to_bytes(3,'little'),0x2afebc,0x2aff20)
        write(at+1,old.to_bytes(3,'little'),(0x708000+field).to_bytes(3,'little'))
    # The thirteenth attribute entries already exist. Assign their values in the
    # reserved initializer, without running a fourteenth write into the next array.
    attr=profiles[12*45+40:12*45+44]
    values=[(-((attr[0]-6)*4))&65535,attr[2]+4,attr[1],attr[3]]
    tail=base.index(bytes.fromhex('a9 f0 ff 99 36 0e a9 0e 00 99 50 0e'),0x2afebc,0x2aff30)
    for delta,value in zip([1,7,13,19],values):write(tail+delta,base[tail+delta:tail+delta+2],value.to_bytes(2,'little'))
    write(0x19d43f,b'\x0c',b'\x0d')
    back=base.index(bytes.fromhex('a9 0b 00'),0x19d420,0x19d440)
    write(back+1,b'\x0b',b'\x0c')
    # The palette copier uses (directory value + 4) * 16, then adds C49A.
    # Keep the 64-byte prefix and all twelve edited palettes exactly intact.
    out[0x70e800:0x70ea60]=base[0x2cc49a:0x2cc6fa]
    out[0x70e9c0:0x70e9e0]=cgram[320:352]
    write(0x2cf212,bytes.fromhex('9a c4'),bytes.fromhex('00 e8'))
    write(0x2cf218,b'\xac',b'\x70')
    # Extend all six signature arrays. Index twelve is deliberately disabled
    # until the actual Perfect-Plex action is implemented, never assigned Bret's.
    for n,old in enumerate([0x2dd36f,0x2dd387,0x2dd39f,0x2dd3b7,0x2dd3cf,0x2dd3e7]):
        new=0x708600+n*32
        out[new:new+24]=base[old:old+24];out[new+24:new+26]=bytes(2)
        addresses=[]
        for bank in [0x80,0xc0]:
            pattern=(old|bank<<16).to_bytes(3,'little');cursor=0
            while True:
                cursor=base.find(pattern,cursor,0x300000)
                if cursor<0:break
                if base[cursor-1]in [0xbf,0x7f,0xff]:addresses.append(cursor)
                cursor+=1
        if not addresses:raise ValueError(f'No references to {old:06x}')
        for address in addresses:write(address,base[address:address+3],new.to_bytes(3,'little'))
    for offset,code,hook,expected in [(0x70f000,hook_worker(False,native),0xecc1,bytes.fromhex('5c 00 e1 4b'if native else'7f 13 d5 ad')),
                                     (0x70f100,hook_worker(True,native),0xed19,bytes.fromhex('5c 00 e2 4b'if native else'7f 47 d5 ad')),
                                     (0x70f200,hook_lookup(native),0x2cf6e4,bytes.fromhex('5c 00 e0 4b'if native else'cf 48 0f 00'))]:
        out[offset:offset+len(code)]=code
        write(hook,expected,b'\x5c'+offset.to_bytes(3,'little'))
    magic=b'PERFECT-SLOT-PROTO1'
    out[0x70fe00:0x70fe00+len(magic)]=magic
    assets=None
    if original is not None and portrait is not None:
        from perfect_profile_assets import configure
        assets=configure(out,original,portrait)
    checksum(out)
    return out,{'development_only':True,'perfect_plex_imported':False,
                'assets':assets,'profile_table':0x708000,'changes':changes,'slot':12,
                'known_remaining':['portrait/name/monitor assets','ordinary move table audit',
                                   'remaining donor poses','Perfect-Plex action and pin','AI and match variants']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('cgram',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--original',type=Path);p.add_argument('--portrait',type=Path);a=p.parse_args()
    out,report=build(a.base.read_bytes(),a.cgram.read_bytes(),a.original.read_bytes() if a.original else None,a.portrait)
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'perfect-slot-prototype.sfc').write_bytes(out)
    (a.output/'slot-report.json').write_text(json.dumps(report,indent=2)+'\n')
