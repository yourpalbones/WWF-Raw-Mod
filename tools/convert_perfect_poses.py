"""Convert Royal source poses into private Raw descriptors for the new slot.

Exact Bret silhouette correspondence supplies Royal donor pose IDs. Unmatched
Raw actions retain explicitly reported donor geometry until their conversion is
verified. This intermediate build must not be advertised as a completed port.
"""
import argparse
import hashlib
import json
from pathlib import Path
import royal_rumble_sprites as royal
import scott_frame_catalog as raw
from compare_royal_raw_poses import silhouette
from build_bret_gear import planar
from decode_sprite_tile import encode_sprite_tile


def minimum(points):
    return (min(x for x, y in points), min(y for x, y in points)) if points else (0, 0)


def convert(raw_rom, raw_wram, royal_rom, royal_wram):
    source = royal.catalog(royal_rom, royal_wram, 1)
    bret = royal.catalog(royal_rom, royal_wram, 3)
    shapes = {}
    for frame in bret:
        if frame['index'] >= 16:
            shapes.setdefault(silhouette(royal.raster(frame)), []).append(frame)
    result = []
    for frame in raw.catalog(raw_rom, raw_wram, 1):
        points, _ = raw.raster(frame)
        candidates = shapes.get(silhouette(points), []) if points else []
        # Ambiguous shapes are not automatically treated as semantic matches.
        donor = candidates[0] if len(candidates) == 1 and not frame['common'] else None
        if donor:
            target = source[donor['index']]
            left, top = minimum(points)
            dl, dt = minimum(royal.raster(donor))
            parts = [{**part, 'x': part['x'] + left - dl,
                      'y': part['y'] + top - dt} for part in target['parts']]
        else:
            # Palette-index adaptation only; preserves Raw action geometry.
            # These frames are called out as incomplete conversion in the report.
            colors = {0:0, 1:1, 2:4, 3:8, 4:4, 5:8, 6:13, 7:2,
                      8:14, 9:7, 10:6, 11:3, 12:2, 13:15, 14:14, 15:11}
            parts = []
            for part in frame['parts']:
                refs = [{**ref, 'pixels': [colors[v] for v in ref['pixels']]} for ref in part['refs']]
                parts.append({**part, 'refs': refs})
        result.append({'kind': frame['kind'], 'index': frame['index'], 'parts': parts,
                       'royal_index': donor['index'] if donor else None,
                       'common': frame['common']})
    return result


def write_private(base, frames):
    out = bytearray(base)
    regions = [(0x710000,0x712000),(0x720000,0x750000),(0x750000,0x7d0000),(0x7d0000,0x7e0000)]
    for start,end in regions:
        if any(v != 255 for v in base[start:end]):
            raise ValueError(f'Private space is occupied: {start:06x}')
    tables = {'primary':0x710000,'secondary':0x711000}
    cursors = {'primary':0x720100,'secondary':0x740100}
    pointer_tables = {'primary':0x7d0000,'secondary':0x7dc000}
    tile_maps = {'primary':{},'secondary':{}}
    descriptors = {'primary':{},'secondary':{}}
    packet = 0x750000
    for kind,count in [('primary',998),('secondary',722)]:
        out[tables[kind]:tables[kind]+count*3] = bytes(count*3)
    for frame in frames:
        kind = frame['kind']
        parts=sorted(frame['parts'],key=lambda p:-p['size'])
        if not parts:
            # The native object loop cannot represent zero; emit an invisible tile.
            parts=[{'x':0,'y':0,'size':8,'hflip':False,'vflip':False,
                    'refs':[{'pixels':[0]*64}]}]
        before=raw.raster({'parts':frame['parts']})[0]
        after=raw.raster({'parts':parts})[0]
        if before!=after:
            raise ValueError(f"Mixed Royal OBJ order changes pixels: {kind}/{frame['index']}")
        pieces=[]
        for part in parts:
            size=part['size'];x,y=part['x'],part['y']
            if not -64<=x<64 or not -105<=y<23:
                raise ValueError(f"Unrepresentable coordinate: {kind}/{frame['index']} {x},{y}")
            entry=bytearray([0,x&127,(y+105)&127])
            for ty in range(size//8):
                for tx in range(size//8):
                    pixels=[]
                    for py in range(8):
                        for px in range(8):
                            sx,sy=tx*8+px,ty*8+py
                            if part['hflip']:sx=size-1-sx
                            if part['vflip']:sy=size-1-sy
                            ref=part['refs'][(sy//8)*(size//8)+sx//8]
                            pixels.append(ref['pixels'][(sy%8)*8+sx%8])
                    encoded=planar(pixels);tiles=tile_maps[kind]
                    if encoded not in tiles:
                        index=len(tiles);ptr=pointer_tables[kind]+index*3
                        if index>=16384:raise ValueError('Private tile namespace exhausted')
                        payload=encode_sprite_tile(encoded)
                        if (packet&65535)+len(payload)>65536:packet=(packet+65535)&~65535
                        if packet+len(payload)>0x7d0000:raise ValueError('Private tile region exhausted')
                        tiles[encoded]=index;out[packet:packet+len(payload)]=payload
                        out[ptr:ptr+3]=packet.to_bytes(3,'little');packet+=len(payload)
                    entry+=(0xc000|tiles[encoded]).to_bytes(2,'little')
            pieces.append(entry)
        if len(pieces)>64:raise ValueError('OBJ count overflow')
        descriptor=bytes([len(pieces),sum(p['size']==16 for p in parts)])+b''.join(pieces)
        if descriptor not in descriptors[kind]:
            address=cursors[kind]
            if (address & 65535)+len(descriptor)>65536:address=(address+65535)&~65535
            if address+len(descriptor)>(0x740000 if kind=='primary' else 0x750000):
                raise ValueError('Descriptor bank exhausted')
            descriptors[kind][descriptor]=address
            out[address:address+len(descriptor)]=descriptor
            cursors[kind]+=len(descriptor)
        address=descriptors[kind][descriptor]
        at=tables[kind]+frame['index']*3
        out[at:at+3]=address.to_bytes(3,'little')
    report={'private_tiles':{k:len(v)for k,v in tile_maps.items()},
            'royal_candidates_converted':sum(f['royal_index'] is not None for f in frames),
            'raw_donor_geometry_remaining':sum(f['royal_index'] is None for f in frames),
            'complete_port':False,'packet_end':packet,
            'pose_map':[{k:f[k]for k in ['kind','index','royal_index','common']}for f in frames]}
    return out,report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['base','raw_rom','raw_wram','royal_rom','royal_wram']:p.add_argument(name,type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();frames=convert(*(getattr(a,n).read_bytes()for n in ['raw_rom','raw_wram','royal_rom','royal_wram']))
    out,report=write_private(a.base.read_bytes(),frames)
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'private-perfect.sfc').write_bytes(out)
    (a.output/'conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='pose_map'})
