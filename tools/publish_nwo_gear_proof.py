"""Publish native gameplay proof for Scott, Nash and Syxx without ROM data."""
from pathlib import Path
from PIL import Image,ImageDraw
import json
repo=Path(__file__).resolve().parents[1];root=repo/'outputs/nwo-gear';out=repo/'evidence/nwo-gear';out.mkdir(parents=True,exist_ok=True);sheet=Image.new('RGB',(768,244),'#151820');draw=ImageDraw.Draw(sheet);cases=[]
for n,name in enumerate(['scott','nash','syxx']):
 r=root/{'scott':'captures-raw-scott','nash':'verified-nash','syxx':'complete-captures'}[name];ready=next((r/'ready'/name).glob('frame-*.png'));im=Image.open(ready).convert('RGB');sheet.paste(im,(n*256,20));draw.text((n*256+8,4),{'scott':'Scott Hall','nash':'Kevin Nash','syxx':'Syxx'}[name],fill='white')
 for kind in['finisher','mega']:
  folder=r/'specials'/name/kind;frames=[Image.open(p).convert('RGB').resize((512,448),Image.Resampling.NEAREST)for p in sorted(folder.glob('frame-*.png'))];frames[0].save(out/f'{name}-{kind}.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=False);j=json.loads((folder/'run.json').read_text());actions=sorted({int.from_bytes(p.read_bytes()[0x6b4:0x6b6],'little')for p in folder.glob('*-wram.bin')});cases.append(dict(character=name,kind=kind,observed_actions=actions,inputs=j['presses'],frames=j['frames']))
 for action in['walk','kick']:
  folder=r/'actions'/name/action;frames=[Image.open(p).convert('RGB').resize((512,448),Image.Resampling.NEAREST)for p in sorted(folder.glob('frame-*.png'))];frames[0].save(out/f'{name}-{action}.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=False)
sheet.resize((1536,488),Image.Resampling.NEAREST).save(out/'in-game-trio.png');(out/'special-inputs.json').write_text(json.dumps(cases,indent=2)+'\n');print('Native trio screenshot and twelve gameplay GIFs published')
