"""Publish donor-based Sting's real gameplay and full submission identity proof."""
import argparse,json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
from extract_oam import objects

p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('captures',type=Path);p.add_argument('grapples',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256(a.rom.read_bytes()).hexdigest();cases=[]
def publish(folder,label,interval,expected=None):
    context=json.loads((folder/'capture-context.json').read_text());assert context['rom_sha256']==digest
    frames=[];actions=set()
    for f in sorted(folder.glob('frame-*.png')):
        n=int(f.stem.split('-')[1])
        if n<24:continue
        frames.append(Image.open(f).convert('RGB').resize((768,672),Image.Resampling.NEAREST))
        wram=Path(str(f.with_suffix(''))+'-wram.bin').read_bytes();actions.add(int.from_bytes(wram[0x6b4:0x6b6],'little'))
    if expected is not None:assert expected in actions,(label,actions)
    frames[0].save(a.output/(label+'.gif'),save_all=True,append_images=frames[1:],duration=interval*1000//60,loop=0,optimize=True)
    cases.append({'case':label,'controller_recipe':folder.name,'observed_action_words':sorted(actions),'expected_action_seen':expected,'native_frame_interval':interval})
for name in ['walk','run-ropes','punch','kick']:publish(a.captures/'actions'/name,name,6)
publish(a.captures/'specials/finisher','scorpion-deathlock',6,592)
moves=[('give-atomic','give-atomic-drop',206),('give-back-suplex','give-back-suplex',210),
       ('give-fallaway','give-samoan-drop',234),('give-slam','give-faceplant',246),('give-suplex','give-vertical-suplex',174),
       ('take-atomic','take-atomic-drop',208),('take-back-suplex','take-back-suplex',212),
       ('take-faceplant','take-faceplant',248),('take-fallaway','take-fallaway-slam',240),('take-piledriver','take-vertical-suplex',176)]
for folder,label,action in moves:publish(a.grapples/folder,label,18,action)
Image.open(a.captures/'actions/walk/frame-000048.png').resize((768,672),Image.Resampling.NEAREST).save(a.output/'in-game.png')
# Isolate actual captured OBJ pixels for a readable head/body close-up. This
# retains the game's palette and geometry; it does not synthesize sprite art.
prefix=a.captures/'actions/walk/frame-000048';read=lambda name:Path(str(prefix)+'-'+name+'.bin').read_bytes()
parts=[(r,im)for r,im in objects(read('vram'),read('oam'),read('cgram'),read('registers')[0x2101])if r['palette']==0 and 0<=r['y']<190 and im.getbbox()]
l=min(r['x']for r,im in parts);t=min(r['y']for r,im in parts);right=max(r['x']+r['size']for r,im in parts);bottom=max(r['y']+r['size']for r,im in parts)
im=Image.new('RGBA',(right-l,bottom-t))
for r,pic in reversed(parts):im.alpha_composite(pic,(r['x']-l,r['y']-t))
im=im.resize((im.width*8,im.height*8),Image.Resampling.NEAREST);background=Image.new('RGB',im.size,'#24252d');background.paste(im,mask=im.getchannel('A'));background.save(a.output/'native-closeup.png')
page=Image.new('RGB',(4*320,3*265),'#24252d');draw=ImageDraw.Draw(page)
for n,frame in enumerate([60,66,72,84,96,108,120,132,144,168,180,240]):
    im=Image.open(a.captures/f'specials/finisher/frame-{frame:06d}.png').crop((70,70,230,190)).resize((320,240),Image.Resampling.NEAREST);x=n%4*320;y=n//4*265;page.paste(im,(x,y+22));draw.text((x+5,y+4),f'Native frame {frame}',fill='white')
page.save(a.output/'deathlock-sequence.png')
(a.output/'native-replays.json').write_text(json.dumps({'rom_sha256':digest,'method':'Pinned Snes9x; cold boot plus controller inputs only. No state-memory writes.','cases':cases,'complete_live_coverage':False},indent=2)+'\n');print('Published 15 native replay GIFs, live screenshot, close-up and full Deathlock contact sheet')
