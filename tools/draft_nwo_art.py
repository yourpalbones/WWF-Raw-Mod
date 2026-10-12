"""Create anatomy-audit art drafts; not a playable ROM or release preset."""
import argparse,copy
from pathlib import Path
from PIL import Image,ImageDraw
from scott_frame_catalog import catalog,raster,image
from native_gear_art import decorate as revised_decorate
from build_nwo_gear import decorate

SKIN={7,9,10,11,12,15}
def draft(frame,slot):
 return revised_decorate(frame,slot)

def apply(frame,changes):
 f=copy.deepcopy(frame)
 for p in f['parts']:
  for r in p['refs']:
   if r['field']in changes:r['pixels']=changes[r['field']]
 return f

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('selector',type=int,choices=[9,10]);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rom=a.rom.read_bytes();frames=catalog(rom,a.wram.read_bytes(),a.selector);palette=[int.from_bytes(rom[0x2cc4da+a.selector*32+i*2:0x2cc4dc+a.selector*32+i*2],'little')for i in range(16)];rgb=lambda r,g,b:r|g<<5|b<<10
 if a.selector==10:
  palette[2]=rgb(1,1,1);palette[3]=rgb(5,5,5);palette[13]=rgb(2,1,0);palette[14]=rgb(7,4,2);palette[6]=rgb(18,0,1);palette[8]=rgb(29,3,3)
 else:
  for i,v in {2:rgb(29,2,2),3:rgb(16,0,0),4:rgb(1,1,1),5:rgb(29,29,29),6:rgb(2,1,1),8:rgb(6,6,6)}.items():palette[i]=v
 sample=[f for f in frames if f['kind']=='primary' and len(f['parts'])>=6][:60];sheet=Image.new('RGB',(720,((len(sample)+5)//6)*220),'#23232b');draw=ImageDraw.Draw(sheet)
 for n,f in enumerate(sample):
  im,_=image(apply(f,draft(f,a.selector)),palette);im=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);x=n%6*120;y=n//6*220;sheet.paste(im,(x+(120-im.width)//2,y+25),im);draw.text((x+4,y+5),'DRAFT primary '+str(f['index']),fill='white')
 a.output.parent.mkdir(parents=True,exist_ok=True);sheet.save(a.output);print('Saved draft anatomy sheet:',a.output)
