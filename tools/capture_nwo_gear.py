"""Replay stock move recipes on a locally supplied edited ROM; no state mutation."""
import argparse,json,subprocess,os,shutil,hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('core',type=Path);p.add_argument('rom',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--only',choices=['scott','nash','syxx']);a=p.parse_args();repo=Path(__file__).resolve().parents[1];recipes=json.loads((repo/'data/roster-special-captures.json').read_text())['captures'];runner=repo/'tools/run_headless.py';a.output.mkdir(parents=True,exist_ok=True)
def run(stage,out,state=None,interval=None,extra=[]):
 end=out/f"frame-{stage['frames']:06d}.state"
 context={'rom_sha256':hashlib.sha256(a.rom.read_bytes()).hexdigest(),'state_sha256':hashlib.sha256(state.read_bytes()).hexdigest()if state else None,'stage':stage,'interval':interval,'extra':extra}
 if(out/'run.json').exists()and end.exists():
  previous=json.loads((out/'run.json').read_text())
  if(out/'capture-context.json').exists()and json.loads((out/'capture-context.json').read_text())==context:return end
 if out.exists():shutil.rmtree(out)
 cmd=['python3',str(runner),str(a.core),str(a.rom),'--output',str(out),'--frames',str(stage['frames']),'--interval',str(interval or stage['frames'])]
 if state:cmd+=['--load-state',str(state)]
 for port,frame,button,duration in stage['inputs']+extra:cmd+=['--press-p2'if port else'--press',f'{frame}:{button}:{duration}']
 subprocess.run(cmd,env={**os.environ,'WWF_TRACE_DIR':str(out.resolve())},check=True,stdout=subprocess.DEVNULL)
 (out/'capture-context.json').write_text(json.dumps(context,sort_keys=True)+'\n')
 for snapshot in out.glob('*.state'):
  if snapshot!=end:snapshot.unlink()
 log=out/'tiles.jsonl'
 if log.exists():
  kept=[];seen=set()
  for line in log.read_text().splitlines():
   e=json.loads(line)
   if e['source']not in seen:seen.add(e['source']);kept.append(line)
   else:(out/'assets'/f"tile-{e['event']:06d}-{e['source']:06x}.bin").unlink(missing_ok=True)
  log.write_text('\n'.join(kept)+'\n')
 return end
state=None
for i,stage in enumerate(recipes[0]['stages'][:2]):
 # Bret's first recipe is a combined menu sequence; use Scott's common stages.
 stage=next(c for c in recipes if c['id']=='razor-ramon-finisher')['stages'][i];state=run(stage,a.output/f'menu-{i}',state)
menu=state
for name,key in [('scott','razor-ramon'),('nash','diesel'),('syxx','123-kid')]:
 if a.only and a.only!=name:continue
 for kind in['finisher','mega']:
  case=next(c for c in recipes if c['id']==key+'-'+kind);state=menu
  for i,stage in enumerate(case['stages'][2:],2):
   if name=='syxx'and i==15:stage={**stage,'frames':240,'inputs':[[0,1,9,8]]}
   if name=='syxx'and i==16:stage={**stage,'inputs':[[0,1,6,20],[0,40,4,20],[0,100,4,16],[0,160,11,8]]}
   if name=='nash'and kind=='mega'and i==12:stage={**stage,'frames':300,'inputs':[[0,1,9,8]]}
   state=run(stage,a.output/'specials'/name/(kind if i==len(case['stages'])-1 else f'{kind}-setup-{i}'),state,6 if i==len(case['stages'])-1 else None)
  actions={int.from_bytes(p.read_bytes()[0x6b4:0x6b6],'little')for p in state.parent.glob('*-wram.bin')};assert case['observed_action_word']in actions,(name,kind,actions);print(name,kind,'verified',case['observed_action_word'],flush=True)
 case=next(c for c in recipes if c['id']==key+'-finisher');stage=case['stages'][2];ready=run({'frames':stage['frames']+150,'inputs':stage['inputs']},a.output/'ready'/name,menu,extra=[[0,stage['frames']+70,3,1]])
 for action,button in[('walk',7),('run-ropes',7),('punch',0),('kick',8)]:
  inputs=[[0,30,button,180 if button==7 else 8]]
  if action=='run-ropes':inputs.append([0,30,1,8])
  run({'frames':240,'inputs':inputs},a.output/'actions'/name/action,ready,6)
 print(name,'basic actions captured',flush=True)
