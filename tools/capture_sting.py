"""Replay Sting's replacement slot from cold boot with real controller inputs."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('core',type=Path);p.add_argument('rom',type=Path)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--mega',action='store_true')
p.add_argument('--trace-preparation',action='store_true',help='Also trace intermediate opponent-damage setup; not needed for sprite proofs')
a=p.parse_args();repo=Path(__file__).resolve().parents[1]
recipes=json.loads((repo/'data/roster-special-captures.json').read_text())['captures']
doink=next(c for c in recipes if c['id']=='doink-finisher')
bret=next(c for c in recipes if c['id']=='bret-finisher')
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
for i,st in enumerate(doink['stages'][:3]):
    stage={k:st[k] for k in ['frames','inputs']}
    state=run(stage,a.output/f'setup-{i}',state,trace=i==2)
ready=state
for name,button in [('walk',7),('run-ropes',7),('punch',0),('kick',8)]:
    inputs=[[0,1,3,8],[0,30,button,150 if button==7 else 8]]
    if name=='run-ropes':inputs.append([0,30,1,8])
    run({'frames':240,'inputs':inputs},a.output/'actions'/name,ready,6,True)
for i,st in enumerate(bret['stages'][1:-1],3):
    stage={k:st[k] for k in ['frames','inputs']}
    state=run(stage,a.output/f'setup-{i}',state,trace=a.trace_preparation)
last=bret['stages'][-1]
state=run({k:last[k] for k in ['frames','inputs']},a.output/'specials/finisher',state,6,True)
actions={int.from_bytes(p.read_bytes()[0x6b4:0x6b6],'little') for p in state.parent.glob('*-wram.bin')}
print({'observed_actions':sorted(actions),'sharpshooter_seen':592 in actions},flush=True)
assert 592 in actions,'Controller replay did not execute the Scorpion Deathlock'
if a.mega:
    mega=next(c for c in recipes if c['id']=='doink-mega')
    state=ready
    for i,st in enumerate(mega['stages'][3:],3):
        final=i==len(mega['stages'])-1
        state=run({k:st[k]for k in ['frames','inputs']},
                  a.output/('specials/mega' if final else f'mega-setup-{i}'),
                  state,6 if final else None,True)
    actions={int.from_bytes(p.read_bytes()[0x6b4:0x6b6],'little')for p in state.parent.glob('*-wram.bin')}
    assert mega['observed_action_word'] in actions,('Mega move replay failed',actions)
    print({'mega_observed_actions':sorted(actions),'native_mega_preserved':True},flush=True)
