"""Replay controller-only giving/taking grapple samples on the revised gear ROM."""
import argparse,json,subprocess,os,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
p=argparse.ArgumentParser(description=__doc__);p.add_argument('core',type=Path);p.add_argument('rom',type=Path);p.add_argument('--captures',type=Path,required=True);p.add_argument('--recipes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--only',choices=['scott','nash','syxx']);a=p.parse_args();repo=Path(__file__).resolve().parents[1];jobs=[];digest=hashlib.sha256(a.rom.read_bytes()).hexdigest()
for name in ['scott','nash','syxx']:
 if a.only and a.only!=name:continue
 ready=next((a.captures/f'captures-{name}'/'ready'/name).glob('*.state'))
 for old in sorted(a.recipes.iterdir()):
  if old.is_dir()and(old/'run.json').exists():jobs.append((name,ready,old))
def run(job):
 name,state,old=job;j=json.loads((old/'run.json').read_text());out=a.output/name/old.name;context={'rom_sha256':digest,'ready_sha256':hashlib.sha256(state.read_bytes()).hexdigest(),'inputs':j['presses'],'frames':j['frames']}
 if(out/'capture-context.json').exists():
  assert json.loads((out/'capture-context.json').read_text())==context;return name,old.name,'cached'
 cmd=['python3',str(repo/'tools/run_headless.py'),str(a.core),str(a.rom),'--output',str(out),'--load-state',str(state),'--frames',str(j['frames']),'--interval','18']
 for port,f,b,d in j['presses']:cmd+=['--press-p2'if port else'--press',f'{f}:{b}:{d}']
 subprocess.run(cmd,env={**os.environ,'WWF_TRACE_DIR':str(out.resolve())},check=True,stdout=subprocess.DEVNULL)
 for snapshot in out.glob('*.state'):snapshot.unlink()
 log=out/'tiles.jsonl';kept=[];seen=set()
 for line in log.read_text().splitlines():
  e=json.loads(line)
  if e['source']not in seen:seen.add(e['source']);kept.append(line)
  else:(out/'assets'/f"tile-{e['event']:06d}-{e['source']:06x}.bin").unlink(missing_ok=True)
 log.write_text('\n'.join(kept)+'\n');(out/'capture-context.json').write_text(json.dumps(context)+'\n');states=sorted({int.from_bytes(f.read_bytes()[0x6b4:0x6b6],'little')for f in out.glob('*-wram.bin')});return name,old.name,states
with ThreadPoolExecutor(max_workers=2)as pool:
 for result in pool.map(run,jobs):print(result,flush=True)
