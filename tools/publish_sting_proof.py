"""Publish real emulator captures of the Sting replacement, without ROM data."""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw
p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('captures',type=Path);p.add_argument('grapples',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256(a.rom.read_bytes()).hexdigest();cases=[]
for folder,label,duration in [(a.captures/'actions'/name,name,100)for name in ['walk','run-ropes','punch','kick']]+[(a.captures/'specials/finisher','scorpion-deathlock',100)]+[(a.grapples/name,name,300)for name in ['give-atomic','take-back-suplex']]:
    context=json.loads((folder/'capture-context.json').read_text());assert context['rom_sha256']==digest
    frames=[];actions=set();parts=set()
    for f in sorted(folder.glob('frame-*.png')):
        frame=int(f.stem.split('-')[1])
        if frame<24:continue
        im=Image.open(f).convert('RGB').resize((768,672),Image.Resampling.NEAREST);frames.append(im)
        wram=Path(str(f.with_suffix(''))+'-wram.bin').read_bytes();actions.add(int.from_bytes(wram[0x6b4:0x6b6],'little'))
    frames[0].save(a.output/(label+'.gif'),save_all=True,append_images=frames[1:],duration=duration,loop=0,optimize=True)
    cases.append({'case':label,'rom_sha256':digest,'observed_action_words':sorted(actions),
                  'controller_inputs':context.get('inputs',context.get('stage',{}).get('inputs')),
                  'native_frame_interval':6 if duration==100 else 18})
assert 592 in next(c['observed_action_words']for c in cases if c['case']=='scorpion-deathlock')
assert 206 in next(c['observed_action_words']for c in cases if c['case']=='give-atomic')
assert 212 in next(c['observed_action_words']for c in cases if c['case']=='take-back-suplex')
Image.open(a.captures/'actions/walk/frame-000048.png').resize((768,672),Image.Resampling.NEAREST).save(a.output/'in-game.png')
Image.open(a.captures/'specials/finisher/frame-000180.png').resize((768,672),Image.Resampling.NEAREST).save(a.output/'deathlock.png')
report={'playable_rom_sha256':digest,'method':'Pinned Snes9x libretro, cold boot and controller inputs; no WRAM/state mutation.',
        'cases':cases,'all_animations_verified':False,
        'mega_replay':'Recorded input recipe did not reproduce the Mega Move; also failed in the control with stock Doink finisher tables restored. Unverified.'}
(a.output/'native-replays.json').write_text(json.dumps(report,indent=2)+'\n');print('Published native PNGs and seven timed replay GIFs')
