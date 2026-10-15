"""Replace Doink's graphics with a fully private donor-based Sting sprite set."""
import json,hashlib
from pathlib import Path
from scott_frame_catalog import catalog
from build_bret_gear import planar
from sting_rebuild_art import author

def build(base,wram,art=None,frames=None,palette=None):
    """art: the authoring function (default sting_rebuild_art.author); frames: the Undertaker donor catalog
    (default read with WRAM); palette: {index: BGR555} (default data/sting-palette.json)."""
    from build_nwo_gear import CONFIGS,programs,checksum
    c=CONFIGS[7]
    art=art or author
    frames=frames if frames is not None else catalog(base,wram,2)
    out=bytearray(base)+bytearray(b'\xff'*(0x800000-len(base)))
    for start,end in [(c['frames_start'],c['frames_end']),(c['packets_start'],c['packets_end']),
                      (c['pointers'],c['pointer_end']),(c['secondary_pointers'],c['secondary_pointer_end'])]:
        out[start:end]=b'\xff'*(end-start)
    for table,count in [(c['primary_table'],998),(c['secondary_table'],722)]:out[table:table+count*3]=bytes(count*3)
    cursors={'primary':0x600100,'secondary':0x610100}
    ends={'primary':0x610000,'secondary':0x620000}
    pointer_tables={'primary':c['pointers'],'secondary':c['secondary_pointers']}
    tile_maps={'primary':{},'secondary':{}};descriptor_maps={'primary':{},'secondary':{}}
    packet_cursor=c['packets_start'];rows=[];metadata=[];fingerprint=hashlib.sha256()
    for f in frames:
        changes=art(f);descriptor=bytearray(base[f['offset']:f['offset']+f['length']]);fields=[]
        kind=f['kind'];tiles=tile_maps[kind];ptr=pointer_tables[kind]
        for part in f['parts']:
            for ref in part['refs']:
                pixels=changes[ref['field']];raw=planar(pixels);fingerprint.update(planar(ref['pixels']))
                fields.append({'relative':ref['relative'],'source':ref['source'],'compressed':ref['compressed'],
                               'length':ref['length'],'edits':[[i,v]for i,v in enumerate(pixels)if v!=ref['pixels'][i]]})
                if raw not in tiles:
                    idx=len(tiles);assert idx<16384 and ptr+idx*3+3<=ptr+0xc000
                    if(packet_cursor&65535)+36>65536:packet_cursor=(packet_cursor+65535)&~65535
                    assert packet_cursor+36<=c['packets_end'],(kind,idx,hex(packet_cursor))
                    tiles[raw]=idx;out[packet_cursor:packet_cursor+32]=raw
                    out[ptr+idx*3:ptr+idx*3+3]=packet_cursor.to_bytes(3,'little')
                    metadata.append({'offset':packet_cursor,'original_offset':ref['source'],'original_compressed':ref['compressed'],
                                     'original_length':ref['length'],'length':36,'compressed':False,'namespace':kind})
                    packet_cursor+=36
                descriptor[ref['relative']:ref['relative']+2]=(0xc000|tiles[raw]).to_bytes(2,'little')
        fingerprint.update(base[f['offset']:f['offset']+f['length']])
        rows.append({'kind':kind,'index':f['index'],'offset':f['offset'],'length':f['length'],'tiles':fields})
        key=bytes(descriptor);descriptors=descriptor_maps[kind]
        if key not in descriptors:
            cursor=cursors[kind];assert cursor+len(key)<=ends[kind],(kind,'descriptor bank full')
            descriptors[key]=cursor;out[cursor:cursor+len(key)]=key;cursors[kind]+=len(key)
        address=descriptors[key];table=c['primary_table']if kind=='primary'else c['secondary_table']
        out[table+f['index']*3:table+f['index']*3+3]=address.to_bytes(3,'little')
    palette=palette or {int(k):v for k,v in json.loads((Path(__file__).resolve().parents[1]/'data/sting-palette.json').read_text()).items()}
    offset=0x2cc5ba
    for i,v in palette.items():out[offset+i*2:offset+i*2+2]=v.to_bytes(2,'little')
    out[c['signature_offset']:c['signature_offset']+len(c['signature'])]=c['signature'].encode()
    for p in programs():
        out[p['offset']:p['offset']+256]=b'\xff'*256;out[p['offset']:p['offset']+len(p['code'])]=bytes(p['code'])
        if'hook'in p:out[p['hook']:p['hook']+4]=bytes([0x5c,p['offset']&255,p['offset']>>8&255,p['offset']>>16])
    extra=[]
    for table in [0x2dd36f,0x2dd387,0x2dd39f,0x2dd3b7,0x2dd3cf,0x2dd3e7]:
        data=base[table+2:table+4];out[table+14:table+16]=data;extra.append({'offset':table+14,'code':list(data)})
    checksum(out)
    recipe={**c,'version':4,'selector':'7','donor_selector':2,'replacement':True,
            'materialize_all_tiles':True,'allow_outline_changes':True,'namespace_by_kind':True,
            'private_compressed':False,'source_fingerprint':fingerprint.hexdigest(),
            'palette_offset':offset,'palette':palette,'frames':rows,'programs':programs(),'extra_records':extra,
            'legacy_signatures':[{'offset':0x6ff000,'signature':'STING-NATIVE-GEAR3'},{'offset':0x6ff000,'signature':'STING-NATIVE-GEAR2'},{'offset':0x6cf000,'signature':'STING-NATIVE-GEAR1'}]}
    report={'selector':7,'donor_selector':2,'known_entries':len(frames),
            'private_tiles_by_kind':{k:len(v)for k,v in tile_maps.items()},'private_tiles':sum(map(len,tile_maps.values())),
            'every_tile_materialized':True,'tile_sources':metadata,'source_fingerprint':fingerprint.hexdigest(),
            'patched_sha256':hashlib.sha256(out).hexdigest()}
    return bytes(out),recipe,report
