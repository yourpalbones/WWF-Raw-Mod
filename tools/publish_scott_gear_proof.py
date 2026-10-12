"""Build public screenshots/GIFs from actual emulator captures, never ROM data."""
from pathlib import Path
from PIL import Image,ImageDraw
import json
repo=Path(__file__).resolve().parents[1];root=repo/'outputs/scott-hall-gear';out=repo/'evidence/scott-hall-gear';out.mkdir(parents=True,exist_ok=True)
before=Image.open(root/'fresh-before/frame-002800.png').convert('RGB');after=Image.open(root/'fresh-v5/frame-002800.png').convert('RGB');scale=3;pair=Image.new('RGB',(before.width*scale*2,(before.height+16)*scale),'#151820');draw=ImageDraw.Draw(pair)
for n,(label,im)in enumerate([('Your latest ROM',before),('Scott reference gear',after)]):
 draw.text((n*im.width*scale+12,8),label,fill='white');pair.paste(im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST),(n*im.width*scale,16*scale))
pair.save(out/'before-after.png');after.resize((after.width*3,after.height*3),Image.Resampling.NEAREST).save(out/'in-game.png')
recipes=[]
for name,path,limit in [('walking',root/'actions-v5/walk',240),('running-ropes',root/'actions-v5/run-ropes',300),('giving-slam',root/'grapple-v5/give-slam',420),('taking-piledriver',root/'grapple-v5/take-piledriver',480),('finisher',root/'specials-v5-traced/finisher',480),('mega-move',root/'specials-v5-traced/mega',300)]:
 frames=[Image.open(p).convert('RGB').resize((512,448),Image.Resampling.NEAREST)for p in sorted(path.glob('frame-*.png'))if int(p.stem.split('-')[1])<=limit];assert frames;frames[0].save(out/(name+'.gif'),save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=False);r=json.loads((path/'run.json').read_text());recipes.append({'name':name,'frames':r['frames'],'interval':r['interval'],'inputs':r['presses']})
(out/'controller-recipes.json').write_text(json.dumps(recipes,indent=2)+'\n');print('Published native gameplay screenshot and six GIFs')
