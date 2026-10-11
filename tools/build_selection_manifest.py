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
        'width':128,'height':120,
        'monitor_directory_offset':0x2FE35D+[4,1,10,7,9,6,0,11,5,8,2,3].index(selector)*4,
        'monitor_palette_directory_offset':0x2FE38D+[4,1,10,7,9,6,0,11,5,8,2,3].index(selector)*4,
        'announcer_monitor_word':0x2EE90F+selector*2,'announcer_monitor_bank':0x2EE927+selector*2,
        'announcer_palette_word':0x2EE93F+selector*2,'announcer_palette_bank':0x2EE957+selector*2,
        'monitor_offset':int.from_bytes(rom[record+20:record+23],'little')&0x3fffff,
        'monitor_palette_offset':int.from_bytes(rom[record+24:record+27],'little')&0x3fffff,
        'logo_offset':int.from_bytes(rom[record+8:record+11],'little')&0x3fffff,
        'logo_map_offset':int.from_bytes(rom[record+12:record+15],'little')&0x3fffff,
        'logo_palette_offset':int.from_bytes(rom[record+16:record+19],'little')&0x3fffff,
        'logo_tile_limit':len(decode_block(rom,int.from_bytes(rom[record+8:record+11],'little')&0x3fffff)[0])//32,
        'theme_offset':record+44,'theme':rom[record+44],
        'fields':{'name':record+28,'from':record+30,
        'weight':record+32,'height':record+36,'special':record+38}}
for meta in characters.values():
    pointer=rom[meta['record']+20:meta['record']+23]
    palette=rom[meta['record']+24:meta['record']+27]
    if rom[meta['monitor_directory_offset']:meta['monitor_directory_offset']+3]!=pointer or rom[meta['monitor_palette_directory_offset']:meta['monitor_palette_directory_offset']+3]!=palette:
        raise ValueError('Monitor directory differs')
    if rom[meta['announcer_monitor_word']:meta['announcer_monitor_word']+2]!=pointer[:2] or rom[meta['announcer_monitor_bank']]!=pointer[2] or rom[meta['announcer_palette_word']:meta['announcer_palette_word']+2]!=palette[:2] or rom[meta['announcer_palette_bank']]!=palette[2]:
        raise ValueError('Announcer monitor directory differs')
    if len(decode_block(rom,meta['monitor_offset'])[0])!=2304 or len(decode_block(rom,meta['logo_map_offset'])[0])!=2048:
        raise ValueError('Unexpected companion image size')
# Text uses a bank mirror where addresses below $8000 are not ROM.
free=[{'offset':0x2EFF49,'length':183}]
for region in free:
    if rom[region['offset']:region['offset']+region['length']]!=b'\xff'*region['length']:
        raise ValueError('Reserved text storage differs')
result={'characters':characters,'text_regions':free,'portrait_base':0x300000,'portrait_stride':0x4000,
    'monitor_base':0x330000,'monitor_stride':0x1000,
    'logo_base':0x340000,'logo_stride':0x8000,'font_offset':0x2ADBE3}
(Path(__file__).resolve().parents[1]/'editor/selection-layouts.js').write_text('window.RAW_SELECTION_MANIFEST = '+json.dumps(result,indent=2)+';\n')
