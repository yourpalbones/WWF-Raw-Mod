"""Isolate Sting's actual native OBJ pixels for outfit consistency review."""
import argparse,json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
from extract_oam import objects

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['rom','captures','grapples']:p.add_argument(name,type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();digest=hashlib.sha256(a.rom.read_bytes()).hexdigest()
    cases=[('Giving atomic drop',a.grapples/'give-atomic',288),('Giving vertical suplex',a.grapples/'give-suplex',288),
           ('Giving Samoan drop',a.grapples/'give-fallaway',288),('Giving faceplant',a.grapples/'give-slam',288),
           ('Taking back suplex',a.grapples/'take-back-suplex',288),('Taking fallaway slam',a.grapples/'take-fallaway',288),
           ('Deathlock turn',a.captures/'specials/finisher',132),('Deathlock hold',a.captures/'specials/finisher',180)]
    page=Image.new('RGB',(1200,800),'#24252d');draw=ImageDraw.Draw(page)
    for i,(label,folder,frame)in enumerate(cases):
        assert json.loads((folder/'capture-context.json').read_text())['rom_sha256']==digest
        prefix=folder/f'frame-{frame:06d}';read=lambda n:Path(str(prefix)+'-'+n+'.bin').read_bytes()
        parts=[(r,im)for r,im in objects(read('vram'),read('oam'),read('cgram'),read('registers')[0x2101])if r['palette']==0 and 0<=r['y']<190 and im.getbbox()]
        left=min(r['x']for r,im in parts);top=min(r['y']for r,im in parts)
        right=max(r['x']+r['size']for r,im in parts);bottom=max(r['y']+r['size']for r,im in parts)
        im=Image.new('RGBA',(right-left,bottom-top))
        for r,pic in reversed(parts):im.alpha_composite(pic,(r['x']-left,r['y']-top))
        scale=min(5,270//im.width,360//im.height);im=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
        x=i%4*300;y=i//4*400;page.paste(im,(x+15,y+30),im);draw.text((x+15,y+8),label,fill='white')
    a.output.parent.mkdir(parents=True,exist_ok=True);page.save(a.output)
