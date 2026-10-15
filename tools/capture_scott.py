"""Replay Scott's slot (Razor Ramon's) from cold boot with real controller inputs: walk, ropes, punch, kick and the
Outsider's Edge (Razor's Edge). Same stages as tools/capture_sting.py, from the Razor Ramon captures in
data/roster-special-captures.json."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('core',type=Path);p.add_argument('rom',type=Path)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();repo=Path(__file__).resolve().parents[1]
recipes=json.loads((repo/'data/roster-special-captures.json').read_text())['captures']
razor=next(c for c in recipes if c['id']=='razor-ramon-finisher')
def run(stage,folder,state=None,interval=None,trace=False):
    context={'rom_sha256':hashlib.sha256(a.rom.read_bytes()).hexdigest(),
             'stage':stage,'input_state_sha256':hashlib.sha256(state.read_bytes()).hexdigest() if state else None}
    end=folder/f"frame-{stage['frames']:06d}.state"
    if end.exists() and (folder/'capture-context.json').exists():
        assert json.loads((folder/'capture-context.json').read_text())==context
        return end
    cmd=['python',str(repo/'tools/run_headless.py'),str(a.core),str(a.rom),
         '--output',str(folder),'--frames',str(stage['frames']),
         '--interval',str(interval or stage['frames'])]
    if state:cmd+=['--load-state',str(state)]
    for port,frame,button,duration in stage['inputs']:
        cmd+=['--press-p2' if port else '--press',f'{frame}:{button}:{duration}']
    env={**os.environ};env.pop('WWF_TRACE_DIR',None)
    if trace:env['WWF_TRACE_DIR']=str(folder.resolve())
    subprocess.run(cmd,env=env,check=True,stdout=subprocess.DEVNULL)
    (folder/'capture-context.json').write_text(json.dumps(context,sort_keys=True))
    for file in folder.glob('*.state'):
        if file!=end:file.unlink()
    log=folder/'tiles.jsonl'
    if log.exists():
        seen=set();kept=[]
        for line in log.read_text().splitlines():
            e=json.loads(line)
            if e['source'] not in seen:seen.add(e['source']);kept.append(line)
            else:(folder/'assets'/f"tile-{e['event']:06d}-{e['source']:06x}.bin").unlink(missing_ok=True)
        log.write_text('\n'.join(kept)+'\n')
    return end

state=None
for i,st in enumerate(razor['stages'][:3]):
    state=run({k:st[k] for k in ['frames','inputs']},a.output/f'setup-{i}',state,trace=i==2)
ready=state
for name,button in [('walk',7),('run-ropes',7),('punch',0),('kick',8)]:
    inputs=[[0,1,3,8],[0,30,button,150 if button==7 else 8]]
    if name=='run-ropes':inputs.append([0,30,1,8])
    run({'frames':240,'inputs':inputs},a.output/'actions'/name,ready,6,True)
for i,st in enumerate(razor['stages'][3:-1],3):
    state=run({k:st[k] for k in ['frames','inputs']},a.output/f'setup-{i}',state)
last=razor['stages'][-1]
state=run({k:last[k] for k in ['frames','inputs']},a.output/'specials/finisher',state,6,True)
actions={int.from_bytes(p.read_bytes()[0x6b4:0x6b6],'little') for p in state.parent.glob('*-wram.bin')}
print({'observed_actions':sorted(actions),'finisher_seen':razor['observed_action_word'] in actions},flush=True)
assert razor['observed_action_word'] in actions,"Controller replay did not execute the Outsider's Edge"
