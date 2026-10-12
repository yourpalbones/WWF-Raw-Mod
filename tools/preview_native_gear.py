"""Render decoded native frame pieces from private gear tables for art review."""
import argparse,copy
from pathlib import Path
from PIL import Image,ImageDraw
from scott_frame_catalog import catalog,image
from build_nwo_gear import CONFIGS
from inspect_rom import tile
p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('wram',type=Path);p.add_argument('selector',type=int,choices=[5,9,10]);p.add_argument('--kind',choices=['primary','secondary'],default='primary');p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=60);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rom=a.rom.read_bytes();fs=catalog(rom,a.wram.read_bytes(),a.selector);c=CONFIGS[a.selector];colors=[int.from_bytes(rom[0x2cc4da+a.selector*32+i*2:0x2cc4dc+a.selector*32+i*2],'little')for i in range(16)];samples=[f for f in fs if f['kind']==a.kind][a.start:a.start+a.count];sheet=Image.new('RGB',(1000,((len(samples)+9)//10)*170),'#242429');d=ImageDraw.Draw(sheet)
for n,f in enumerate(samples):
 f=copy.deepcopy(f);table=c['primary_table']if f['kind']=='primary'else c['secondary_table'];ptr=int.from_bytes(rom[table+f['index']*3:table+f['index']*3+3],'little')
 if ptr:
  for part in f['parts']:
   for ref in part['refs']:
    tid=int.from_bytes(rom[ptr+ref['relative']:ptr+ref['relative']+2],'little')
    if tid>=0xc000:
     addr=int.from_bytes(rom[c['pointers']+(tid&0x3fff)*3:c['pointers']+(tid&0x3fff)*3+3],'little');ref['pixels']=tile(rom[addr:addr+32],0,4)
 im,_=image(f,colors);scale=min(3,95/max(im.size));im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.NEAREST);x=n%10*100;y=n//10*170;sheet.paste(im,(x+(100-im.width)//2,y+24),im);d.text((x+4,y+4),str(f['index']),fill='white')
a.output.parent.mkdir(parents=True,exist_ok=True);sheet.save(a.output);print('Saved',a.output)
