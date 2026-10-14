"""Static source study. All offsets refer to private disc-extracted files."""
from pathlib import Path
from PIL import Image,ImageDraw
import bisect
import argparse,json
T=C=b''
starts=offs=[]
def load_source(chr_path,tab_path):
 global T,C,starts,offs
 T=Path(tab_path).read_bytes();C=Path(chr_path).read_bytes()
 if len(T)!=47370 or len(C)!=212480:raise ValueError('Unexpected Boss Man source file sizes')
 starts=[int.from_bytes(C[i*4:i*4+4],'big') for i in range(28)]
 offs=[int.from_bytes(C[128+i*4:132+i*4],'big') for i in range(28)]
def word(b,a):return int.from_bytes(b[a:a+2],'big')
def tile(n):
 k=bisect.bisect_right(starts,n)-1
 if k==27:
  p=offs[k]+(n-starts[k])*32;return C[p:p+32]
 if k<0:raise ValueError('tile id')
 p=offs[k]+(n-starts[k])*(k+5);mask=int.from_bytes(C[p:p+4],'big');fill=C[p+4];cur=p+5;out=[]
 for i in range(32):
  if mask&(1<<(31-i)):out.append(C[cur]);cur+=1
  else:out.append(fill)
 return out

def component(n):
 p=0x1946+word(T,0x988a+n*2);mask=word(T,p);p+=2;shape=-1;im=Image.new('P',(128,128))
 for _ in range(30):
  coord=word(T,p);p+=2
  if coord&0x8000:
   if not mask:return im
   while True:
    shape+=1;selected=mask&1;mask>>=1
    if selected:break
  if shape>=16:raise ValueError('shape')
  w=1+(shape>>2);h=1+(shape&3);x=(coord>>8)&127;y=coord&127
  for tx in range(w):
   for ty in range(h):
    raw=tile(word(T,p));p+=2
    for j,b in enumerate(raw):
     for dx,v in enumerate([b>>4,b&15]):
      px=x+tx*8+(j%4)*2+dx;py=y+ty*8+j//4
      if v and px<128 and py<128:im.putpixel((px,py),v)
 raise ValueError('long')
def pose(n):
 p=10+word(T,10+n*2);im=Image.new('P',(192,192));parts=[]
 for _ in range(20):
  ident=word(T,p);p+=2
  if ident==65535:break
  if ident==32768:continue
  dx,dy=T[p:p+2];p+=2;dx=dx-256 if dx&128 else dx;dy=dy-256 if dy&128 else dy
  parts.append((ident//2,dx,dy))
 for n,dx,dy in reversed(parts):
  c=component(n);mask=Image.frombytes('L',c.size,bytes(255 if x else 0 for x in c.get_flattened_data()));im.paste(c,(96+dx,128+dy),mask)
 return im

def main():
 ap=argparse.ArgumentParser(description='Rage in the Cage Boss Man artwork decoder.')
 ap.add_argument('chr',type=Path);ap.add_argument('tab',type=Path);ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--native-prefix',type=Path,help='Private Boss Man gameplay snapshot prefix for palette 2')
 args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True);load_source(args.chr,args.tab)
 pal=sum(([i*17]*3 for i in range(16)),[])+[0]*720
 if args.native_prefix:
  from genesis_sprite_capture import word as native_word,native_color
  c=Path(str(args.native_prefix)+'-cgram.bin').read_bytes()
  if len(c)!=128:raise ValueError('Not a Genesis CRAM snapshot')
  pal=sum((list(native_color(native_word(c,64+i*2))) for i in range(16)),[])+[0]*720
 records=[];images=[]
 for i in range(415):
  im=pose(i);im.putpalette(pal);images.append(im.convert('RGB'));records.append({'pose':i,'bbox':im.getbbox()})
 for page in range(7):
  sheet=Image.new('RGB',(8*160,8*200),(40,40,45));d=ImageDraw.Draw(sheet)
  for cell in range(64):
   i=page*64+cell
   if i>=len(images):break
   im=images[i];box=Image.frombytes('L',(192,192),bytes(255 if v else 0 for v in pose(i).get_flattened_data())).getbbox()
   if box:
    crop=im.crop(box);crop=crop.resize((crop.width*2,crop.height*2),Image.Resampling.NEAREST);sheet.paste(crop,(cell%8*160,cell//8*200+20))
   d.text((cell%8*160,cell//8*200),str(i),fill='white')
  sheet.save(args.output/f'poses-{page+1}.png')
 frames=[images[i].resize((576,576),Image.Resampling.NEAREST) for i in range(12,18)]
 frames[0].save(args.output/'walk-pose-study.gif',save_all=True,append_images=frames[1:],duration=120,loop=0)
 (args.output/'inventory.json').write_text(json.dumps({'composite_entries':len(records),'native_verified':False,'palette':'native palette 2' if args.native_prefix else 'temporary grayscale','animation_timing':'illustration only','poses':records},indent=2))
 print(f'Decoded {len(records)} composite entries; native verification pending.')

if __name__=='__main__':main()
