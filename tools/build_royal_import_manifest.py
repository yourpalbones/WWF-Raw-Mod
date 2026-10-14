"""Publish address/geometry recipes for local Royal-to-Raw import; no game pixels."""
import argparse,json
from pathlib import Path
from PIL import Image
import royal_rumble_sprites as royal
from convert_perfect_poses import convert
from extract_oam import objects
from build_bret_gear import planar
from import_perfect_plex import actor_pixels,init_hook,sequence_hook
from build_perfect_slot import hook_worker,hook_lookup
from build_shawn_superkick_animation import pack


def reference(ref):return [ref['source'],int(ref['compressed']),ref['length']]


def frame_rows(frames):
    """Manifest rows. 'royal' rows read Royal Perfect tiles; 'replaces' is the hash of the adapted piece a
    matched row supersedes (an upgrade only replaces a piece that still has exactly that content)."""
    rows=[]
    for f in frames:
        row={'kind':f['kind'],'index':f['index'],'royal':f['royal_index'] is not None,
             'common':f['common'],'parts':[{'x':p['x'],'y':p['y'],'size':p['size'],
             'hflip':p['hflip'],'vflip':p['vflip'],'refs':[reference(r)for r in p['refs']]}for p in f['parts']]}
        if f.get('source')=='matched':row['replaces']=f['replaces_hash']
        rows.append(row)
    return rows


def coverage(rows):
    return {'royal_poses':sum(r['royal']for r in rows),'adapted_raw_poses':sum(not r['royal']for r in rows),
            'matched_royal_poses':sum('replaces' in r for r in rows)}


def build(raw_rom,raw_wram,royal_rom,royal_wram,captures,matches=None):
    frames=convert(raw_rom,raw_wram,royal_rom,royal_wram,matches)
    rows=frame_rows(frames)
    atlas={bytes(32):None}
    for frame in royal.catalog(royal_rom,royal_wram,1):
        for part in frame['parts']:
            for ref in part['refs']:atlas.setdefault(planar(ref['pixels']),reference(ref))
    finisher=[]
    for frame in range(56,145,8):
        prefix=captures/f'frame-{frame:06d}'
        def read(n):return Path(str(prefix)+'-'+n+'.bin').read_bytes()
        v,o,c,regs=(read(n)for n in('vram','oam','cgram','registers'));obsel=regs[0x2101]
        base=(obsel&3)<<14;select=((obsel>>3)&3)<<13;parts=[]
        for rec,_ in objects(v,o,c,obsel):
            if rec['palette']!=2:continue
            n=rec['tile']&255;attr=o[rec['index']*4+3];refs=[]
            for y in range(rec['size']//8):
                for x in range(rec['size']//8):
                    number=((n&0xf0)+y*16+((n+x)&15))&255
                    a=(base+(select+8192 if attr&1 else 0)+number*32)&65535
                    raw=v[a:a+32]
                    if raw not in atlas:raise ValueError('Captured finisher tile has no verified Royal source')
                    refs.append(atlas[raw])
            parts.append({'x':rec['x']-145,'y':rec['y']-162,'size':rec['size'],
                          'hflip':rec['hflip'],'vflip':rec['vflip'],'refs':refs})
        image=Image.new('P',(112,112))
        for (x,y),value in actor_pixels(prefix,2).items():image.putpixel((145-x+56,y-162+100),value)
        choices=[o for o in pack(image,112)if o[0][0]+2<=17 and o[0][1]+4<=64]
        (count,cost),chunks=min(choices,key=lambda o:(o[0][1],o[0][0]))
        finisher.append({'source_frame':frame,'parts':parts,'chunks':[[x-56,y-100,size]for x,y,size,pixels in sorted(chunks,key=lambda c:-c[2])]})
    def worker(secondary,native):
        code=hook_worker(secondary,native)
        return code.replace(bytes.fromhex('c9 76 08'),bytes.fromhex('c9 7f 08'))if secondary else code.replace(bytes.fromhex('c9 b2 0b'),bytes.fromhex('c9 dc 0b'))
    def lookup(native):
        code=hook_lookup(native)
        for before,after in [(0x7dc000,0x749800),(0x7dc002,0x749802)]:code=code.replace(before.to_bytes(3,'little'),after.to_bytes(3,'little'))
        return code
    programs={}
    for variant,native in [('stock',False),('native',True)]:
        programs[variant]=[[at,list(code),hook]for at,code,hook in
                           [(0x70f000,worker(False,native),0xecc1),(0x70f100,worker(True,native),0xed19),
                            (0x70f200,lookup(native),0x2cf6e4),(0x70f300,init_hook(),0x2cecb0),(0x70f400,sequence_hook(),0xf073)]]
    return {'version':1,'source_sha256':royal.ROYAL_SHA256,'worker':{'selector':1,'name':'MR PERFECT','raw_slot':12},
            'roster':['Randy Savage','Mr. Perfect','Undertaker','Bret Hart','Tatanka','Crush','Ric Flair','Shawn Michaels','Razor Ramon','Yokozuna','Lex Luger','Ted DiBiase'],
            'frames':rows,'finisher':finisher,'programs':programs,
            'victim':json.loads((Path(__file__).resolve().parents[1]/'data/perfect-victim-layouts.json').read_text())['rows'],
            'palette':{'offset':0x17c46,'length':32},'coverage':coverage(rows)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in('raw_rom','raw_wram','royal_rom','royal_wram','captures'):p.add_argument(name,type=Path)
    p.add_argument('--matches',type=Path,help='data/perfect-pose-matches.json')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    matches=json.loads(a.matches.read_text())['rows'] if a.matches else None
    result=build(*(getattr(a,n).read_bytes()for n in('raw_rom','raw_wram','royal_rom','royal_wram')),a.captures,matches)
    a.output.write_text('window.RAW_ROYAL_IMPORT_MANIFEST='+json.dumps(result,separators=(',',':'))+';\n')
    print('Wrote address-only import recipe:',a.output.stat().st_size,'bytes')
