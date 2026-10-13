"""Recover paired Royal receiving poses and component anchors from native OAM.

The output contains only geometry and source addresses. Pixel data remains in
the user's ROM. Every Undertaker receiving frame must match the native capture.
"""
import argparse
import json
from collections import Counter
from pathlib import Path
import royal_rumble_sprites as royal
from build_bret_gear import planar
from extract_oam import objects
from import_perfect_plex import actor_pixels


def build(rom, wram, captures, trace):
    catalog = royal.catalog(rom, wram, 2)
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    rows = []
    for frame in range(56,145,8):
        indices = [row['part_index']//2 for row in events
                   if row['frame']==frame-7 and row['actor']==2 and row['pc']==0x80d50e]
        atlas = {}
        for ident in indices:
            for part in catalog[ident]['parts']:
                key = (part['size'], b''.join(planar(ref['pixels']) for ref in part['refs']))
                atlas.setdefault(key, []).append((ident, part))
        prefix = captures/f'frame-{frame:06d}'
        read = lambda name: Path(str(prefix)+'-'+name+'.bin').read_bytes()
        vram, oam, cgram, regs = (read(name) for name in ('vram','oam','cgram','registers'))
        obsel = regs[0x2101]
        base, select = (obsel&3)<<14, ((obsel>>3)&3)<<13
        candidates = []
        for record, image in objects(vram, oam, cgram, obsel):
            if record['palette']!=3 or not image.getbbox():
                continue
            raw = bytearray()
            number, attr = record['tile']&255, oam[record['index']*4+3]
            for y in range(record['size']//8):
                for x in range(record['size']//8):
                    tile = ((number&240)+y*16+((number+x)&15))&255
                    address = (base+(select+8192 if attr&1 else 0)+tile*32)&65535
                    raw += vram[address:address+32]
            matches = atlas.get((record['size'], bytes(raw)), [])
            if not matches:
                raise ValueError(f'Missing native receiving object: {frame}/{record["index"]}')
            options=set()
            for ident,part in matches:
                x=record['x']+(part['x']+part['size'] if record['hflip'] else -part['x'])
                y=record['y']+(part['y']+part['size'] if record['vflip'] else -part['y'])
                options.add((ident,x,y,record['hflip'],record['vflip']))
            candidates.append(options)
        votes=Counter(anchor for options in candidates for anchor in options)
        anchors=Counter()
        for options in candidates:
            best=max(votes[anchor]for anchor in options)
            winners=[anchor for anchor in options if votes[anchor]==best]
            if len(winners)!=1:raise ValueError(f'Ambiguous component anchor at {frame}')
            anchors[winners[0]]+=1
        components = [{'pose':ident,'x':x,'y':y,'hflip':h,'vflip':v}
                      for ident,x,y,h,v in anchors]
        if len(components)!=len(indices):
            raise ValueError(f'Inconsistent source component anchors at frame {frame}')
        rows.append({'source_frame':frame,'components':components})

    workers = []
    for selector in range(12):
        source = royal.catalog(rom, wram, selector)
        poses = []
        for row in rows:
            parts, points = [], {}
            for component in row['components']:
                for part in source[component['pose']]['parts']:
                    size = part['size']
                    x = component['x']+(-part['x']-size if component['hflip'] else part['x'])
                    y = component['y']+(-part['y']-size if component['vflip'] else part['y'])
                    refs = [[r['source'],int(r['compressed']),r['length']] for r in part['refs']]
                    parts.append({'x':x-145,'y':y-162,'size':size,
                                  'hflip':component['hflip'],'vflip':component['vflip'],'refs':refs})
            # Match the native OAM order: earlier components and objects win.
            for component in reversed(row['components']):
                for part in reversed(source[component['pose']]['parts']):
                    size = part['size']
                    left = component['x']+(-part['x']-size if component['hflip'] else part['x'])
                    top = component['y']+(-part['y']-size if component['vflip'] else part['y'])
                    for y in range(size):
                        for x in range(size):
                            sx = size-1-x if component['hflip'] else x
                            sy = size-1-y if component['vflip'] else y
                            value = part['refs'][(sy//8)*(size//8)+sx//8]['pixels'][sy%8*8+sx%8]
                            if value: points[left+x,top+y] = value
            if selector==2 and points!=actor_pixels(captures/f'frame-{row["source_frame"]:06d}',3):
                raise ValueError(f'Receiver reconstruction differs from native pixels: {row["source_frame"]}')
            poses.append({'source_frame':row['source_frame'],'parts':parts,
                          'bbox':[min(x for x,y in points)-145,min(y for x,y in points)-162,
                                  max(x for x,y in points)-145,max(y for x,y in points)-162]})
        workers.append({'selector':selector,'poses':poses})
    return {'method':'Native Royal receiving pose IDs and OAM component anchors',
            'native_undertaker_frames_verified':12,'components':rows,'workers':workers}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','wram','captures','trace'):parser.add_argument(name,type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=build(args.rom.read_bytes(),args.wram.read_bytes(),args.captures,args.trace)
    args.output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('Native receiving frames verified:',result['native_undertaker_frames_verified'])
    print('Royal workers mapped:',len(result['workers']))
