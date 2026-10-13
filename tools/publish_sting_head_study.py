"""Compare head pixels decoded from two actual Sting ROM builds."""
import argparse,copy,json
from pathlib import Path
from PIL import Image,ImageDraw
from scott_frame_catalog import catalog,raster
from inspect_rom import tile

def decoded(frame,rom):
    frame=copy.deepcopy(frame);kind=frame['kind']
    table=0x6fc000 if kind=='primary'else 0x6fd000
    pointers=0x6e0000 if kind=='primary'else 0x6f0000
    descriptor=int.from_bytes(rom[table+frame['index']*3:table+frame['index']*3+3],'little')
    for part in frame['parts']:
        for ref in part['refs']:
            ident=int.from_bytes(rom[descriptor+ref['relative']:descriptor+ref['relative']+2],'little')
            assert ident>=0xc000
            source=int.from_bytes(rom[pointers+(ident&0x3fff)*3:pointers+(ident&0x3fff)*3+3],'little')
            ref['pixels']=tile(rom[source:source+32],0,4)
    return raster(frame)[0]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('before',type=Path);p.add_argument('after',type=Path);p.add_argument('wram',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    before=a.before.read_bytes();after=a.after.read_bytes();frames=catalog(before,a.wram.read_bytes(),2)
    seeds=json.loads((Path(__file__).resolve().parents[1]/'data/sting-head-seeds.json').read_text())
    keys=['front','profile','profile-walking','angled-front','deathlock-entry-stand','deathlock-bend','deathlock-turn','deathlock-hold']
    page=Image.new('RGB',(960,1040),'#24252d');draw=ImageDraw.Draw(page)
    for i,key in enumerate(keys):
        s=seeds[key];frame=next(f for f in frames if f['kind']==s.get('kind','primary')and f['index']==s['piece'])
        x=i%4*240;y=i//4*520;draw.text((x+8,y+4),key,fill='white');l,t,r,b=s['box']
        for row,rom in enumerate([before,after]):
            im=Image.new('RGB',(r-l+7,b-t+8),'#24252d');points=decoded(frame,rom)
            colors=[int.from_bytes(rom[0x2cc5ba+n*2:0x2cc5bc+n*2],'little')for n in range(16)]
            for (qx,qy),v in points.items():
                if l-3<=qx<=r+3 and t-1<=qy<=b+6:
                    im.putpixel((qx-l+3,qy-t+1),tuple((colors[v]>>shift&31)*255//31 for shift in [0,5,10]))
            im=im.resize((im.width*8,im.height*8),Image.Resampling.NEAREST)
            page.paste(im,(x+8,y+45+row*240));draw.text((x+8,y+25+row*240),'v0.13'if row==0 else'Magazine reference revision',fill='white')
    a.output.parent.mkdir(parents=True,exist_ok=True);page.save(a.output)
