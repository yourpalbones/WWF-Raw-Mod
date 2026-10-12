"""Publish native gameplay proof for Scott, Nash and Syxx without ROM data."""
from pathlib import Path
from PIL import Image,ImageDraw
import json,argparse,hashlib
repo=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser(description=__doc__);p.add_argument('--captures',type=Path,default=repo/'outputs/nwo-gear');p.add_argument('--output',type=Path,default=repo/'evidence/nwo-gear');a=p.parse_args();root=a.captures;out=a.output;out.mkdir(parents=True,exist_ok=True);sheet=Image.new('RGB',(768,244),'#151820');draw=ImageDraw.Draw(sheet);cases=[]
for n,name in enumerate(['scott','nash','syxx']):
 r=root/f'captures-{name}';ready=next((r/'ready'/name).glob('frame-*.png'));im=Image.open(ready).convert('RGB');sheet.paste(im,(n*256,20));draw.text((n*256+8,4),{'scott':'Scott Hall','nash':'Kevin Nash','syxx':'Syxx'}[name],fill='white')
 for kind in['finisher','mega']:
  folder=r/'specials'/name/kind;frames=[Image.open(p).convert('RGB').resize((512,448),Image.Resampling.NEAREST)for p in sorted(folder.glob('frame-*.png'))];frames[0].save(out/f'{name}-{kind}.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=False);j=json.loads((folder/'run.json').read_text());actions=sorted({int.from_bytes(p.read_bytes()[0x6b4:0x6b6],'little')for p in folder.glob('*-wram.bin')});cases.append(dict(character=name,kind=kind,observed_actions=actions,inputs=j['presses'],frames=j['frames'],rom_sha256=json.loads((folder/'capture-context.json').read_text())['rom_sha256']))
 for action in['walk','kick']:
  folder=r/'actions'/name/action;frames=[Image.open(p).convert('RGB').resize((512,448),Image.Resampling.NEAREST)for p in sorted(folder.glob('frame-*.png'))];frames[0].save(out/f'{name}-{action}.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=False)
sheet.resize((1536,488),Image.Resampling.NEAREST).save(out/'in-game-trio.png');before=Image.open(repo/'evidence/nwo-gear/in-game-trio.png').convert('RGB');after=sheet.resize((1536,488),Image.Resampling.NEAREST);comparison=Image.new('RGB',(1536,1024),'#151820');comparison.paste(before,(0,24));comparison.paste(after,(0,536));d=ImageDraw.Draw(comparison);d.text((10,7),'Before: v0.9',fill='white');d.text((10,519),'After: v0.10 — native emulator captures',fill='white');comparison.save(out/'before-after.png');(out/'special-inputs.json').write_text(json.dumps(cases,indent=2)+'\n');print('Native trio screenshot and twelve gameplay GIFs published')

summary=[]
for name in ['scott','nash','syxx']:
 for folder in sorted((root/'grapples'/name).iterdir()):
  states=sorted({int.from_bytes(p.read_bytes()[0x6b4:0x6b6],'little')for p in folder.glob('*-wram.bin')})
  summary.append({'character':name,'controller_recipe':folder.name,'observed_action_words':states})
(out/'grapple-samples.json').write_text(json.dumps(summary,indent=2)+'\n')
