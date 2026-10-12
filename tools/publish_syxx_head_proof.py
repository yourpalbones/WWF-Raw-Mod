"""Publish screenshots and timed GIFs from native Syxx replay captures."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tarfile

from PIL import Image, ImageDraw


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom',type=Path)
    parser.add_argument('--captures',type=Path,required=True)
    parser.add_argument('--previous-archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    digest=hashlib.sha256(args.rom.read_bytes()).hexdigest()
    args.output.mkdir(parents=True,exist_ok=True)
    root=args.captures/'captures-syxx'
    ready=root/'ready/syxx/frame-004000.png'
    current=Image.open(ready).convert('RGB')
    current.resize((768,672),Image.Resampling.NEAREST).save(args.output/'in-game.png')
    old_key='outputs/nwo-art-revision/captures-syxx/ready/syxx/frame-004000.png'
    with tarfile.open(args.previous_archive,'r:gz')as archive:
        previous=Image.open(BytesIO(archive.extractfile(old_key).read())).convert('RGB')
    comparison=Image.new('RGB',(1024,480),'#151820')
    draw=ImageDraw.Draw(comparison)
    for x,label,im in [(0,'Before: v0.10',previous),(512,'After: v0.11 / native emulator capture',current)]:
        comparison.paste(im.resize((512,448),Image.Resampling.NEAREST),(x,28))
        draw.text((x+10,8),label,fill='white')
    comparison.save(args.output/'before-after.png')
    cases=[]
    folders=[(root/'actions/syxx'/name,name,100)for name in ['walk','run-ropes','punch','kick']]
    folders += [(root/'specials/syxx'/name,name,100)for name in ['finisher','mega']]
    folders += [(args.captures/'grapples/syxx'/name,name,300)for name in ['give-atomic','take-back-suplex']]
    for folder,name,delay in folders:
        context=json.loads((folder/'capture-context.json').read_text())
        assert context['rom_sha256']==digest,folder
        frames=[Image.open(p).convert('RGB').resize((512,448),Image.Resampling.NEAREST)
                for p in sorted(folder.glob('frame-*.png'))]
        frames[0].save(args.output/(name+'.gif'),save_all=True,append_images=frames[1:],
                       duration=delay,loop=0,optimize=False)
        actions=sorted({int.from_bytes(p.read_bytes()[0x6b4:0x6b6],'little')
                        for p in folder.glob('*-wram.bin')})
        run=json.loads((folder/'run.json').read_text())
        cases.append({'case':name,'frames':run['frames'],'inputs':run['presses'],
                      'observed_action_words':actions,'rom_sha256':digest,
                      'snapshot_interval':6 if delay==100 else 18})
    assert 608 in next(c['observed_action_words']for c in cases if c['case']=='finisher')
    assert 586 in next(c['observed_action_words']for c in cases if c['case']=='mega')
    grapples=[]
    for folder in sorted((args.captures/'grapples/syxx').iterdir()):
        if not folder.is_dir():continue
        context=json.loads((folder/'capture-context.json').read_text())
        assert context['rom_sha256']==digest
        grapples.append({'controller_recipe':folder.name,
                        'observed_action_words':sorted({int.from_bytes(p.read_bytes()[0x6b4:0x6b6],'little')
                                                       for p in folder.glob('*-wram.bin')})})
    report={'rom_sha256':digest,'capture_method':'Snes9x libretro, controller inputs, unmodified game state.',
            'cases':cases,'grapple_controller_samples':grapples,
            'complete_gameplay_coverage':False}
    (args.output/'native-replays.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Published native screenshot, comparison and',len(cases),'timed replay GIFs')


if __name__=='__main__':main()
