"""Read-only Flair full-pose source extraction from SNES Royal Rumble USA."""
from pathlib import Path
from PIL import Image
import royal_rumble_sprites as royal

POSE_DIRECTORY=0x8ead84
POSE_COUNT=640

def pose_parts(rom,index):
 if not 0<=index<POSE_COUNT:raise ValueError('Royal composite pose outside directory')
 at=royal.lorom_offset(POSE_DIRECTORY)+index*2
 pointer=0x8e0000|int.from_bytes(rom[at:at+2],'little');parts=[]
 for _ in range(32):
  a=royal.lorom_offset(pointer);ident=int.from_bytes(rom[a:a+2],'little');pointer+=2
  if ident==0xffff:return parts
  if ident==0x8000:continue
  if ident&0x8000 or ident&1:raise ValueError('Unverified Royal pose control')
  dx,dy=rom[a+2:a+4];pointer+=2
  parts.append({'piece':ident//2,'dx':dx-256 if dx&128 else dx,'dy':dy-256 if dy&128 else dy})
 raise ValueError('Unterminated Royal composite pose')

def render_pose(rom,frames,index,include_shadow=True):
 im=Image.new('P',(192,192))
 for part in reversed(pose_parts(rom,index)):
  if not include_shadow and part['piece']<16:continue
  for (x,y),value in royal.raster(frames[part['piece']]).items():
   px=96+part['dx']+x+64;py=128+part['dy']+y+64
   if not 0<=px<192 or not 0<=py<192:raise ValueError('Pose exceeds study canvas')
   im.putpixel((px,py),value)
 return im
