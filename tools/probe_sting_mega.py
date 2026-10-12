"""Check the recorded Doink Mega input recipe independently of finishers."""
import argparse,json,subprocess,os
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('core',type=Path);p.add_argument('rom',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();repo=Path(__file__).resolve().parents[1]
case=next(c for c in json.loads((repo/'data/roster-special-captures.json').read_text())['captures']if c['id']=='doink-mega');state=None
for i,st in enumerate(case['stages']):
    final=i==len(case['stages'])-1;folder=a.output/('capture'if final else f'setup-{i}')
    cmd=['python',str(repo/'tools/run_headless.py'),str(a.core),str(a.rom),'--output',str(folder),'--frames',str(st['frames']),'--interval','6'if final else str(st['frames'])]
    if state:cmd+=['--load-state',str(state)]
    for port,frame,button,duration in st['inputs']:cmd+=['--press-p2'if port else'--press',f'{frame}:{button}:{duration}']
    env={**os.environ};env.pop('WWF_TRACE_DIR',None)
    subprocess.run(cmd,env=env,check=True,stdout=subprocess.DEVNULL)
    state=folder/f"frame-{st['frames']:06d}.state"
    for f in folder.glob('*.state'):
        if f!=state:f.unlink()
actions=sorted({int.from_bytes(f.read_bytes()[0x6b4:0x6b6],'little')for f in folder.glob('*-wram.bin')})
report={'observed_actions':actions,'mega_seen':572 in actions}
(a.output/'result.json').write_text(json.dumps(report));print(report)
