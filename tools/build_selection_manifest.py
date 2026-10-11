"""Publish address-only selection records; never publish ROM portrait/text bytes."""
import argparse
import hashlib
import json
from pathlib import Path
from build_bret_gear import ORIGINAL_HASH
from decode_graphics import decode_block

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('rom',type=Path)
args=parser.parse_args()
rom=args.rom.read_bytes()
if hashlib.sha256(rom).hexdigest()!=ORIGINAL_HASH:
    raise ValueError('Requires original USA ROM')
characters={}
for selector in range(12):
    record=0x2EFAF5+selector*45
    portrait=int.from_bytes(rom[record:record+3],'little')&0x3fffff
    palette=int.from_bytes(rom[record+4:record+7],'little')&0x3fffff
    decoded,meta=decode_block(rom,portrait)
    if len(decoded)!=15360:
        raise ValueError('Unexpected portrait size')
    characters[str(selector)]={'record':record,'portrait_offset':portrait,
        'portrait_length':meta['compressed_size'],'palette_offset':palette+64,
        'width':128,'height':120,'fields':{'name':record+28,'from':record+30,
        'weight':record+32,'height':record+36,'special':record+38}}
# Text uses a bank mirror where addresses below $8000 are not ROM.
free=[{'offset':0x2EFF49,'length':183}]
for region in free:
    if rom[region['offset']:region['offset']+region['length']]!=b'\xff'*region['length']:
        raise ValueError('Reserved text storage differs')
result={'characters':characters,'text_regions':free,'portrait_base':0x300000,'portrait_stride':0x4000}
(Path(__file__).resolve().parents[1]/'editor/selection-layouts.js').write_text('window.RAW_SELECTION_MANIFEST = '+json.dumps(result,indent=2)+';\n')
